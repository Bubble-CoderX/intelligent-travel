"""O21: 出行统计 API — 聚合行程历史数据。"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/travel-stats", tags=["travel-stats"])


@router.get("/overview")
async def get_overview(device_id: str):
    """获取出行统计数据概览。"""
    db = get_db()

    # 总行程数
    total = db.execute(
        "SELECT COUNT(*) FROM trip_history WHERE device_id=?", (device_id,)
    ).fetchone()[0]

    # 城市数
    cities_count = db.execute(
        "SELECT COUNT(DISTINCT destination) FROM trip_history WHERE device_id=?", (device_id,)
    ).fetchone()[0]

    # 总天数
    total_days = db.execute(
        "SELECT COALESCE(SUM(days), 0) FROM trip_history WHERE device_id=?", (device_id,)
    ).fetchone()[0]

    # 总预算
    total_budget = db.execute(
        "SELECT COALESCE(SUM(budget_total), 0) FROM trip_history WHERE device_id=?", (device_id,)
    ).fetchone()[0]

    # 最常去的城市 Top 5
    top_cities = db.execute(
        "SELECT destination, COUNT(*) as cnt FROM trip_history "
        "WHERE device_id=? GROUP BY destination ORDER BY cnt DESC LIMIT 5",
        (device_id,),
    ).fetchall()

    # 人员构成分布
    composition_dist = db.execute(
        "SELECT composition, COUNT(*) as cnt FROM trip_history "
        "WHERE device_id=? AND composition != '' GROUP BY composition ORDER BY cnt DESC",
        (device_id,),
    ).fetchall()

    db.close()

    return {
        "total_trips": total,
        "cities_count": cities_count,
        "total_days": total_days,
        "total_budget": round(total_budget),
        "top_cities": [{"city": r["destination"], "count": r["cnt"]} for r in top_cities],
        "composition_dist": [{"type": r["composition"], "count": r["cnt"]} for r in composition_dist],
    }
