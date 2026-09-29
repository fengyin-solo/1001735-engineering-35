"""压力管道接口：维护压力管道，覆盖办理投用、安排检修、停用管道等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.pressurepipe import PressurepipeService

router = APIRouter(prefix="/api/pressurepipe", tags=["压力管道"])

service = PressurepipeService()

LIST_FIELDS = ["管道编号", "管道名称", "管道级别", "公称直径", "输送介质", "敷设方式", "下次检验日", "管道状态"]
STATUSES = ["待投用", "在用运行", "隔离检修", "已停用"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按管道编号检索"),
    status: str | None = Query(default=None, description="待投用、在用运行、隔离检修、已停用"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按管道编号与状态过滤压力管道列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


# 注意：/export 必须声明在 /{entry_id} 之前，否则字面量 "export" 会被
# 当成 entry_id 解析，直接返回 422，前端“导出”按钮拿到的是错误页。
@router.get("/export")
def export_entries(
    keyword: str | None = Query(default=None, description="按管道编号检索，与列表筛选一致"),
    status: str | None = Query(default=None, description="待投用、在用运行、隔离检修、已停用"),
) -> JSONResponse:
    """导出压力管道清单：按列表当前筛选条件（keyword/status）返回全量条目。

    条数与列表 total 始终一致（不分页、不额外裁剪），保证“另存的文件条数=列表当前范围”。
    以附件形式返回，浏览器直接触发另存。
    """
    items, total = service.list_entries(keyword=keyword, status=status, page=1, size=10000)
    payload: dict[str, Any] = {"module": "pressurepipe", "total": total, "items": items}
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="pressurepipe.json"'},
    )


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条压力管道明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"压力管道 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条压力管道，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="压力管道已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条压力管道执行办理投用、安排检修、停用管道；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
