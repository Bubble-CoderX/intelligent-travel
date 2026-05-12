"""主动服务管理器：WebSocket 连接管理 + 天气定时提醒 + 景点到达问候。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import WebSocket

from app.services.llm_client import call_llm
from app.services.memory_service import get_all_preferences
from app.services.weather_service import get_weather_forecast

logger = logging.getLogger(__name__)

# ── WebSocket 连接池 ──────────────────────────────────────────
_connections: dict[str, WebSocket] = {}

# ── APScheduler 实例 ──────────────────────────────────────────
_scheduler = AsyncIOScheduler()


def register_ws(device_id: str, ws: WebSocket) -> None:
    _connections[device_id] = ws
    logger.info("WebSocket 已注册：%s（当前 %d 个连接）", device_id, len(_connections))


def unregister_ws(device_id: str) -> None:
    _connections.pop(device_id, None)
    logger.info("WebSocket 已注销：%s（剩余 %d 个连接）", device_id, len(_connections))


async def push_message(device_id: str, content: str, msg_type: str = "proactive") -> bool:
    """向指定设备推送消息。返回是否成功。"""
    ws = _connections.get(device_id)
    if ws is None:
        logger.warning("设备 %s 未连接，无法推送", device_id)
        return False
    try:
        payload = json.dumps({"type": msg_type, "content": content, "timestamp": datetime.now().isoformat()}, ensure_ascii=False)
        await ws.send_text(payload)
        return True
    except Exception:
        logger.exception("推送消息失败：%s", device_id)
        unregister_ws(device_id)
        return False


# ── 天气定时提醒 ──────────────────────────────────────────────

async def _weather_check_job(device_id: str, city: str) -> None:
    """定时天气检查任务：查天气 → 有雨则推送提醒。"""
    try:
        data = get_weather_forecast(city)
        days = data.get("days", [])
        if not days:
            return

        today = days[0]
        weather = today.get("day_weather", "")
        night_weather = today.get("night_weather", "")

        rain_keywords = ["雨", "雷", "阵雨", "暴雨", "小雨", "中雨", "大雨"]
        has_rain = any(kw in weather or kw in night_weather for kw in rain_keywords)

        if not has_rain:
            return

        prefs = get_all_preferences(device_id)
        pref_text = "、".join(f"{p['key']}={p['value']}" for p in prefs[:3]) if prefs else "无"

        prompt = f"""你是一位贴心的旅行助手。明天{city}有雨（白天{weather}，夜间{night_weather}），请用简短友好的语言提醒用户注意天气。
用户的偏好：{pref_text}
要求：1-2句话，温暖贴心，给出实用建议（带伞/穿什么等）。"""

        reply = await call_llm(
            messages=[{"role": "user", "content": f"明天{city}有雨，提醒我一下"}],
            system_prompt=prompt,
            temperature=0.7,
            max_tokens=200,
        )

        await push_message(device_id, reply, msg_type="weather_alert")
        logger.info("天气提醒已推送：%s → %s", device_id, city)

    except Exception:
        logger.exception("天气定时检查失败：%s", device_id)


def set_weather_reminder(device_id: str, city: str, hour: int = 20, minute: int = 0) -> str:
    """设置每日天气定时提醒。返回 job_id。"""
    job_id = f"weather_{device_id}_{city}"
    existing = _scheduler.get_job(job_id)
    if existing:
        existing.remove()

    _scheduler.add_job(
        _weather_check_job,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[device_id, city],
        id=job_id,
        replace_existing=True,
    )
    logger.info("天气提醒已设置：%s → %s 每天 %02d:%02d", device_id, city, hour, minute)
    return job_id


def remove_weather_reminder(job_id: str) -> bool:
    job = _scheduler.get_job(job_id)
    if job:
        job.remove()
        return True
    return False


# ── 景点到达问候 ──────────────────────────────────────────────

async def send_arrival_greeting(device_id: str, spot_name: str, city: str = "") -> str:
    """生成并推送景点到达问候。返回问候消息。"""
    prefs = get_all_preferences(device_id)
    pref_text = "、".join(f"{p['key']}={p['value']}" for p in prefs[:3]) if prefs else "无"

    location_hint = f"在{city}" if city else ""
    prompt = f"""你是一位热情的导游「AI智游伴」。用户刚到达{location_hint}的「{spot_name}」。
