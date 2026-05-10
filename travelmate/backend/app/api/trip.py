from fastapi import APIRouter

router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("/{device_id}/list")
async def list_trips(device_id: str):
    """获取设备的行程列表。"""
    return {"total": 0, "items": []}


@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    """获取单个行程详情。"""
    return {"trip_id": trip_id, "itinerary": None}
