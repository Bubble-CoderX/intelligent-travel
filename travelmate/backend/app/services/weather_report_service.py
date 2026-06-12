"""F7: 天气日报/周报生成服务。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

DAILY_REPORT_PROMPT = """你是「AI智游伴」的天气播报员。请基于以下天气数据生成一份简洁的天气日报。

## 天气数据
{weather_data}

## 输出要求
- 200字以内的天气日报
- 包含：当前天气概况、气温范围、出行建议
- 语气温暖自然，像朋友在提醒你
- 直接输出内容，不要标题前缀"""


WEEKLY_REPORT_PROMPT = """你是「AI智游伴」的天气分析师。请基于以下7天天气数据生成一份天气周报。

## 近7天天气数据
{weather_data}

## 输出要求
- 300字以内的天气周报
- 包含：本周天气趋势总结、气温变化、降雨分布、下周出行建议
- 如有明显趋势（如持续升温、连阴雨等）要特别指出
- 语气专业但易懂
- 直接输出内容，不要标题前缀"""


async def generate_daily_weather_report(city: str) -> str:
    """基于当日天气数据生成日报。"""
    from app.services.weather_service import get_weather_with_fallback

    weather = await get_weather_with_fallback(city)
    today = weather.get("days", [{}])[0] if weather.get("days") else {}

    weather_text = (
        f"城市：{city}\n"
        f"白天：{today.get('day_weather', '未知')}，{today.get('day_temp', '?')}°C\n"
        f"夜间：{today.get('night_weather', '未知')}，{today.get('night_temp', '?')}°C\n"
        f"风力：{today.get('day_wind', '未知')}"
    )

    prompt = DAILY_REPORT_PROMPT.format(weather_data=weather_text)
    report = await call_llm(
        messages=[{"role": "user", "content": f"生成{city}今日天气日报"}],
        system_prompt=prompt,
        temperature=0.6,
        max_tokens=300,
    )
    return report.strip()


async def generate_weekly_weather_report(city: str) -> str:
    """基于近7天历史数据生成周报。"""
    from app.services.weather_service import get_weather_history, get_weather_with_fallback

    # 尝试从历史记录获取
    history = get_weather_history(city, limit=7)

    if len(history) >= 3:
        weather_text = "\n".join(
            f"- {h['fetched_at'][:10]}：{h['weather']}，{h['temperature']}°C，风{h['wind_power']}"
            for h in reversed(history)
        )
    else:
        # 历史不足，用预报数据
        forecast = await get_weather_with_fallback(city)
        days = forecast.get("days", [])
        weather_text = "\n".join(
            f"- {d.get('date', '?')}：白天{d.get('day_weather', '?')} {d.get('day_temp', '?')}°C / 夜间{d.get('night_weather', '?')} {d.get('night_temp', '?')}°C"
            for d in days
        )

    prompt = WEEKLY_REPORT_PROMPT.format(weather_data=weather_text)
    report = await call_llm(
        messages=[{"role": "user", "content": f"生成{city}天气周报"}],
        system_prompt=prompt,
        temperature=0.6,
        max_tokens=400,
    )
    return report.strip()
