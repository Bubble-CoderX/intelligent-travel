from fastapi import APIRouter

router = APIRouter(prefix="/proactive", tags=["proactive"])


@router.get("/{device_id}")
async def get_proactive_messages(device_id: str):
    """获取主动推送消息（出发提醒、天气预警等）。"""
    return {"messages": []}
