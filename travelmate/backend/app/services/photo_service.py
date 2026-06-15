"""O22: 景点图片获取服务 — 调用高德地图POI搜索获取实景照片。"""

from __future__ import annotations

import logging

import httpx

from app.core.config import AMAP_API_KEY

logger = logging.getLogger(__name__)


def get_poi_photo(spot_name: str, city: str) -> str | None:
    """获取景点/餐厅的实景照片URL。无照片返回 None。"""
    if not AMAP_API_KEY:
        return None
    try:
        resp = httpx.get(
            "https://restapi.amap.com/v3/place/text",
            params={
                "key": AMAP_API_KEY,
                "keywords": spot_name,
                "city": city,
                "offset": 1,
                "extensions": "all",
            },
            timeout=5,
        )
        data = resp.json()
        pois = data.get("pois", [])
        if pois:
            photos = pois[0].get("photos", [])
            if photos:
                return photos[0].get("url")
    except Exception as e:
        logger.debug("获取照片失败 %s: %s", spot_name, e)
    return None


async def enrich_itinerary_with_photos(itinerary: dict) -> dict:
    """为行程中每个景点补充高德实景照片 URL。"""
    city = itinerary.get("destination", "")
    if not city:
        return itinerary

    for day in itinerary.get("days", []):
        for spot in day.get("spots", []):
            name = spot.get("name", "")
            if name and not spot.get("photo_url"):
                photo = get_poi_photo(name, city)
                if photo:
                    spot["photo_url"] = photo
        for meal in day.get("meals", []):
            name = meal.get("name", "")
            # 只查餐厅名（去掉括号里的店名后缀）
            clean_name = name.split("（")[0].split("(")[0].strip()
            if clean_name and not meal.get("photo_url"):
                photo = get_poi_photo(clean_name, city)
                if photo:
                    meal["photo_url"] = photo

    return itinerary
