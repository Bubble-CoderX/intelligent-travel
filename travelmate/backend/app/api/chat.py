import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.context_service import save_message
from app.services.intent_router import route_intent
from app.utils.safety import check_rate_limit

from app.api.sessions import _generate_title, update_session_title

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 请求频率限制：每设备每分钟最多 30 次
    if not check_rate_limit(req.device_id):
        return ChatResponse(
            reply="请求太频繁了，请稍后再试～",
            intent="rate_limited",
            message_type="text",
        )

    session_id = req.session_id or "default"

    # F10: 情绪感知拦截——在意图识别前检测情绪
    try:
        from app.services.mood_companion_service import intercept_mood_in_chat
        mood_result = await intercept_mood_in_chat(req.message, req.device_id)
        if mood_result:
            save_message(req.device_id, session_id, "user", req.message, "MOOD")
            save_message(req.device_id, session_id, "assistant", mood_result["mood_response"], "MOOD")
            return ChatResponse(
                reply=mood_result["mood_response"],
                intent="CHAT",
                message_type="text",
                metadata={
                    "mood_type": mood_result["mood_type"],
                    "mood_label": mood_result["mood_label"],
                    "mood_confidence": mood_result["confidence"],
                },
            )
    except Exception:
        logger.debug("情绪检测失败，继续正常流程", exc_info=True)

    try:
        result = await route_intent(req.message, req.device_id, session_id=session_id, trip_style=req.trip_style)
    except Exception as exc:
        logger.exception("意图识别管道异常")
        return ChatResponse(
            reply=f"处理消息时出现错误：{type(exc).__name__}。请检查后端日志。",
            intent="error",
            message_type="text",
        )

    if result.get("intent") == "blocked":
        save_message(req.device_id, session_id, "user", req.message, "blocked")
        save_message(req.device_id, session_id, "assistant", result.get("reply", ""), "blocked")
        return ChatResponse(
            reply=result.get("reply", "抱歉，无法处理该请求。"),
            intent="blocked",
            message_type="text",
        )

    intent = result.get("intent", "CHAT")
    reply = result.get("reply", "")

    # 根据意图类型决定消息展示形式
    if intent == "TRIP_PLAN":
        message_type = "card"
    elif intent == "WEATHER":
        message_type = "weather"
    elif intent == "KNOWLEDGE":
        message_type = "knowledge"
    else:
        message_type = "text"

    metadata = {
        "layer": result.get("layer"),
        "sub_intent": result.get("sub_intent"),
        "confidence": result.get("confidence"),
        "safety": result.get("safety"),
    }

    # 安全提醒：WARN/URGENT 级别附加警告信息
    safety = result.get("safety", {})
    if safety.get("level") in ("WARN", "URGENT") and safety.get("warning"):
        metadata["safety_warning"] = safety["warning"]

    # 行程规划：传递结构化数据给前端 TripCard
    if intent == "TRIP_PLAN":
        extracted = result.get("extracted_data", {})
        trip_plan = extracted.get("_trip_plan")
        if trip_plan:
            metadata["trip_plan"] = trip_plan
            metadata["destination"] = trip_plan.get("destination", "")
            metadata["days"] = len(trip_plan.get("days", []))
        else:
            metadata["destination"] = extracted.get("destination", "")
            metadata["days"] = extracted.get("days", 0)
        metadata["trip_style"] = req.trip_style or "default"

    save_message(req.device_id, session_id, "user", req.message, intent)
    save_message(req.device_id, session_id, "assistant", reply, intent, metadata=metadata)

    # ── 会话自动命名 ──────────────────────────────────────
    from app.models.database import get_db as _get_db
    _conn = _get_db()
    _session = _conn.execute(
        "SELECT title FROM sessions WHERE session_id = ? AND device_id = ?",
        (session_id, req.device_id),
    ).fetchone()
    _conn.close()

    if _session:
        current_title = _session["title"] or ""
        # 行程规划生成了结构化方案 → 以目的地命名
        if intent == "TRIP_PLAN" and metadata.get("trip_plan"):
            dest = metadata.get("destination", "")
            days = metadata.get("days", 0)
            if dest:
                new_title = f"{dest}·{days}日游" if days else dest
                if new_title != current_title:
                    update_session_title(req.device_id, session_id, new_title)
        # 首条消息且仍是默认标题 → 用消息内容命名
        elif current_title in ("新会话", ""):
            new_title = _generate_title(req.device_id, session_id)
            if new_title != "新会话":
                update_session_title(req.device_id, session_id, new_title)

    return ChatResponse(
        reply=reply,
        intent=intent,
        message_type=message_type,
        metadata=metadata,
    )


# ── O9: 流式输出 SSE 端点 ────────────────────────────────

