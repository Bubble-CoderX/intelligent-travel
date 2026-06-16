import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.database import get_db
from app.services.checklist_service import generate_checklist
from app.services.export_service import itinerary_to_pdf_bytes, itinerary_to_markdown
from app.models.schemas import Itinerary, TripDetailResponse

router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("/{device_id}/list")
async def list_trips(device_id: str):
    """获取设备的行程列表。"""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, destination, days, plan_json, created_at FROM trip_plans "
        "WHERE device_id = ? ORDER BY created_at DESC LIMIT 20",
        (device_id,),
    ).fetchall()
    conn.close()

    items = []
    for r in rows:
        try:
            plan = json.loads(r["plan_json"]) if r["plan_json"] else {}
        except json.JSONDecodeError:
            plan = {}
        items.append({
            "trip_id": plan.get("trip_id", str(r["id"])),
            "destination": r["destination"],
            "summary": plan.get("summary", ""),
            "days": r["days"],
            "created_at": r["created_at"],
        })
    return {"total": len(items), "items": items}


def _find_trip_row(conn, trip_id: str):
    """通过 trip_id（JSON 内字段）或自增 id 查找行程。"""
    # 优先尝试按自增 id 查找（支持 trip_123 格式）
    if trip_id.startswith("trip_"):
        try:
            real_id = int(trip_id.replace("trip_", ""))
            row = conn.execute("SELECT * FROM trip_plans WHERE id = ?", (real_id,)).fetchone()
            if row:
                return row
        except ValueError:
            pass
    # 回退：在 plan_json 中搜索 trip_id
    rows = conn.execute("SELECT * FROM trip_plans ORDER BY id DESC").fetchall()
    for row in rows:
        try:
            plan = json.loads(row["plan_json"]) if row["plan_json"] else {}
            if plan.get("trip_id") == trip_id:
                return row
        except (json.JSONDecodeError, KeyError):
            continue
    return None


@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    """获取单个行程详情。"""
    conn = get_db()
    row = _find_trip_row(conn, trip_id)
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="行程不存在")
    try:
        itinerary = Itinerary(**json.loads(row["plan_json"]))
    except Exception:
        raise HTTPException(status_code=500, detail="行程数据损坏")
    return TripDetailResponse(
        trip_id=trip_id,
        itinerary=itinerary,
        created_at=row["created_at"],
    )


@router.get("/{trip_id}/export")
async def export_trip(trip_id: str, format: str = "json"):
    """导出行程为 PDF 或 JSON。优先从 trip_history 读取（含清单+照片）。"""
    conn = get_db()

    # 优先从 trip_history 读取（数据更完整，含清单+照片）
    # 尝试数字 ID
    real_id = 0
    try:
        real_id = int(trip_id.replace("trip_", ""))
    except (ValueError, TypeError):
        pass

    history_row = None
    if real_id > 0:
        history_row = conn.execute(
            "SELECT itinerary_json, created_at FROM trip_history WHERE id=?", (real_id,)
        ).fetchone()

    # UUID 格式：在 trip_plans 的 plan_json 中搜索
    if not history_row:
        row = conn.execute(
            "SELECT plan_json, created_at FROM trip_plans WHERE plan_json LIKE ?",
            (f'%{trip_id}%',),
        ).fetchone()
        if row and row["plan_json"]:
            try:
                plan = json.loads(row["plan_json"])
                plan_id = plan.get("trip_id", "")
                if plan_id == trip_id:
                    history_row = {"itinerary_json": row["plan_json"], "created_at": row["created_at"]}
            except Exception:
                pass

    if history_row and history_row["itinerary_json"]:
        try:
            itinerary = Itinerary(**json.loads(history_row["itinerary_json"]))
            logger.info("PDF导出: checklist=%s, categories=%d",
                        'YES' if itinerary.checklist else 'NO',
                        len(itinerary.checklist.get("categories", [])) if itinerary.checklist else 0)
            detail = TripDetailResponse(trip_id=trip_id, itinerary=itinerary, created_at=history_row["created_at"])
            # PDF 文件名用行程标题（URL编码避免中文乱码）
            title = itinerary.summary or f"{itinerary.destination}{len(itinerary.days)}日游"
            from urllib.parse import quote
            safe_title = quote(title[:30])
            if format == "pdf":
                pdf_bytes = itinerary_to_pdf_bytes(detail)
                return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_title}.pdf"})
            return {"trip_id": trip_id, "itinerary": itinerary.model_dump(), "created_at": history_row["created_at"]}
        except Exception:
            pass

    # 回退到 trip_plans
    row = _find_trip_row(conn, trip_id)
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="行程不存在")

    try:
        itinerary = Itinerary(**json.loads(row["plan_json"]))
    except Exception:
        raise HTTPException(status_code=500, detail="行程数据损坏")

    detail = TripDetailResponse(
        trip_id=trip_id,
        itinerary=itinerary,
        created_at=row["created_at"],
    )

    if format == "pdf":
        title = itinerary.summary or f"{itinerary.destination}{len(itinerary.days)}日游"
        from urllib.parse import quote
        safe_title = quote(title[:30])
        pdf_bytes = itinerary_to_pdf_bytes(detail)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_title}.pdf"},
        )

    # 默认返回 JSON
    return detail.model_dump()


@router.get("/{trip_id}/checklist")
async def get_trip_checklist(trip_id: str):
    """为指定行程生成旅行准备清单。"""
    conn = get_db()
    row = _find_trip_row(conn, trip_id)
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="行程不存在")
    try:
        itinerary = json.loads(row["plan_json"])
    except Exception:
        raise HTTPException(status_code=500, detail="行程数据损坏")
    destination = itinerary.get("destination", "")
    days = itinerary.get("days", 1) if isinstance(itinerary.get("days"), int) else len(itinerary.get("days", [])) or 1
    composition = itinerary.get("composition", "")
    allergies_raw = itinerary.get("allergies", "")
    allergies = [a.strip() for a in allergies_raw.split(",") if a.strip()] if isinstance(allergies_raw, str) and allergies_raw else (allergies_raw if isinstance(allergies_raw, list) else [])
    weather = itinerary.get("weather", "")
    checklist = await generate_checklist(destination, days, weather=weather, composition=composition, allergies=allergies)
    return {"trip_id": trip_id, "checklist": checklist}
