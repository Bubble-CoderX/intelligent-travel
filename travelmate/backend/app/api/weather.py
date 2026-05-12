from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request

from app.services.map_service import reverse_geocode
from app.services.memory_service import get_all_preferences
from app.services.weather_service import get_weather_forecast

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])


def _ip_to_city(ip: str) -> str | None:
    """通过 IP 获取城市（ip-api.com 免费服务，无需 API Key）。"""
    if ip in ("127.0.0.1", "::1", ""):
        return None
    try:
        resp = httpx.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = resp.json()
        if data.get("status") == "success":
            return data.get("city")
    except Exception:
        pass
    return None


@router.get("/current")
async def current_weather(
    device_id: str,
    lat: float | None = None,
    lng: float | None = None,
    request: Request = None,
):
    """获取用户当前所在地天气。定位优先级：偏好城市 > 浏览器坐标 > IP"""
    city = None

    # ① 用户偏好中是否有常住城市
    prefs = get_all_preferences(device_id)
    for p in prefs:
        if p.get("category") == "location" and p.get("key") == "home_city":
            city = p.get("value")
            break

    # ② 浏览器坐标 → 逆地理编码
    if not city and lat and lng:
        geo = reverse_geocode(f"{lng},{lat}")
        city = geo.get("city") if geo else None

    # ③ IP 定位（兜底）
    if not city and request:
        client_ip = request.client.host if request.client else None
        if client_ip:
            city = _ip_to_city(client_ip)

    if not city:
        return {"status": "unknown", "message": "无法确定你的位置"}

    try:
        import asyncio
        weather = await asyncio.to_thread(get_weather_forecast, city)
        today = weather.get("days", [{}])[0] if weather.get("days") else {}
        return {
            "status": "ok",
            "city": city,
            "weather": today.get("day_weather", ""),
            "temp": today.get("day_temp", ""),
            "wind": today.get("day_wind", ""),
            "report_time": weather.get("report_time", ""),
        }
    except Exception as exc:
        logger.warning("天气查询失败: city=%s err=%s", city, exc)
        return {"status": "error", "city": city, "message": f"天气查询失败: {type(exc).__name__}"}
