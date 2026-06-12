"""天气智能 API：日报周报(F7) + 定时巡检(F8) + TCI体感指数(F9) + 异常检测(F3)"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/weather-intel", tags=["weather-intel"])


# ── F3: 手动触发异常检测 ──────────────────────────────────

class AnomalyRequest(BaseModel):
    city: str = Field(..., description="城市名称")
    device_id: str = Field(..., description="设备 ID")


@router.post("/detect-anomalies")
async def api_detect_anomalies(req: AnomalyRequest):
    """手动触发天气异常检测并推送。"""
    from app.services.weather_anomaly_detector import detect_and_push
    report = await detect_and_push(req.city, req.device_id)
    return {
        "city": report.city,
        "has_anomaly": report.has_anomaly,
        "anomalies": [
            {"rule": a.rule_name, "severity": a.severity, "title": a.title, "detail": a.detail, "suggestion": a.suggestion}
            for a in report.anomalies
        ],
    }


# ── F7: 天气日报/周报 ────────────────────────────────────

@router.get("/daily-report")
async def api_daily_report(city: str = "广州"):
    """生成天气日报。"""
    from app.services.weather_report_service import generate_daily_weather_report
    report = await generate_daily_weather_report(city)
    return {"city": city, "type": "daily", "report": report}


@router.get("/weekly-report")
async def api_weekly_report(city: str = "广州"):
    """生成天气周报。"""
    from app.services.weather_report_service import generate_weekly_weather_report
    report = await generate_weekly_weather_report(city)
    return {"city": city, "type": "weekly", "report": report}


# ── F8: 定时巡检管理 ──────────────────────────────────────

class PatrolRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    city: str = Field(..., description="城市名称")


@router.post("/setup-patrol")
async def api_setup_patrol(req: PatrolRequest):
    """设置天气巡检定时任务（每天08:00和20:00）。"""
    from app.services.proactive_service import setup_weather_patrol
    job_ids = setup_weather_patrol(req.device_id, req.city)
    return {"status": "ok", "job_ids": job_ids, "message": f"已设置{req.city}天气巡检（08:00/20:00）"}


# ── F9: TCI 旅行体感指数 ──────────────────────────────────

class TCIRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    city: str = Field(..., description="城市名称")
    user_group: str = Field(default="", description="用户群体：老人/儿童/青年")
    trip_intensity: str = Field(default="", description="行程强度：紧凑/休闲")


@router.post("/comfort-index")
async def api_comfort_index(req: TCIRequest):
    """计算 TCI 旅行体感指数。"""
    from app.services.comfort_index_service import get_travel_comfort_index
    result = await get_travel_comfort_index(
        req.device_id, req.city,
        user_group=req.user_group,
        trip_intensity=req.trip_intensity,
    )
    return result


# ── F5: 行程天气重排建议 ──────────────────────────────────

class TripAdjustRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    city: str = Field(..., description="城市名称")
    trip_plan: dict = Field(..., description="当前行程数据")


@router.post("/trip-adjust")
async def api_trip_adjust(req: TripAdjustRequest):
    """根据天气给出行程调整建议。"""
    from app.services.weather_linkage_engine import adjust_trip_by_weather
    from app.services.weather_service import get_weather_with_fallback
    weather = await get_weather_with_fallback(req.city)
    result = await adjust_trip_by_weather(req.device_id, req.city, req.trip_plan, weather)
    return result


# ── F4: 清单动态调整 ──────────────────────────────────────

class ChecklistAdjustRequest(BaseModel):
    city: str = Field(..., description="城市名称")
    checklist: dict = Field(..., description="现有清单数据")


@router.post("/adjust-checklist")
async def api_adjust_checklist(req: ChecklistAdjustRequest):
    """根据天气动态调整准备清单。"""
    from app.services.weather_linkage_engine import adjust_checklist_by_weather
    from app.services.weather_service import get_weather_with_fallback
    weather = await get_weather_with_fallback(req.city)
    result = adjust_checklist_by_weather(weather, req.checklist)
    return result


# ── F6: 餐饮推荐 ──────────────────────────────────────────

@router.get("/dining-suggestion")
async def api_dining_suggestion(city: str = "广州"):
    """获取天气餐饮推荐。"""
    from app.services.weather_linkage_engine import get_dining_suggestion_by_weather
    from app.services.weather_service import get_weather_with_fallback
    weather = await get_weather_with_fallback(city)
    return get_dining_suggestion_by_weather(weather)
