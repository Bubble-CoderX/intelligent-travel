from fastapi import APIRouter, Header
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    type: str = "text"
    metadata: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_device_id: str = Header(default="")):
    return ChatResponse(
        reply=f"你说了：{req.message}",
        type="text",
    )
