"""样例数据初始化与校验命令。

用法（在 backend/ 目录下）：

    .venv/bin/python -m app.seed_cli init
        初始化样例数据并做幂等自检：连续装载两遍基准数据，逐模块比对条数，
        证明“反复初始化不会多出条目”。输出每模块条数、总条数与基准数据校验和。

    .venv/bin/python -m app.seed_cli check [--base-url URL] [--expect-sha SHA]
        不连服务时，只校验基准数据本身（每模块 id 唯一、条数正常）并打印校验和；
        给出 --base-url 时，再请求运行中的服务（overview + 压力管道导出），
        比对条数是否与基准一致、导出条目数是否等于列表 total；
        给出 --expect-sha 时，校验基准数据指纹（用于本地与容器交叉核对）。

退出码：0 通过；1 发现条数不一致或指纹不符（属于样例数据被污染，需重新 init）；
2 请求不到服务等环境问题（会打印缺的是什么）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.seed import SEED_ROWS
from app.store import Store


def canonical_bytes() -> bytes:
    """基准样例数据的规范化字节串：同样的数据在任何机器/容器里指纹一致。"""
    return json.dumps(
        SEED_ROWS, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha() -> str:
    return hashlib.sha256(canonical_bytes()).hexdigest()


def expected_counts() -> dict[str, int]:
    return {name: len(rows) for name, rows in SEED_ROWS.items()}


def validate_canonical() -> list[str]:
    """检查基准数据自身：条数为正、id 在模块内唯一。"""
    problems: list[str] = []
    for name, rows in SEED_ROWS.items():
        if not rows:
            problems.append(f"模块 {name} 没有任何样例条目")
        ids = [int(row.get("id", 0)) for row in rows]
        if len(set(ids)) != len(ids):
            problems.append(f"模块 {name} 的样例 id 存在重复：{ids}")
    return problems


def cmd_init() -> int:
    problems = validate_canonical()
    if problems:
        for problem in problems:
            print(f"[失败] {problem}")
        return 1

    # 幂等自检：用同一份基准数据连续初始化两个独立仓库，再“重置”一次，
    # 任何模块条数都不允许增长。
    first = Store()
    second = Store()
    second.reset_to_seed()
    second.reset_to_seed()

    counts = expected_counts()
    total = sum(counts.values())
    for name in sorted(counts):
        got = (len(first.rows(name)), len(second.rows(name)))
        if got != (counts[name], counts[name]):
            print(f"[失败] 模块 {name} 重复初始化后条数变化：{got}，应为 {counts[name]}")
            return 1

    print("[OK] 样例数据初始化完成，连续初始化三遍条数未增长（幂等）")
    for name in sorted(counts):
        print(f"     {name:<12} {counts[name]} 条")
    print(f"[合计] {len(counts)} 个模块，{total} 条样例记录")
    print(f"[指纹] sha256:{canonical_sha()}")
    return 0


def http_get_json(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    request = urllib.request.Request(path + query, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def cmd_check(base_url: str | None, expect_sha: str | None) -> int:
    problems = validate_canonical()
    if problems:
        for problem in problems:
            print(f"[失败] {problem}")
        return 1

    sha = canonical_sha()
    print(f"[基准] sha256:{sha}")
    counts = expected_counts()
    print(f"[基准] {len(counts)} 个模块，共 {sum(counts.values())} 条样例记录")

    if expect_sha and expect_sha.strip() != sha:
        print(f"[失败] 基准数据指纹不一致：期望 {expect_sha.strip()}")
        return 1

    if not base_url:
        print("[OK] 基准样例数据校验通过（未连接服务，跳过运行时比对）")
        return 0

    base_url = base_url.rstrip("/")
    try:
        overview = http_get_json(f"{base_url}/api/overview")
    except (urllib.error.URLError, OSError) as exc:
        print(f"[环境缺失] 连不上后端服务 {base_url}：{exc}")
        print("          请先在 backend/ 下执行 ./run.sh（容器方式用 docker compose up -d backend）")
        return 2

    actual = {item["name"]: int(item["created"]) for item in overview.get("modules", [])}
    ok = True
    for name in sorted(counts):
        if actual.get(name) != counts[name]:
            print(f"[失败] 模块 {name} 服务内 {actual.get(name)} 条，基准 {counts[name]} 条")
            ok = False
    if not ok:
        print("       服务里的样例数据与基准不符（可能重复灌数或被改动），重启后端即可恢复基准")
        return 1

    # 压力管道：列表 total 必须与导出文件条数一致（另存出来的文件条数 = 列表当前范围）
    cases = (
        ("全量", None),
        ("按关键字", {"keyword": "PRES-0002"}),
        ("按状态", {"status": "在用运行"}),
    )
    for label, params in cases:
        listing = http_get_json(f"{base_url}/api/pressurepipe", params)
        exported = http_get_json(f"{base_url}/api/pressurepipe/export", params)
        list_total = int(listing["total"])
        export_total = int(exported["total"])
        item_count = len(exported["items"])
        if not (list_total == export_total == item_count):
            print(f"[失败] 压力管道{label}：列表 total={list_total}，导出 total={export_total}，"
                  f"导出条目数={item_count}，三者应一致")
            return 1
        print(f"[OK] 压力管道{label}：列表/导出均为 {item_count} 条")

    print("[OK] 运行中服务的样例数据与基准一致，导出条数与列表范围一致")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="样例数据初始化与校验")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="初始化样例数据并做幂等自检")

    check = sub.add_parser("check", help="校验基准数据及运行中服务的数据一致性")
    check.add_argument("--base-url", default=None, help="后端地址，如 http://127.0.0.1:8000")
    check.add_argument("--expect-sha", default=None, help="期望的基准数据 sha256 指纹")

    args = parser.parse_args()
    if args.command == "init":
        return cmd_init()
    return cmd_check(args.base_url, args.expect_sha)


if __name__ == "__main__":
    sys.exit(main())
