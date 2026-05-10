from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{device_id}")
async def get_memory(device_id: str):
    """获取设备的用户记忆。"""
    return {"device_id": "device_id", "preferences": []}


@router.post("/{device_id}")
async def save_memory(device_id: str, category: str, key: str, value: str):
    """保存用户偏好。"""
    return {"status": "ok"}
