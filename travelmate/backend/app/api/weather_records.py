"""O20: 天气记录 API — 查询历史天气数据。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter

from app.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather-records", tags=["weather-records"])


@router.get("/list")
async def list_weather_records(city: str = "", limit: int = 30):
    """获取天气记录列表。"""
    db = get_db()
    if city:
        rows = db.execute(
            "SELECT id, city, weather, temperature, humidity, wind_direction, wind_power, fetched_at "
            "FROM weather_records WHERE city=? ORDER BY fetched_at DESC LIMIT ?",
            (city, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, city, weather, temperature, humidity, wind_direction, wind_power, fetched_at "
            "FROM weather_records ORDER BY fetched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    db.close()
    return {"records": [dict(r) for r in rows], "total": len(rows)}


@router.get("/cities")
async def list_weather_cities():
    """获取有天气记录的城市列表。"""
    db = get_db()
    rows = db.execute(
        "SELECT city, COUNT(*) as count, MAX(fetched_at) as latest "
        "FROM weather_records GROUP BY city ORDER BY count DESC"
    ).fetchall()
    db.close()
    return {"cities": [dict(r) for r in rows]}
