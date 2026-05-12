"""行程规划服务：整合 POI + 天气 + 偏好，调用 LLM 生成结构化行程。"""
from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from app.models.database import get_db
from app.models.schemas import BudgetBreakdown, DayPlan, Itinerary, SpotItem, MealItem, TransportItem, HotelItem
from app.services.llm_client import call_llm
from app.services.map_service import search_places
from app.services.memory_service import get_all_preferences
from app.services.weather_service import get_weather_forecast
from app.utils.trip_prompts import TRIP_PLAN_PROMPT, STYLE_INSTRUCTIONS

logger = logging.getLogger(__name__)


def _format_poi_text(city: str) -> str:
    """获取并格式化目的地板块的 POI 数据。"""
    try:
        places = search_places(city, city, 10)
        if not places:
            return "暂无相关地点数据"
        lines = []
        for p in places:
            lines.append(f"- {p['name']}（{p.get('address', '暂无地址')}）")
        return "\n".join(lines)
    except Exception:
        logger.warning("获取 POI 数据失败")
        return "暂无相关地点数据"


def _format_weather_text(city: str) -> str:
    """获取并格式化目的地天气数据。"""
    try:
        data = get_weather_forecast(city)
        days = data.get("days", [])
        if not days:
            return "暂无天气数据"
        lines = [f"更新时间：{data.get('report_time', '未知')}"]
        for d in days:
            lines.append(
                f"- {d['date']}：白天 {d['day_weather']} {d['day_temp']}℃，"
                f"夜间 {d['night_weather']} {d['night_temp']}℃，{d['day_wind']}风"
            )
        return "\n".join(lines)
    except Exception:
        logger.warning("获取天气数据失败")
        return "暂无天气数据"


def _format_preferences_text(device_id: str) -> str:
    """获取并格式化用户偏好数据。"""
    prefs = get_all_preferences(device_id)
    if not prefs:
        return "（暂无旅行偏好记录）"
    lines = []
    for p in prefs:
        lines.append(f"- {p['category']}/{p['key']}：{p['value']}")
    return "\n".join(lines)


def _parse_trip_json(raw: str, destination: str) -> dict:
    """解析 LLM 返回的 JSON，含容错处理。"""
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 尝试从文本中提取 JSON 片段
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 完全无法解析 → 返回降级结果
    logger.warning("LLM 返回无法解析为 JSON，使用降级行程")
    raise ValueError(f"无法解析 LLM 返回的 JSON: {raw[:200]}...")


def _save_trip_to_db(
    device_id: str, destination: str, days: int, itinerary_json: str
) -> str:
    """将生成的行程（JSON 字符串）保存到 SQLite，返回 trip_id。"""
    try:
        conn = get_db()
        cursor = conn.execute(
            """INSERT INTO trip_plans (device_id, destination, days, plan_json)
               VALUES (?, ?, ?, ?)""",
            (device_id, destination, days, itinerary_json),
        )
        conn.commit()
        trip_id = f"trip_{cursor.lastrowid}"
        conn.close()
        logger.info("行程已保存：trip_id=%s", trip_id)
        return trip_id
    except Exception:
        logger.exception("保存行程失败")
        return f"trip_{uuid.uuid4().hex[:8]}"


async def generate_trip_plan(
    device_id: str, destination: str, days: int, style: str = "default"
) -> dict[str, Any]:
    """
    完整行程生成流程：
    收集数据 → 组装 Prompt → 调用 LLM → 解析 JSON → Pydantic 校验 → 存储 → 返回
    """
    poi_text = _format_poi_text(destination)
    weather_text = _format_weather_text(destination)
    preferences_text = _format_preferences_text(device_id)
    style_instructions = STYLE_INSTRUCTIONS.get(style, "")

    prompt = TRIP_PLAN_PROMPT.format(
        destination=destination,
        days=days,
        poi_text=poi_text,
        weather_text=weather_text,
        preferences_text=preferences_text,
        style_instructions=style_instructions,
    )

    raw = await call_llm(
        messages=[{"role": "user", "content": f"请为我规划一份{destination}{days}天的旅行行程"}],
        system_prompt=prompt,
        temperature=0.7,
        max_tokens=3000,
    )

    # 解析 JSON
    try:
        plan_dict = _parse_trip_json(raw, destination)
    except ValueError as exc:
        logger.warning("行程 JSON 解析失败：%s", exc)
        return {
            "trip_id": "",
            "destination": destination,
            "days": days,
            "summary": f"抱歉，生成{destination}行程时遇到了格式问题。请稍后再试。",
            "itinerary_json": None,
        }

    # 注入 trip_id 和 destination
    trip_id = f"trip_{uuid.uuid4().hex[:8]}"
    plan_dict["trip_id"] = trip_id
    plan_dict["destination"] = destination

    # Pydantic 校验（自动补全缺失字段默认值）
    try:
        itinerary = Itinerary(**plan_dict)
    except Exception as e:
        logger.warning("Pydantic 校验失败：%s → 尝试部分修复", e)
        # 尝试手动补全常见缺失字段
        for key in ("trip_id", "destination", "summary"):
            if key not in plan_dict:
                plan_dict[key] = ""
        plan_dict["trip_id"] = trip_id
        plan_dict["destination"] = destination
        if "days" not in plan_dict:
            plan_dict["days"] = []
        if "estimated_budget" not in plan_dict:
            plan_dict["estimated_budget"] = 0
        itinerary = Itinerary(**plan_dict)

    # 存储
    itinerary_json_str = json.dumps(
        itinerary.model_dump(), ensure_ascii=False
    )
    _save_trip_to_db(device_id, destination, days, itinerary_json_str)

    return {
        "trip_id": itinerary.trip_id,
        "destination": destination,
        "days": days,
        "summary": itinerary.summary,
        "itinerary_json": itinerary.model_dump(),
    }


def query_trip_plans(device_id: str, limit: int = 10) -> list[dict]:
    """查询用户的历史行程记录。"""
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT id, destination, days, plan_json, created_at
               FROM trip_plans
               WHERE device_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (device_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        logger.exception("查询行程失败")
        return []


def get_trip_plan(device_id: str, trip_id: str) -> dict | None:
    """查询单个行程详情，trip_id 格式为 trip_{id}。"""
    try:
        real_id = int(trip_id.replace("trip_", ""))
        conn = get_db()
        row = conn.execute(
            """SELECT id, destination, days, plan_json, created_at
               FROM trip_plans
               WHERE device_id = ? AND id = ?""",
            (device_id, real_id),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        logger.exception("查询行程详情失败")
        return None
