from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.intent_router import route_intent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    result = await route_intent(req.message, req.device_id)

    # 安全拦截时直接返回
    if result.get("intent") == "blocked":
        return ChatResponse(
            reply=result["reply"],
            intent="blocked",
            message_type="text",
        )

    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        message_type="text",
        metadata={
            "layer": result.get("layer"),
            "sub_intent": result.get("sub_intent"),
            "confidence": result.get("confidence"),
            "safety": result.get("safety"),
        },
    )
