"""知识库管理 API：手动触发自动调研、查询状态。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.knowledge_expander import auto_expand, has_local_knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class AutoExpandRequest(BaseModel):
    spot_name: str = Field(..., description="景点名称，例如「平遥古城」")


@router.post("/auto-expand")
async def api_auto_expand(req: AutoExpandRequest):
    """手动触发景点知识自动调研。"""
    result = await auto_expand(req.spot_name)
    if result.get("status") == "no_results":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("/has-local")
async def api_has_local(spot_name: str):
    """检查指定景点是否有本地知识文件。"""
    return {"has_local": has_local_knowledge(spot_name)}
