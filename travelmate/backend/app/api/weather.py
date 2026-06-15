from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request

from app.services.map_service import reverse_geocode
from app.services.memory_service import get_all_preferences
from app.services.weather_service import get_weather_forecast

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])

# 高德API返回的英文/拼音城市名 → 中文翻译
_EN_TO_CN_CITY: dict[str, str] = {
    # 中国城市（高德拼音）
    "Guangzhou": "广州", "Shenzhen": "深圳", "Beijing": "北京", "Shanghai": "上海",
    "Chengdu": "成都", "Hangzhou": "杭州", "Wuhan": "武汉", "Nanjing": "南京",
    "Chongqing": "重庆", "Xi'an": "西安", "Changsha": "长沙", "Kunming": "昆明",
    "Xiamen": "厦门", "Dali": "大理", "Sanya": "三亚", "Harbin": "哈尔滨",
    "Qingdao": "青岛", "Suzhou": "苏州", "Zhengzhou": "郑州", "Jinan": "济南",
    "Ningbo": "宁波", "Fuzhou": "福州", "Dongguan": "东莞", "Foshan": "佛山",
    "Wuxi": "无锡", "Nanning": "南宁", "Guiyang": "贵阳", "Lanzhou": "兰州",
    "Urumqi": "乌鲁木齐", "Lhasa": "拉萨",
    # 国际城市
    "San Francisco": "旧金山", "San Jose": "圣何塞", "Los Angeles": "洛杉矶",
    "New York": "纽约", "Boston": "波士顿", "Chicago": "芝加哥",
    "Seattle": "西雅图", "London": "伦敦", "Paris": "巴黎",
    "Tokyo": "东京", "Seoul": "首尔", "Singapore": "新加坡",
    "Bangkok": "曼谷", "Sydney": "悉尼", "Toronto": "多伦多",
}


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
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    request: Request = None,
):
    """获取用户当前所在地天气。定位优先级：指定city > 偏好城市 > 浏览器坐标 > IP"""
    resolved_city = city  # 如果直接传了 city 参数，优先使用

    # ① 用户偏好中是否有常住城市
    if not resolved_city:
        prefs = get_all_preferences(device_id)
        for p in prefs:
            if p.get("category") == "location" and p.get("key") == "home_city":
                resolved_city = p.get("value")
                break

    # ② 浏览器坐标 → 逆地理编码
    if not resolved_city and lat and lng:
        geo = reverse_geocode(f"{lng},{lat}")
        resolved_city = geo.get("city") if geo else None

    # ③ IP 定位（兜底）
    if not resolved_city and request:
        client_ip = request.client.host if request.client else None
        if client_ip:
            resolved_city = _ip_to_city(client_ip)

    if not resolved_city:
        return {"status": "unknown", "message": "无法确定你的位置，请在URL中添加city参数"}

    # 英文城市名 → 中文翻译（IP定位可能返回英文名）
    resolved_city = _EN_TO_CN_CITY.get(resolved_city, resolved_city)

    try:
        import asyncio
        weather = await asyncio.to_thread(get_weather_forecast, resolved_city)
        today = weather.get("days", [{}])[0] if weather.get("days") else {}
        return {
            "status": "ok",
            "city": resolved_city,
            "weather": today.get("day_weather", ""),
            "temp": today.get("day_temp", ""),
            "wind": today.get("day_wind", ""),
            "report_time": weather.get("report_time", ""),
        }
    except Exception as exc:
        logger.warning("天气查询失败: city=%s err=%s", resolved_city, exc)
        return {"status": "error", "city": resolved_city, "message": f"天气查询失败: {type(exc).__name__}"}
