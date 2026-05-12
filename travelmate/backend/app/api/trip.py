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
    """导出行程为 PDF 或 JSON。"""
    conn = get_db()
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
        pdf_bytes = itinerary_to_pdf_bytes(detail)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{trip_id}.pdf"'},
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
    checklist = await generate_checklist(destination, days)
    return {"trip_id": trip_id, "checklist": checklist}
