import logging

from fastapi import APIRouter

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
