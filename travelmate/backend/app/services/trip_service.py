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
from app.services.profile_extractor import get_travel_profile_text, _get_profile_field
from app.services.rag_service import retrieve_knowledge
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
    收集数据(POI+天气+知识库+出行档案) → 组装 Prompt → 调用 LLM → 解析 JSON → 存储
    """
    poi_text = _format_poi_text(destination)
    weather_text = _format_weather_text(destination)
    style_instructions = STYLE_INSTRUCTIONS.get(style, "")

    # ── O2: 知识库 RAG 检索（无则自动调研） ─────────────
    knowledge_text = ""
    try:
        # 先精确匹配目的地名称（避免语义搜索返回其他城市的脏数据）
        knowledge_results = retrieve_knowledge(destination, spot_name=destination, top_k=10)
        if not knowledge_results:
            # 精确匹配无结果 → 自动调研生成并入库
            logger.info("知识库中无「%s」，启动自动调研...", destination)
            from app.services.knowledge_expander import auto_expand
            expand_result = await auto_expand(destination)
            if expand_result.get("status") == "ok":
                logger.info("自动调研完成：%s → %d 个段落", destination, expand_result.get("chunk_count", 0))
                knowledge_results = retrieve_knowledge(destination, spot_name=destination, top_k=10)
        if knowledge_results:
            knowledge_text = "\n\n".join(
                f"### {r.get('spot_name', '')}\n{r.get('text', '')}"
                for r in knowledge_results
            )
        else:
            knowledge_text = "暂无知识库数据，基于AI通用知识推荐。"
    except Exception:
        logger.warning("知识库检索/调研失败，降级为空知识库")
        knowledge_text = "暂无知识库数据，基于AI通用知识推荐。"

    # ── O1: 出行档案注入 ───────────────────────────────
    travel_profile_text = get_travel_profile_text(device_id)

    # ── O2: 健康信息提取 ───────────────────────────────
    allergies = _get_profile_field(device_id, "allergies", [])
    special_needs = _get_profile_field(device_id, "special_needs", [])
    composition = _get_profile_field(device_id, "composition", "")
    child_age = _get_profile_field(device_id, "child_age", "")
    elder_count = _get_profile_field(device_id, "elder_count", "")

    health_parts = []
    if allergies:
        allergy_str = "、".join(allergies) if isinstance(allergies, list) else str(allergies)
        health_parts.append(f"- 过敏史：{allergy_str}")
        if "花粉过敏" in (allergies if isinstance(allergies, list) else []):
            health_parts.append("  → 花粉过敏：避免推荐花海/花卉密集景区")
        if "季节性鼻炎" in (allergies if isinstance(allergies, list) else []):
            health_parts.append("  → 鼻炎：避免推荐沙尘大/油烟重的区域")
    if special_needs:
        needs_str = "、".join(special_needs) if isinstance(special_needs, list) else str(special_needs)
        health_parts.append(f"- 特殊需求：{needs_str}")
        if "携带婴儿" in (special_needs if isinstance(special_needs, list) else []):
            health_parts.append("  → 携带婴儿：每2小时安排休息点，推荐有母婴室的景点")
    if composition == "family_child" and child_age:
        health_parts.append(f"- 带{child_age}岁儿童出行：行程节奏放缓，每天安排休息时间")
    if composition == "family_elder" and elder_count:
        health_parts.append(f"- 带{elder_count}位老人出行：避免爬山/走栈道，优先无障碍景点")

    health_text = "\n".join(health_parts) if health_parts else "无特殊健康或人群需求"

    prompt = TRIP_PLAN_PROMPT.format(
        destination=destination,
        days=days,
        poi_text=poi_text,
        weather_text=weather_text,
        travel_profile_text=travel_profile_text,
        style_instructions=style_instructions,
        knowledge_text=knowledge_text,
        health_text=health_text,
    )

    # 动态 token：天数越多需要越多 token 输出 JSON
    dynamic_tokens = min(3000 + days * 500, 6000)

    raw = await call_llm(
        messages=[{"role": "user", "content": f"请为我规划一份{destination}{days}天的旅行行程"}],
        system_prompt=prompt,
        temperature=0.7,
        max_tokens=dynamic_tokens,
    )

    # 解析 JSON，失败则重试一次（LLM 有时输出不规范）
    try:
        plan_dict = _parse_trip_json(raw, destination)
    except ValueError:
        logger.warning("行程 JSON 首次解析失败，重试一次")
        raw = await call_llm(
            messages=[{
                "role": "user",
                "content": f"请为我规划一份{destination}{days}天的旅行行程。请严格输出JSON格式，不要包裹在代码块中。"
            }],
            system_prompt=prompt,
            temperature=0.3,
            max_tokens=dynamic_tokens,
        )
        try:
            plan_dict = _parse_trip_json(raw, destination)
        except ValueError as exc:
            logger.warning("行程 JSON 重试仍失败：%s", exc)
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

    # ── LLM 输出清洗（校验前执行，避免无意义的失败重试）──
    # 补全顶层缺失字段
    for key in ("trip_id", "destination", "summary"):
        if not plan_dict.get(key):
            plan_dict[key] = ""
    plan_dict["trip_id"] = trip_id
    plan_dict["destination"] = destination
    if "estimated_budget" not in plan_dict:
        plan_dict["estimated_budget"] = 0
    # 清洗每天数据
    for day in plan_dict.get("days", []):
        if not isinstance(day, dict):
            continue
        hotel = day.get("hotel")
        if hotel and isinstance(hotel, dict) and not hotel.get("name"):
            day["hotel"] = None
        elif hotel is None:
            day["hotel"] = None
        for arr_key in ("spots", "meals", "transport"):
            if not day.get(arr_key):
                day[arr_key] = []
        if not day.get("day_index"):
            day["day_index"] = plan_dict["days"].index(day) + 1
        if not day.get("theme"):
            day["theme"] = f"Day {day['day_index']}"
    # 修复预算：负数→0，other 重算
    bb = plan_dict.setdefault("budget_breakdown", {})
    for k in ("transport", "hotel", "meals", "tickets", "other"):
        if bb.get(k, 0) < 0:
            bb[k] = 0
    total = bb.get("total", 0)
    if total > 0:
        bb["other"] = max(0, total - bb.get("transport", 0) - bb.get("hotel", 0) - bb.get("meals", 0) - bb.get("tickets", 0))
        bb["total"] = bb["transport"] + bb["hotel"] + bb["meals"] + bb["tickets"] + bb["other"]

    # Pydantic 校验
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
