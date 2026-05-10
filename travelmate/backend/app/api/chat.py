from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 阶段二：仅回显，后续接入意图管道
    return ChatResponse(
        reply=f"收到你的消息：{req.message}",
        intent="chat",
        message_type="text",
    )
