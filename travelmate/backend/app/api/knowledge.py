"""知识库管理 API：手动触发自动调研、批量扩充（SSE 进度）、查询状态。"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.knowledge_expander import auto_expand, has_local_knowledge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class AutoExpandRequest(BaseModel):
    spot_name: str = Field(..., description="景点名称，例如「平遥古城」")


class BatchExpandRequest(BaseModel):
    spot_names: list[str] = Field(..., description="景点名称列表", min_length=1, max_length=20)


@router.post("/auto-expand")
async def api_auto_expand(req: AutoExpandRequest):
    """手动触发景点知识自动调研。"""
    result = await auto_expand(req.spot_name)
    if result.get("status") == "no_results":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.post("/auto-expand-batch")
async def api_auto_expand_batch(req: BatchExpandRequest):
    """批量扩充景点知识库，通过 SSE 逐条推送进度。

    响应为 text/event-stream，每个事件格式：
    data: {"type": "progress", "spot": "...", "index": 1, "total": 7, "status": "generating"}
    data: {"type": "done", "spot": "...", "index": 1, "total": 7, "chunks": 8}
    data: {"type": "error", "spot": "...", "index": 1, "total": 7, "message": "..."}
    data: {"type": "complete", "total": 7, "success": 6, "failed": 1}
    """

    async def stream() -> AsyncGenerator[str, None]:
        total = len(req.spot_names)
        success = 0
        failed = 0

        for i, name in enumerate(req.spot_names):
            # 通知：开始生成
            yield f"data: {json.dumps({'type': 'progress', 'spot': name, 'index': i + 1, 'total': total, 'status': 'generating'}, ensure_ascii=False)}\n\n"

            try:
                # 检查是否已有本地知识
                if has_local_knowledge(name):
                    yield f"data: {json.dumps({'type': 'done', 'spot': name, 'index': i + 1, 'total': total, 'chunks': 0, 'cached': True}, ensure_ascii=False)}\n\n"
                    success += 1
                    continue

                result = await auto_expand(name)

                if result.get("status") == "ok":
                    yield f"data: {json.dumps({'type': 'done', 'spot': name, 'index': i + 1, 'total': total, 'chunks': result.get('chunk_count', 0), 'cached': False}, ensure_ascii=False)}\n\n"
                    success += 1
                else:
                    msg = result.get("message", "未知错误")
                    yield f"data: {json.dumps({'type': 'error', 'spot': name, 'index': i + 1, 'total': total, 'message': msg}, ensure_ascii=False)}\n\n"
                    failed += 1
            except Exception as exc:
                logger.warning("批量扩充「%s」失败：%s", name, exc)
                yield f"data: {json.dumps({'type': 'error', 'spot': name, 'index': i + 1, 'total': total, 'message': str(exc)}, ensure_ascii=False)}\n\n"
                failed += 1

        # 全部完成
        yield f"data: {json.dumps({'type': 'complete', 'total': total, 'success': success, 'failed': failed}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/has-local")
async def api_has_local(spot_name: str):
    """检查指定景点是否有本地知识文件。"""
    return {"has_local": has_local_knowledge(spot_name)}


CATEGORY_PROMPTS = {
    "景点": "国内热门旅游景点、自然风光、5A景区",
    "非遗文化": "中国非物质文化遗产，如传统技艺、戏曲、手工艺、民俗活动",
    "美食": "国内各地特色美食、传统小吃、饮食文化",
    "民俗": "国内各民族传统民俗活动、节庆习俗、民间艺术",
    "历史遗址": "国内重要历史文化遗址、考古发现、古迹",
    "名山大川": "国内著名的山川河流、自然地理奇观",
    "古城古镇": "国内知名古城、古镇、古村落",
    "博物馆": "国内知名博物馆、美术馆、展览馆",
}


@router.get("/generate-presets")
async def api_generate_presets(category: str = "景点", count: int = 15):
    """用 LLM 随机生成指定类别的预设项目（不使用固定景点池）。"""
    from app.services.llm_client import call_llm

    desc = CATEGORY_PROMPTS.get(category, category)
    prompt = (
        f"请随机生成 {count} 个中国境内与「{desc}」相关的名称，"
        f"每个名称之间用逗号分隔，只输出名称列表，不要编号、不要解释、不要换行。\n"
        f"要求：覆盖面广，不要重复类型，优先选知名度较高的。"
    )

    try:
        result = await call_llm(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是一个中文旅游知识助手。",
            temperature=0.9,
            max_tokens=300,
        )
        items = [s.strip() for s in result.replace("、", ",").split(",") if len(s.strip()) >= 2]
        return {"category": category, "items": items[:count]}
    except Exception:
        return {"category": category, "items": []}
