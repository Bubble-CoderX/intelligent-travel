import logging

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.intent_router import route_intent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
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
