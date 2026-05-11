from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.memory_service import (
    forget_memory,
    get_all_preferences,
    query_memory,
    save_memory,
)

router = APIRouter(prefix="/memory", tags=["memory"])


class PreferenceSaveRequest(BaseModel):
    category: str = Field(..., description="偏好类别，如饮食/预算/住宿")
    key: str = Field(..., description="偏好键，如忌口/每日预算")
    value: str = Field(..., description="偏好值")


@router.get("/{device_id}/preferences")
async def get_preferences(device_id: str):
    """获取用户全部偏好列表。"""
    prefs = get_all_preferences(device_id)
    return {"device_id": device_id, "preferences": prefs, "total": len(prefs)}


@router.get("/{device_id}/query")
async def search_preferences(device_id: str, q: str = ""):
    """按关键词语义检索偏好。"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="查询参数 q 不能为空")
    results = query_memory(device_id, q)
    return {"device_id": device_id, "query": q, "results": results}


@router.post("/{device_id}/preferences")
async def add_preference(device_id: str, req: PreferenceSaveRequest):
    """手动保存一条用户偏好。"""
    ok = save_memory(device_id, req.category, req.key, req.value, source="api")
    if not ok:
        raise HTTPException(status_code=500, detail="保存失败")
    return {"status": "ok", "message": f"已保存偏好：{req.key} = {req.value}"}


@router.delete("/{device_id}/preferences")
async def delete_preferences(
    device_id: str,
    category: str | None = None,
    key: str | None = None,
):
    """删除用户偏好（支持按 category 或 category+key）。"""
    ok = forget_memory(device_id, category, key)
    if not ok:
        raise HTTPException(status_code=500, detail="删除失败")
    return {"status": "ok"}
