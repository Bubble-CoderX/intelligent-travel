import logging

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.intent_router import route_intent
from app.utils.safety import check_rate_limit

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

    try:
        result = await route_intent(req.message, req.device_id)
    except Exception as exc:
        logger.exception("意图识别管道异常")
        return ChatResponse(
            reply=f"处理消息时出现错误：{type(exc).__name__}。请检查后端日志。",
            intent="error",
            message_type="text",
        )

    if result.get("intent") == "blocked":
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

    # 行程规划：把结构化数据也带上，方便前端渲染卡片
    if intent == "TRIP_PLAN":
        extracted = result.get("extracted_data", {})
        metadata["destination"] = extracted.get("destination", "")
        metadata["days"] = extracted.get("days", 0)
        metadata["budget"] = extracted.get("budget", 0)

    return ChatResponse(
        reply=reply,
        intent=intent,
        message_type=message_type,
        metadata=metadata,
    )
