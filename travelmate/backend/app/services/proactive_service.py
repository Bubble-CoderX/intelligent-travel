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


# ── 调度器管理 ──────────────────────────────────────────────

def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        logger.info("APScheduler 调度器已启动")


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler 调度器已关闭")
