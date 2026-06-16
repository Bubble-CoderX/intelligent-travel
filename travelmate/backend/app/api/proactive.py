from __future__ import annotations

import json as _json
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.proactive_service import (
    generate_greeting,
    remove_weather_broadcasts,
    remove_weather_reminder,
    send_arrival_greeting,
    setup_weather_broadcasts,
)

router = APIRouter(prefix="/proactive", tags=["proactive"])

# 主动服务最小间隔（天）
GREET_COOLDOWN_DAYS = 7


class WeatherCheckRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    city: str = Field(..., description="要监控天气的城市")


class SimulateArrivalRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    spot_name: str = Field(..., description="到达的景点名称")
    city: str = Field(default="", description="所在城市")


class RemoveBroadcastsRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")


def _get_client_ip(request: Request) -> str | None:
    if request and request.client:
        return request.client.host
    return None


@router.post("/set-weather-check")
async def api_set_weather_check(req: WeatherCheckRequest):
    """设置每日 4 时段天气播报（7:00 / 12:00 / 19:00 / 0:00）。"""
    job_ids = setup_weather_broadcasts(req.device_id, req.city)
    return {"status": "ok", "job_ids": job_ids, "message": f"已设置{req.city}每日天气播报（7:00/12:00/19:00/0:00）"}


@router.delete("/weather-check/{job_id}")
async def api_remove_weather_check(job_id: str):
    """取消天气定时提醒。"""
    ok = remove_weather_reminder(job_id)
    return {"status": "ok" if ok else "not_found"}


@router.post("/weather-broadcasts/remove")
async def api_remove_all_broadcasts(req: RemoveBroadcastsRequest):
    """移除设备的所有天气播报。"""
    count = remove_weather_broadcasts(req.device_id)
    return {"status": "ok", "removed": count}


@router.post("/simulate-arrival")
async def api_simulate_arrival(req: SimulateArrivalRequest):
    """模拟到达景点，推送问候消息。"""
    greeting = await send_arrival_greeting(req.device_id, req.spot_name, req.city)
    return {"status": "ok", "greeting": greeting}


@router.get("/greet")
async def api_greet(device_id: str, request: Request = None):
    """生成个性化开场问候（使用 IP 定位所在城市天气）。"""
    client_ip = _get_client_ip(request)
    result = await generate_greeting(device_id, client_ip=client_ip)
    return result


class GreetSessionRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    session_id: str = Field(..., description="会话 ID")


@router.post("/greet-session")
async def api_greet_session(req: GreetSessionRequest, request: Request = None):
    """切换会话时生成问候，带 7 天去重逻辑。"""
    conn = get_db()

    # ① 检查该会话最新一条 assistant 消息是否为主动服务，以及距今多久
    last_msg = conn.execute(
        """SELECT content, created_at, metadata
           FROM conversations
           WHERE device_id = ? AND session_id = ? AND role = 'assistant'
           ORDER BY id DESC LIMIT 1""",
        (req.device_id, req.session_id),
    ).fetchone()

    if last_msg and last_msg["metadata"]:
        try:
            meta = _json.loads(last_msg["metadata"])
            if meta.get("proactive_type"):
                # 有主动服务记录，检查时间间隔
                created_str = last_msg["created_at"]
                if created_str:
                    created_dt = datetime.strptime(created_str[:19], "%Y-%m-%d %H:%M:%S")
                    days_ago = (datetime.now() - created_dt).days
                    if days_ago < GREET_COOLDOWN_DAYS:
                        conn.close()
                        return {"status": "skipped", "reason": f"距上次主动服务仅 {days_ago} 天"}
        except (ValueError, _json.JSONDecodeError):
            pass

    # ② 生成问候（传入客户端 IP 用于定位）
    client_ip = _get_client_ip(request)
    result = await generate_greeting(req.device_id, client_ip=client_ip)
    greeting = result.get("greeting", "")
    if not greeting:
        conn.close()
        return {"status": "empty"}

    # ③ 保存到 conversations 表，标记 metadata 为主动服务
    meta_json = _json.dumps({"proactive_type": "greeting", "generated_by": "greet-session"}, ensure_ascii=False)
    from datetime import datetime, timezone, timedelta
    local_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO conversations (device_id, session_id, role, content, metadata, created_at) VALUES (?, ?, 'assistant', ?, ?, ?)",
        (req.device_id, req.session_id, greeting, meta_json, local_time),
    )
    # 更新会话时间
    conn.execute(
        "UPDATE sessions SET updated_at = ? WHERE session_id = ? AND device_id = ?",
        (local_time, req.session_id, req.device_id),
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "greeting": greeting}
