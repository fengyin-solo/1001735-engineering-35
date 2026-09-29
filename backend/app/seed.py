"""样例数据工具：初始化、幂等自检与快照导出。

用途（在 backend/ 目录下执行）：

    # 初始化/重置内存样例数据到标准基线；重复执行结果完全一致，不会多出条目
    .venv/bin/python -m app.seed init

    # 只校验当前内存仓库与标准基线是否一致（条数、内容、指纹），不改动数据
    .venv/bin/python -m app.seed verify

    # 把当前内存仓库逐模块导出成 JSON 快照，--expect <模块=条数> 可顺带核对条数
    .venv/bin/python -m app.seed snapshot --out seed-snapshot.json --expect pressurepipe=3

标准基线就是 seed_data 模块里的 SEED_ROWS：本地直接运行、容器构建后运行、反复初始化，
看到的都是同一份数据。校验输出的指纹按 (模块、id、字段) 排序后做 SHA-256，
与行顺序无关，两个环境指纹相同即数据完全一致。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from typing import Any

from app.seed_data import SEED_ROWS


def _canonical(rows_by_module: dict[str, list[dict[str, Any]]]) -> bytes:
    """按模块名、记录 id、字段名排序后序列化，保证指纹只取决于数据内容。"""
    ordered: dict[str, list[dict[str, Any]]] = {}
    for module in sorted(rows_by_module):
        rows = [dict(row) for row in rows_by_module[module]]
        rows.sort(key=lambda row: int(row.get("id", 0)))
        ordered[module] = [{key: row[key] for key in sorted(row)} for row in rows]
    return json.dumps(ordered, ensure_ascii=False, sort_keys=True).encode("utf-8")


def fingerprint(rows_by_module: dict[str, list[dict[str, Any]]]) -> str:
    """返回一份样例数据的 SHA-256 指纹，用来比对两个环境是否同一份结果。"""
    return hashlib.sha256(_canonical(rows_by_module)).hexdigest()


def baseline() -> dict[str, list[dict[str, Any]]]:
    """返回标准基线数据的深拷贝，防止调用方改到模块级常量。"""
    return copy.deepcopy(SEED_ROWS)


def _diff(
    actual: dict[str, list[dict[str, Any]]],
    expected: dict[str, list[dict[str, Any]]],
) -> list[str]:
    """对比两份数据，返回可读的差异说明（缺模块、条数不符、内容不符）。"""
    problems: list[str] = []
    for module in sorted(set(actual) | set(expected)):
        if module not in actual:
            problems.append(f"模块 {module} 缺失")
            continue
        if module not in expected:
            problems.append(f"模块 {module} 不在标准基线内（多出 {len(actual[module])} 条）")
            continue
        if len(actual[module]) != len(expected[module]):
            problems.append(
                f"模块 {module} 条数 {len(actual[module])} != 标准 {len(expected[module])}"
            )
            continue
        if fingerprint({module: actual[module]}) != fingerprint({module: expected[module]}):
            problems.append(f"模块 {module} 内容与标准基线不一致")
    return problems


def _load_store() -> Any:
    # 延迟导入：命令行在导入阶段就需要用到 SEED_ROWS，但不应触发服务初始化。
    from app.store import store

    return store


def cmd_init() -> int:
    """把内存仓库重置为标准基线，并连做两次重置验证幂等性。"""
    store = _load_store()
    first = store.reload_seed()
    first_sig = fingerprint(first)
    second = store.reload_seed()  # 再初始化一次：幂等的关键自检
    second_sig = fingerprint(second)
    if second_sig != first_sig:
        print("初始化失败：重复初始化后数据发生变化（指纹不一致）", file=sys.stderr)
        return 1
    total = sum(len(rows) for rows in second.values())
    print(f"样例数据已初始化：{len(second)} 个模块，共 {total} 条记录")
    print(f"数据指纹：{second_sig}")
    print("幂等自检：连续初始化两次，条数与指纹一致，没有多出条目")
    return 0


def cmd_verify() -> int:
    """校验当前内存仓库是否仍是标准基线；不是时逐条列出缺什么。"""
    store = _load_store()
    actual = {name: store.rows(name) for name in store.module_names()}
    standard = baseline()
    problems = _diff(actual, standard)
    if problems:
        print("样例数据校验未通过：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            f"当前指纹 {fingerprint(actual)} != 标准指纹 {fingerprint(standard)}",
            file=sys.stderr,
        )
        print("修复：执行 python -m app.seed init 重新初始化", file=sys.stderr)
        return 1
    total = sum(len(rows) for rows in actual.values())
    print(f"样例数据校验通过：{len(actual)} 个模块，共 {total} 条记录")
    print(f"数据指纹：{fingerprint(actual)}")
    return 0


def _parse_expect(pairs: list[str]) -> dict[str, int]:
    expected: dict[str, int] = {}
    for pair in pairs:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(
                f"--expect 需要 模块=条数 形式，收到 {pair!r}"
            )
        module, raw = pair.split("=", 1)
        module = module.strip()
        if not module:
            raise argparse.ArgumentTypeError(f"--expect 模块名为空：{pair!r}")
        try:
            expected[module] = int(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"--expect 条数必须是整数，收到 {raw!r}"
            ) from exc
    return expected


def cmd_snapshot(out: str, expect: list[str]) -> int:
    """导出当前内存仓库快照；给出 --expect 时核对条数，不一致直接失败。"""
    store = _load_store()
    actual = {name: store.rows(name) for name in sorted(store.module_names())}
    try:
        expected_counts = _parse_expect(expect)
    except (ValueError, argparse.ArgumentTypeError) as exc:
        print(f"参数有误：{exc}", file=sys.stderr)
        return 2
    problems: list[str] = []
    for module, wanted in expected_counts.items():
        got = len(actual.get(module, []))
        if got != wanted:
            problems.append(f"模块 {module} 导出 {got} 条，期望 {wanted} 条")
    if problems:
        for problem in problems:
            print(f"导出中止：{problem}", file=sys.stderr)
        return 1
    payload = {
        "fingerprint": fingerprint(actual),
        "counts": {name: len(rows) for name, rows in actual.items()},
        "rows": actual,
    }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    total = sum(len(rows) for rows in actual.values())
    print(f"快照已写入 {out}：{len(actual)} 个模块，共 {total} 条记录")
    print(f"数据指纹：{payload['fingerprint']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed",
        description="压力管道等特种设备示例数据的初始化、校验与快照工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="初始化/重置为标准基线，重复执行不产生重复条目")
    sub.add_parser("verify", help="校验当前内存数据与标准基线是否一致")

    snap = sub.add_parser("snapshot", help="把当前数据导出为 JSON 快照")
    snap.add_argument("--out", default="seed-snapshot.json", help="快照输出路径")
    snap.add_argument(
        "--expect",
        action="append",
        default=[],
        metavar="模块=条数",
        help="核对某模块导出条数，可重复给出，例如 --expect pressurepipe=3",
    )

    args = parser.parse_args(argv)
    if args.command == "init":
        return cmd_init()
    if args.command == "verify":
        return cmd_verify()
    if args.command == "snapshot":
        return cmd_snapshot(args.out, args.expect)
    parser.error(f"未知命令：{args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
