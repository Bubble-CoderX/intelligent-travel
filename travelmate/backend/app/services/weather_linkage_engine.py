"""F4+F5+F6: 天气联动引擎——清单调整 + 行程重排 + 餐饮权重。"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── F4: 准备清单动态调整 ──────────────────────────────────

def adjust_checklist_by_weather(weather: dict, existing_checklist: dict) -> dict:
    """
    根据天气数据动态增减清单物品。
    weather: get_weather_forecast() 返回的天气数据
    existing_checklist: generate_checklist() 返回的 {"categories": [...]}
    """
    today = weather.get("days", [{}])[0] if weather.get("days") else {}
    day_weather = today.get("day_weather", "")
    night_weather = today.get("night_weather", "")
    all_weather = f"{day_weather} {night_weather}"

    try:
        day_temp = int(today.get("day_temp", 0) or 0)
    except (ValueError, TypeError):
        day_temp = 20

    # 天气 → 物品映射
    additions: list[tuple[str, str, str]] = []  # (category_name, icon, item)
    removals: list[str] = []

    if any(k in all_weather for k in ("雨", "雷", "阵雨", "暴雨")):
        additions.append(("雨具", "☂️", "折叠雨伞"))
        additions.append(("雨具", "☂️", "防水鞋套"))

    if day_temp >= 33:
        additions.append(("防晒", "🧴", "防晒霜 SPF50+"))
        additions.append(("防晒", "🧴", "遮阳帽"))
        additions.append(("防晒", "🧴", "太阳镜"))
    elif day_temp <= 10:
        additions.append(("保暖", "🧥", "厚外套/羽绒服"))
        additions.append(("保暖", "🧤", "手套围巾"))

    if day_temp >= 28 and day_temp < 33:
        additions.append(("防暑", "🧴", "防晒霜"))
        additions.append(("防暑", "💧", "便携水壶"))

    if any(k in all_weather for k in ("大风", "强风", "台风")):
        additions.append(("防风", "🧥", "防风外套"))

    # 湿度高 → 防潮
    if "雾" in all_weather or "霾" in all_weather:
        additions.append(("防护", "😷", "口罩"))

    categories = existing_checklist.get("categories", [])

    # 合并新增物品
    for cat_name, icon, item in additions:
        found = False
        for cat in categories:
            if cat.get("name") == cat_name:
                if item not in cat.get("items", []):
                    cat.setdefault("items", []).append(item)
                found = True
                break
        if not found:
            categories.append({"name": cat_name, "icon": icon, "items": [item]})

    existing_checklist["categories"] = categories
    existing_checklist["weather_adjusted"] = True
    return existing_checklist


# ── F5: 行程智能重排 ──────────────────────────────────────

async def adjust_trip_by_weather(
    device_id: str, city: str, trip_plan: dict, weather: dict
) -> dict:
    """
    检测明天是否有恶劣天气，若有则用 LLM 生成"室内优先"重排建议。
    返回 {"adjusted": bool, "suggestion": str, "adjusted_plan": dict|None}
    """
    days = weather.get("days", [])
    tomorrow = days[1] if len(days) > 1 else None

    if tomorrow is None:
        return {"adjusted": False, "suggestion": "无明日天气数据，无法评估。"}

    tomorrow_weather = tomorrow.get("day_weather", "")
    tomorrow_temp = tomorrow.get("day_temp", "")
    bad_weather_keywords = ("雨", "雷", "暴雨", "大风", "台风", "暴雪")

    is_bad = any(k in tomorrow_weather for k in bad_weather_keywords)
    try:
        is_hot = int(tomorrow_temp) >= 35
    except (ValueError, TypeError):
        is_hot = False

    if not is_bad and not is_hot:
        return {"adjusted": False, "suggestion": f"明日天气({tomorrow_weather} {tomorrow_temp}°C)适宜出行，无需调整。"}

    # 调用 LLM 生成重排建议
    from app.services.llm_client import call_llm

    days_text = json.dumps(trip_plan.get("days", []), ensure_ascii=False, indent=2)[:3000]

    reason = f"明日{tomorrow_weather}，气温{tomorrow_temp}°C" + ("，高温酷暑" if is_hot else "，天气恶劣")
    prompt = (
        f"你是旅行规划助手。{reason}，请对以下行程给出「室内优先」重排建议。\n"
        f"规则：将户外景点移到天气好的天，将室内景点（博物馆、商场、美食街等）提前到明天。\n"
        f"只给出调整建议文本（2-4句话），不要重新生成完整行程。\n\n"
        f"当前行程：\n{days_text}"
    )

    suggestion = await call_llm(
        messages=[{"role": "user", "content": "请给出天气联动的行程调整建议"}],
        system_prompt=prompt,
        temperature=0.5,
        max_tokens=300,
    )

    return {
        "adjusted": True,
        "reason": reason,
        "suggestion": suggestion.strip(),
    }


# ── F6: 餐饮推荐权重调整 ──────────────────────────────────

def get_dining_suggestion_by_weather(weather: dict) -> dict:
    """
    根据当前天气返回餐饮推荐偏好。
    返回 {"temperature_level": "hot|cold|mild", "keywords": [...], "suggestion": str}
    """
    today = weather.get("days", [{}])[0] if weather.get("days") else {}
    try:
        temp = int(today.get("day_temp", 0) or 0)
    except (ValueError, TypeError):
        temp = 20

    if temp >= 33:
        return {
            "temperature_level": "hot",
            "keywords": ["清凉消暑", "冷饮", "甜品", "冰沙", "凉茶", "清淡"],
            "suggestion": "天气炎热，推荐清凉消暑类美食，如绿豆汤、凉粉、冰沙等。",
        }
    elif temp >= 25:
        return {
            "temperature_level": "warm",
            "keywords": ["爽口", "鲜美", "海鲜", "水果", "沙拉"],
            "suggestion": "气温舒适，推荐鲜美爽口的当地特色。",
        }
    elif temp >= 10:
        return {
            "temperature_level": "mild",
            "keywords": ["家常", "特色", "暖胃"],
            "suggestion": "天气凉爽，适合品尝当地正餐和特色小吃。",
        }
    else:
        return {
            "temperature_level": "cold",
            "keywords": ["暖身热食", "火锅", "汤锅", "热饮", "炖菜", "羊肉"],
            "suggestion": "天气寒冷，推荐暖身热食，如火锅、炖汤、羊肉等。",
        }


def inject_dining_context(dining_suggestion: dict) -> str:
    """将餐饮建议格式化为可嵌入 Prompt 的文本。"""
    return (
        f"\n## 天气餐饮偏好\n"
        f"当前气温偏好：{dining_suggestion['temperature_level']}\n"
        f"推荐关键词：{'、'.join(dining_suggestion['keywords'])}\n"
        f"{dining_suggestion['suggestion']}\n"
    )
