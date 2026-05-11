from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.proactive_service import (
    remove_weather_reminder,
    send_arrival_greeting,
    set_weather_reminder,
)

router = APIRouter(prefix="/proactive", tags=["proactive"])


class WeatherCheckRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    city: str = Field(..., description="要监控天气的城市")
    hour: int = Field(default=20, description="每天几点检查（24小时制）")
    minute: int = Field(default=0, description="分钟")


class SimulateArrivalRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    spot_name: str = Field(..., description="到达的景点名称")
    city: str = Field(default="", description="所在城市")


@router.post("/set-weather-check")
async def api_set_weather_check(req: WeatherCheckRequest):
    """设置每日天气定时提醒：有雨时自动推送。"""
    job_id = set_weather_reminder(req.device_id, req.city, req.hour, req.minute)
    return {"status": "ok", "job_id": job_id, "message": f"已设置{req.city}每日{req.hour:02d}:{req.minute:02d}天气检查"}


@router.delete("/weather-check/{job_id}")
async def api_remove_weather_check(job_id: str):
    """取消天气定时提醒。"""
    ok = remove_weather_reminder(job_id)
    return {"status": "ok" if ok else "not_found"}


@router.post("/simulate-arrival")
async def api_simulate_arrival(req: SimulateArrivalRequest):
    """模拟到达景点，推送问候消息。"""
    greeting = await send_arrival_greeting(req.device_id, req.spot_name, req.city)
    return {"status": "ok", "greeting": greeting}
