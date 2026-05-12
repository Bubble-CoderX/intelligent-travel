from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.proactive_service import (
    generate_greeting,
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


@router.get("/greet")
async def api_greet(device_id: str):
    """生成个性化开场问候（新会话或每日首次打开时调用）。"""
    result = await generate_greeting(device_id)
    return result


class GreetSessionRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    session_id: str = Field(..., description="会话 ID")


@router.post("/greet-session")
async def api_greet_session(req: GreetSessionRequest):
    """切换会话时生成问候并保存到数据库（每个会话只问候一次）。"""
    conn = get_db()

    # 检查该会话是否已经问候过
    session = conn.execute(
        "SELECT greeted FROM sessions WHERE session_id = ? AND device_id = ?",
        (req.session_id, req.device_id),
    ).fetchone()

    if session and session["greeted"]:
        conn.close()
        return {"status": "skipped"}

    # 生成问候
    result = await generate_greeting(req.device_id)
    greeting = result.get("greeting", "")
    if not greeting:
        conn.close()
        return {"status": "empty"}

    # 保存到 conversations 表
    conn.execute(
        "INSERT INTO conversations (device_id, session_id, role, content) VALUES (?, ?, 'assistant', ?)",
        (req.device_id, req.session_id, greeting),
    )
    # 标记已问候 + 更新 updated_at
    conn.execute(
        "UPDATE sessions SET greeted = 1, updated_at = CURRENT_TIMESTAMP WHERE session_id = ? AND device_id = ?",
        (req.session_id, req.device_id),
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "greeting": greeting}