@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """流式对话：CHAT/WEATHER/KNOWLEDGE 逐字输出，TRIP_PLAN 整体返回。"""
    if not check_rate_limit(req.device_id):
        async def rate_limit_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '请求太频繁了，请稍后再试～'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(rate_limit_gen(), media_type="text/event-stream")

    session_id = req.session_id or "default"

    # 意图识别（非流式，快速判断意图类型）
    try:
        result = await route_intent(req.message, req.device_id, session_id=session_id, trip_style=req.trip_style)
    except Exception as exc:
        logger.exception("意图识别异常")
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': f'处理消息时出现错误：{type(exc).__name__}'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    intent = result.get("intent", "CHAT")
    reply = result.get("reply", "")

    # TRIP_PLAN 等结构化意图：整体返回（不适合流式）
    if intent in ("TRIP_PLAN", "blocked"):
        # 构建 metadata
        metadata = {}
        if intent == "TRIP_PLAN":
            extracted = result.get("extracted_data", {})
            trip_plan = extracted.get("_trip_plan")
            if trip_plan:
                metadata["trip_plan"] = trip_plan
                metadata["destination"] = trip_plan.get("destination", "")
                metadata["days"] = len(trip_plan.get("days", []))
            else:
                metadata["destination"] = extracted.get("destination", "")
                metadata["days"] = extracted.get("days", 0)
            metadata["trip_style"] = req.trip_style or "default"

        save_message(req.device_id, session_id, "user", req.message, intent)
        save_message(req.device_id, session_id, "assistant", reply, intent, metadata=metadata if metadata else None)

        async def full_gen():
            # 保存消息到数据库（含 metadata）
            save_message(req.device_id, session_id, "user", req.message, intent)
            save_message(req.device_id, session_id, "assistant", reply, intent, metadata=metadata if metadata else None)
            yield f"data: {json.dumps({'type': 'full', 'content': reply, 'intent': intent, 'metadata': metadata}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(full_gen(), media_type="text/event-stream")

    # CHAT/WEATHER/KNOWLEDGE：流式输出
    async def stream_gen():
        from app.services.llm_client import call_llm_stream
        from app.services.context_service import get_recent_history

        # 构建对话历史
        chat_prompt = (
            "你是「AI智游伴」，友好专业的旅行助手。简洁温暖，1-3句话。"
            "前面的消息是你们的对话历史，你必须基于历史回答。"
        )
        history = await get_recent_history(req.device_id, session_id=session_id)
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": req.message})

        full_reply = ""
        try:
            async for chunk in call_llm_stream(
                messages=messages,
                system_prompt=chat_prompt,
                temperature=0.7,
                max_tokens=300,
            ):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.warning("流式输出异常: %s", exc)
            if not full_reply:
                full_reply = reply  # 降级到非流式回复
                yield f"data: {json.dumps({'type': 'chunk', 'content': full_reply}, ensure_ascii=False)}\n\n"

        # 保存消息
        save_message(req.device_id, session_id, "user", req.message, intent)
        save_message(req.device_id, session_id, "assistant", full_reply, intent)

        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")


# ── O8: 图片/文件上传分析 ──────────────────────────────

import base64
from pydantic import BaseModel, Field


class ImageAnalyzeRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    session_id: str = Field(default="", description="会话 ID")
    image_base64: str = Field(..., description="图片 Base64 编码")
    question: str = Field(default="请分析这张图片", description="用户对图片的问题")
    filename: str = Field(default="", description="文件名")


@router.post("/chat/image")
async def analyze_image(req: ImageAnalyzeRequest):
    """分析上传的图片（景点识别/菜单翻译/路牌识别等）。"""
    session_id = req.session_id or "default"

    from app.services.llm_client import call_llm

    # 构建带图片的消息
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{req.image_base64}"}
                },
                {
                    "type": "text",
                    "text": req.question or "请分析这张图片，如果是景点请介绍，如果是菜单请翻译，如果是路牌请说明。"
                },
            ],
        }
    ]

    try:
        reply = await call_llm(
            messages=messages,
            system_prompt="你是「AI智游伴」，擅长识别景点、翻译菜单、解读路牌。用简洁友好的语气回答。",
            temperature=0.5,
            max_tokens=500,
        )
    except Exception as exc:
        logger.warning("图片分析失败: %s", exc)
        reply = f"图片分析失败：{type(exc).__name__}。请稍后再试。"

    # 保存消息
    save_message(req.device_id, session_id, "user", f"[图片] {req.question or '分析图片'}", "IMAGE")
    save_message(req.device_id, session_id, "assistant", reply, "IMAGE")

    return {"reply": reply, "intent": "IMAGE"}
