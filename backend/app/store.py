"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。
"""
from __future__ import annotations

from typing import Any

from app.seed_data import SEED_ROWS


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = self._fresh_tables()

    @staticmethod
    def _fresh_tables() -> dict[str, list[dict[str, Any]]]:
        """从标准基线构建一份全新的表数据（整表替换，不追加）。"""
        return {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }

    def reload_seed(self) -> dict[str, list[dict[str, Any]]]:
        """重新初始化样例数据：整体替换而非追加，重复执行不会多出条目。

        返回初始化后的数据快照（深拷贝），供命令行做条数与指纹校验。
        """
        self._tables = self._fresh_tables()
        return {name: [dict(row) for row in rows] for name, rows in self._tables.items()}

    def module_names(self) -> list[str]:
        return sorted(self._tables)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}


store = Store()
