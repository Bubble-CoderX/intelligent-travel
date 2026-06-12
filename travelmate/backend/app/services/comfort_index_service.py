"""F9: TCI 旅行体感指数——天气×人群×行程×时段四维融合评估。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ComfortContext:
    """体感指数的输入上下文。"""
    city: str
    temperature: int = 20
    weather_desc: str = ""
    humidity: str = ""
    wind: str = ""
    hour: int = 12
    is_holiday: bool = False
    trip_intensity: str = ""   # "紧凑" | "休闲" | ""
    user_group: str = ""       # "老人" | "儿童" | "青年" | ""


@dataclass
class TCIResult:
    """TCI 计算结果。"""
    score: int           # 0-100
    level: str           # "极佳" | "良好" | "一般" | "较差" | "不宜"
    level_emoji: str     # "🟢" | "🔵" | "🟡" | "🟠" | "🔴"
    dimensions: dict     # 各维度得分
    advice: str = ""     # LLM 生成的个性化建议


# ── 纯计算函数（无 LLM 依赖） ─────────────────────────────

def _calc_weather_score(temp: int, weather_desc: str, wind: str) -> int:
    """天气维度评分（0-100）。"""
    # 温度舒适度（最优区间 18-26°C）
    if 18 <= temp <= 26:
        temp_score = 100
    elif 12 <= temp < 18 or 26 < temp <= 30:
        temp_score = 80
    elif 8 <= temp < 12 or 30 < temp <= 33:
        temp_score = 60
    elif 5 <= temp < 8 or 33 < temp <= 36:
        temp_score = 40
    else:
        temp_score = 20

    # 天气状况惩罚
    weather_penalty = 0
    bad_weather = {"暴雨": 30, "大雨": 25, "中雨": 15, "小雨": 10, "雷": 25, "大风": 20, "台风": 40}
    for keyword, penalty in bad_weather.items():
        if keyword in weather_desc:
            weather_penalty = max(weather_penalty, penalty)

    return max(0, min(100, temp_score - weather_penalty))


def _calc_crowd_score(is_holiday: bool, hour: int) -> int:
    """人群/时段维度评分（0-100）。"""
    score = 80  # 基准分

    if is_holiday:
        score -= 20  # 节假日人多

    # 时段修正
    if 10 <= hour <= 15:
        score -= 10  # 午间高峰
    elif 6 <= hour <= 8 or 17 <= hour <= 19:
        score += 5   # 早晚较舒适

    return max(0, min(100, score))


def _calc_trip_score(intensity: str, temp: int) -> int:
    """行程维度评分（0-100）。"""
    base = 80

    if intensity == "紧凑":
        if temp >= 33 or temp <= 5:
            base -= 25  # 极端天气不适合紧凑行程
        else:
            base -= 5
    elif intensity == "休闲":
        base += 5  # 休闲行程对天气容忍度更高

    return max(0, min(100, base))


def _calc_time_score(hour: int, weather_desc: str) -> int:
    """时段维度评分（0-100）。"""
    if 6 <= hour <= 10:
        base = 90  # 上午最舒适
    elif 10 < hour <= 14:
        base = 70  # 中午偏热
    elif 14 < hour <= 18:
        base = 80  # 下午舒适
    elif 18 < hour <= 21:
        base = 75  # 傍晚还行
    else:
        base = 50  # 夜间/凌晨

    if "雨" in weather_desc and hour >= 18:
        base -= 15  # 晚上+下雨体验差

    return max(0, min(100, base))


# ── TCI 主计算 ────────────────────────────────────────────

def calculate_tci(ctx: ComfortContext) -> TCIResult:
    """
    计算 TCI 旅行体感指数（纯计算，无 LLM）。
    加权公式：weather*0.4 + crowd*0.2 + trip*0.2 + time*0.2
    """
    weather_s = _calc_weather_score(ctx.temperature, ctx.weather_desc, ctx.wind)
    crowd_s = _calc_crowd_score(ctx.is_holiday, ctx.hour)
    trip_s = _calc_trip_score(ctx.trip_intensity, ctx.temperature)
    time_s = _calc_time_score(ctx.hour, ctx.weather_desc)

    dimensions = {
        "weather": weather_s,
        "crowd": crowd_s,
        "trip": trip_s,
        "time": time_s,
    }

    total = int(weather_s * 0.4 + crowd_s * 0.2 + trip_s * 0.2 + time_s * 0.2)

    if total >= 85:
        level, emoji = "极佳", "🟢"
    elif total >= 70:
        level, emoji = "良好", "🔵"
    elif total >= 55:
        level, emoji = "一般", "🟡"
    elif total >= 35:
        level, emoji = "较差", "🟠"
    else:
        level, emoji = "不宜", "🔴"

    return TCIResult(score=total, level=level, level_emoji=emoji, dimensions=dimensions)


# ── LLM 生成个性化建议 ────────────────────────────────────

async def generate_dynamic_advice(tci: TCIResult, ctx: ComfortContext) -> str:
    """调用 LLM 生成个性化的出行建议。"""
    from app.services.llm_client import call_llm

    dim_text = "、".join(f"{k}={v}分" for k, v in tci.dimensions.items())
    group_hint = f"（用户群体：{ctx.user_group}）" if ctx.user_group else ""

    prompt = (
        f"你是旅行体感顾问。TCI评分为{tci.score}分（{tci.level}），{group_hint}\n"
        f"各维度：{dim_text}\n"
        f"城市：{ctx.city}，天气：{ctx.weather_desc} {ctx.temperature}°C，时段：{ctx.hour}点\n"
        f"行程强度：{ctx.trip_intensity or '未指定'}\n\n"
        f"请给出2-3句简洁的出行建议，包括是否适合外出、注意事项、替代方案。"
        f"语气轻松自然，像朋友在给建议。"
    )

    advice = await call_llm(
        messages=[{"role": "user", "content": "请给出旅行体感建议"}],
        system_prompt=prompt,
        temperature=0.6,
        max_tokens=200,
    )
    return advice.strip()


# ── 完整流程函数 ──────────────────────────────────────────

async def get_travel_comfort_index(
    device_id: str,
    city: str,
    user_group: str = "",
    trip_intensity: str = "",
) -> dict:
    """
    完整 TCI 流程：获取天气 → 构建上下文 → 计算 → LLM建议。
    """
    from app.services.weather_service import get_weather_with_fallback

    weather = await get_weather_with_fallback(city)
    today = weather.get("days", [{}])[0] if weather.get("days") else {}

    try:
        temp = int(today.get("day_temp", 20) or 20)
    except (ValueError, TypeError):
        temp = 20

    ctx = ComfortContext(
        city=city,
        temperature=temp,
        weather_desc=today.get("day_weather", ""),
        humidity="",
        wind=today.get("day_wind", ""),
        hour=datetime.now().hour,
        trip_intensity=trip_intensity,
        user_group=user_group,
    )

    tci = calculate_tci(ctx)
    advice = await generate_dynamic_advice(tci, ctx)
    tci.advice = advice

    return {
        "city": city,
        "score": tci.score,
        "level": tci.level,
        "level_emoji": tci.level_emoji,
        "dimensions": tci.dimensions,
        "advice": tci.advice,
        "weather": {"temp": temp, "desc": ctx.weather_desc, "wind": ctx.wind},
    }