用户偏好：{pref_text}
请用1-2句话热情地打招呼，可以简短介绍这个景点的一个亮点或小贴士。"""

    greeting = await call_llm(
        messages=[{"role": "user", "content": f"我到{spot_name}了"}],
        system_prompt=prompt,
        temperature=0.8,
        max_tokens=150,
    )

    await push_message(device_id, greeting, msg_type="arrival_greeting")
    return greeting


# ── 会话启动问候 ──────────────────────────────────────────────

GREETING_PROMPT = """你是「AI智游伴」的个性化问候生成器。根据以下上下文生成一条温暖的主动开场白。

## 基础信息
- 时间：{time_of_day}
- 天气：{weather}

## 用户画像
- 是新用户：{is_new_user}
- 旅行偏好：{preferences}
- 最近行程：{recent_trips}

## 问候模板（按用户类型选择）

### 如果是新用户（无偏好、无行程）：
1. 时间问候 + 所在地天气
2. 一句话介绍自己能做什么（规划行程、查天气、推荐景点、讲解故事）
3. 一个引导性问题，例如"最近有想去的地方吗？"

### 如果是回访用户（有偏好或行程）：
1. 时间问候 + 所在地天气
2. 提到 1-2 条用户偏好（自然融入，不要生硬列举）
3. 如果有未完成的行程规划，询问是否继续
4. 一个开放式的服务邀请

## 要求
- 语气温暖自然，像老朋友在聊天，不要像机器人客服
- 总长度 2-4 句话，不要太长
- 每次生成的问候语要有变化，不要每次一样
- 不要用"尊贵的用户""您好"等客服腔
- 天气信息自然地融入，不要单独报天气数据
- 直接输出问候语，不要加前缀如"问候："
"""


def _time_greeting() -> str:
    h = datetime.now().hour
    if h < 6: return "深夜好"
    if h < 12: return "早上好"
    if h < 14: return "中午好"
    if h < 18: return "下午好"
    return "晚上好"


async def generate_greeting(device_id: str) -> dict[str, Any]:
    """生成个性化开场问候。返回 {"greeting": "...", "is_new_user": bool}"""
    from app.services.trip_service import query_trip_plans

    # 收集上下文
    prefs = get_all_preferences(device_id)
    recent_trips = query_trip_plans(device_id, limit=2)

    # 判断用户类型
    total_prefs = len(prefs)
    total_trips = len(recent_trips)
    is_new = (total_prefs == 0 and total_trips == 0)

    # 天气信息
    weather_text = "未知"
    city = None
    for p in prefs:
        if p.get("category") == "location" and p.get("key") == "home_city":
            city = p.get("value")
            break
    if city:
        try:
            import asyncio
            data = await asyncio.to_thread(get_weather_forecast, city)
            today = data.get("days", [{}])[0] if data.get("days") else {}
            weather_text = f"{city} {today.get('day_weather', '')} {today.get('day_temp', '')}°C"
        except Exception:
            weather_text = city if city else "未知"
    else:
        try:
            import asyncio
            data = await asyncio.to_thread(get_weather_forecast, "深圳")
            today = data.get("days", [{}])[0] if data.get("days") else {}
            weather_text = f"深圳 {today.get('day_weather', '')} {today.get('day_temp', '')}°C"
        except Exception:
            weather_text = "（天气未知）"

    # 格式化偏好和行程
    pref_text = "、".join(f"{p['key']}={p['value']}" for p in prefs[:5]) if prefs else "无"
    trip_text = " | ".join(t.get("destination", "") for t in recent_trips[:2]) if recent_trips else "无"

    prompt = GREETING_PROMPT.format(
        time_of_day=_time_greeting(),
        weather=weather_text,
        is_new_user=str(is_new),
        preferences=pref_text,
        recent_trips=trip_text,
    )

    greeting = await call_llm(
        messages=[{"role": "user", "content": "生成一条个性化开场问候"}],
        system_prompt=prompt,
        temperature=0.8,
        max_tokens=300,
    )

    return {"greeting": greeting, "is_new_user": is_new}


# ── 调度器管理 ──────────────────────────────────────────────

def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        logger.info("APScheduler 调度器已启动")


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler 调度器已关闭")
