"""O16: 行程历史记录 API — 列表/详情/状态更新/删除。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trip-history", tags=["trip-history"])


def init_trip_history():
    """启动时将旧 trip_plans 数据迁移到 trip_history。"""
    try:
        db = get_db()
        # 检查 trip_history 是否为空
        count = db.execute("SELECT COUNT(*) FROM trip_history").fetchone()[0]
        if count > 0:
            db.close()
            return

        # 从旧表迁移
        rows = db.execute(
            "SELECT device_id, destination, days, plan_json, created_at FROM trip_plans ORDER BY created_at DESC"
        ).fetchall()
        for r in rows:
            plan = json.loads(r["plan_json"]) if r["plan_json"] else {}
            title = plan.get("summary", "")
            if not title:
                title = f"{r['destination']}{r['days']}日游"
            db.execute(
                """INSERT INTO trip_history
                (device_id, title, destination, days, budget_total, itinerary_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)""",
                (
                    r["device_id"],
                    title[:100],
                    r["destination"],
                    r["days"],
                    plan.get("estimated_budget", 0),
                    r["plan_json"],
                    r["created_at"],
                ),
            )
        db.commit()
        db.close()
        logger.info("已迁移 %d 条旧行程到 trip_history", len(rows))
    except Exception:
        logger.exception("行程历史迁移失败")


def save_trip_history(
    device_id: str,
    itinerary: dict,
    session_id: str = "",
) -> int:
    """行程生成成功后调用，写入历史记录。返回记录 ID。"""
    try:
        db = get_db()
        days = itinerary.get("days", [])
        title = itinerary.get("summary", "")
        if not title and days:
            title = f"{itinerary.get('destination', '')}{len(days)}日游"

        db.execute(
            """INSERT INTO trip_history
            (device_id, session_id, title, destination, departure_city,
             days, group_size, composition, budget_total, itinerary_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned')""",
            (
                device_id,
                session_id,
                title[:100],
                itinerary.get("destination", ""),
                itinerary.get("departure_city", ""),
                len(days),
                itinerary.get("group_size", 2),
                itinerary.get("composition", ""),
                itinerary.get("estimated_budget", 0),
                json.dumps(itinerary, ensure_ascii=False),
            ),
        )
        db.commit()
        row_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
        logger.info("行程历史已保存: id=%s, dest=%s", row_id, itinerary.get("destination", ""))
        return row_id
    except Exception:
        logger.exception("行程历史保存失败")
        return 0


@router.get("/list")
async def list_trips(device_id: str, limit: int = 20, offset: int = 0):
    """获取行程历史列表。"""
    db = get_db()
    rows = db.execute(
        "SELECT id, title, destination, departure_city, days, group_size, "
        "composition, budget_total, status, created_at "
        "FROM trip_history WHERE device_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (device_id, limit, offset),
    ).fetchall()
    total = db.execute(
        "SELECT COUNT(*) FROM trip_history WHERE device_id=?", (device_id,)
    ).fetchone()[0]
    db.close()
    return {"trips": [dict(r) for r in rows], "total": total}


@router.get("/{trip_id}")
async def get_trip_detail(trip_id: int):
    """获取行程详情（含完整 JSON）。"""
    db = get_db()
    row = db.execute("SELECT * FROM trip_history WHERE id=?", (trip_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="行程不存在")
    result = dict(row)
    if result.get("itinerary_json"):
        result["itinerary"] = json.loads(result["itinerary_json"])
    return result


@router.put("/{trip_id}/status")
async def update_trip_status(trip_id: int, status: str):
    """更新行程状态：planned / in_progress / completed。"""
    if status not in ("planned", "in_progress", "completed"):
        raise HTTPException(status_code=400, detail="status 必须是 planned/in_progress/completed")
    db = get_db()
    db.execute(
        "UPDATE trip_history SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, trip_id),
    )
    db.commit()
    db.close()
    return {"ok": True}


@router.delete("/{trip_id}")
async def delete_trip(trip_id: int):
    """删除行程记录。"""
    db = get_db()
    db.execute("DELETE FROM trip_history WHERE id=?", (trip_id,))
    db.commit()
    db.close()
    return {"ok": True}
