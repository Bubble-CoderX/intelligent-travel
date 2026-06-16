"""主动服务管理器：WebSocket 连接管理 + 天气定时播报 + 景点到达问候。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx
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


# ── 位置解析 ──────────────────────────────────────────────────

def _ip_to_city(ip: str) -> str | None:
    """通过 IP 获取城市（ip-api.com 免费服务，无需 API Key）。"""
    if ip in ("127.0.0.1", "::1", ""):
        return None
    try:
        resp = httpx.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = resp.json()
        if data.get("status") == "success":
            return data.get("city")
    except Exception:
        pass
    return None


def resolve_location(device_id: str, client_ip: str | None = None) -> str | None:
    """解析用户位置：偏好城市 > IP 定位。"""
    prefs = get_all_preferences(device_id)
    for p in prefs:
        if p.get("category") == "location" and p.get("key") == "home_city":
            return p.get("value")
    if client_ip:
        city = _ip_to_city(client_ip)
        if city:
            return city
    return None


# ── 天气定时播报 ──────────────────────────────────────────────

BROADCAST_HOURS = [7, 12, 19, 0]  # 每天 7:00 / 12:00 / 19:00 / 0:00

BROADCAST_PROMPT = """你是「AI智游伴」的天气播报员。请根据以下天气数据，生成一条温暖的天气播报。

## 天气数据
- 城市：{city}
- 时段：{time_label}
- 白天天气：{day_weather}，温度 {day_temp}°C
- 夜间天气：{night_weather}，温度 {night_temp}°C
- 风力：{day_wind}

## 用户偏好
{preferences}

## 播报要求
- 语气温暖自然，像朋友在聊天
- 1-2句话，简短实用
- 根据时段给出穿衣/出行/带伞等建议
- 如果是早晚时段（7点/19点），可以加上"新的一天加油"或"辛苦了"之类的情感表达
- 直接输出播报内容，不要加任何前缀"""


def _time_label(hour: int) -> str:
    if hour == 7:
        return "早晨"
    elif hour == 12:
        return "中午"
    elif hour == 19:
        return "傍晚"
    else:
        return "深夜"


async def _weather_broadcast_job(device_id: str, city: str, hour: int) -> None:
    """定时天气播报任务：获取天气 → LLM 生成播报 → WebSocket 推送。"""
    try:
        data = get_weather_forecast(city)
        days = data.get("days", [])
        if not days:
            return

        today = days[0]
        day_weather = today.get("day_weather", "未知")
        night_weather = today.get("night_weather", "未知")
        day_temp = today.get("day_temp", "?")
        night_temp = today.get("night_temp", "?")
        day_wind = today.get("day_wind", "未知")

        prefs = get_all_preferences(device_id)
        pref_text = "、".join(f"{p['key']}={p['value']}" for p in prefs[:3]) if prefs else "无"

        prompt = BROADCAST_PROMPT.format(
            city=city,
            time_label=_time_label(hour),
            day_weather=day_weather,
            night_weather=night_weather,
            day_temp=day_temp,
            night_temp=night_temp,
            day_wind=day_wind,
            preferences=pref_text,
        )

        reply = await call_llm(
            messages=[{"role": "user", "content": f"{city}今天天气怎么样"}],
            system_prompt=prompt,
            temperature=0.7,
            max_tokens=250,
        )

        await push_message(device_id, reply, msg_type="weather_alert")
        logger.info("天气播报已推送：%s → %s（%s）", device_id, city, _time_label(hour))

    except Exception:
        logger.exception("天气播报失败：%s", device_id)


def setup_weather_broadcasts(device_id: str, city: str) -> list[str]:
    """设置每天 4 个时段的天气播报。返回所有 job_id 列表。"""
    job_ids = []
    for hour in BROADCAST_HOURS:
        job_id = f"weather_{device_id}_{city}_{hour}"
        _scheduler.add_job(
            _weather_broadcast_job,
            trigger=CronTrigger(hour=hour, minute=0),
            args=[device_id, city, hour],
            id=job_id,
            replace_existing=True,
        )
        job_ids.append(job_id)
    logger.info("天气播报已设置：%s → %s 每天 %s", device_id, city, BROADCAST_HOURS)
    return job_ids


def remove_weather_broadcasts(device_id: str) -> int:
    """移除该设备的所有天气播报任务。返回移除数量。"""
    count = 0
    for hour in BROADCAST_HOURS:
        for city_suffix in ["", "_广州", "_深圳", "_北京", "_上海", "_杭州", "_成都", "_武汉", "_南京", "_西安", "_重庆"]:
            job_id = f"weather_{device_id}_{city_suffix}_{hour}"
            job = _scheduler.get_job(job_id)
            if job:
                job.remove()
                count += 1
    return count


# 保留旧接口兼容
def set_weather_reminder(device_id: str, city: str, hour: int = 20, minute: int = 0) -> str:
    """设置每日天气定时提醒。返回 job_id。（兼容旧接口，实际使用 setup_weather_broadcasts）"""
    return setup_weather_broadcasts(device_id, city)[0]


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

import random as _random

GREETING_MODES = ["weather", "weather", "trip_reflect", "recommend", "services"]

GREETING_PROMPTS: dict[str, str] = {
    "weather": """你是「AI智游伴」的个性化问候生成器。请根据以下上下文生成一条以天气为主题的温暖开场白。

## 基础信息
- 时间：{time_of_day}
- 天气：{weather}

## 用户画像
- 是新用户：{is_new_user}
- 旅行偏好：{preferences}
- 最近行程：{recent_trips}

## 问候方向：天气 + 日常关怀
- **必须**在问候中提及当前天气情况（下面已提供具体天气数据）
- 根据天气给出1条实用建议（穿衣/出行/带伞等）
- 如果不忙可以聊聊旅行计划

## 要求
- 语气温暖自然，像老朋友在聊天
- 总长度 2-4 句话
- 不要用"尊贵的用户""您好"等客服腔
- 直接输出问候语，不要加前缀""",

    "trip_reflect": """你是「AI智游伴」的个性化问候生成器。请根据以下上下文生成一条以旅行回顾为主题的温暖开场白。

## 基础信息
- 时间：{time_of_day}
- 天气：{weather}

## 用户画像
- 是新用户：{is_new_user}
- 旅行偏好：{preferences}
- 最近行程：{recent_trips}

## 问候方向：旅行回顾 + 体验关怀
- 如果用户有最近行程：自然地问问上次去XX玩得怎么样、有什么有趣经历
- 如果用户没有行程：问问最近有没有出去玩、有什么想去的地方
- 可以分享一个应季的旅行小建议

## 要求
- 语气温暖自然，像老朋友在聊天
- 总长度 2-4 句话
- 不要用"尊贵的用户""您好"等客服腔
- 直接输出问候语，不要加前缀""",

    "recommend": """你是「AI智游伴」的个性化问候生成器。请根据以下上下文生成一条以旅行推荐为主题的温暖开场白。

## 基础信息
- 时间：{time_of_day}
- 天气：{weather}

## 用户画像
- 是新用户：{is_new_user}
- 旅行偏好：{preferences}
- 最近行程：{recent_trips}

## 问候方向：目的地推荐 + 灵感激发
- 根据用户偏好和当前季节，推荐1个适合的目的地或景点类型
- 简短说说为什么推荐
- 问问用户感不感兴趣，要不要帮忙规划

## 要求
- 语气温暖自然，像老朋友在聊天
- 总长度 2-4 句话
- 不要用"尊贵的用户""您好"等客服腔
- 直接输出问候语，不要加前缀""",

    "services": """你是「AI智游伴」的个性化问候生成器。请根据以下上下文生成一条以服务介绍为主题的温暖开场白。

## 基础信息
- 时间：{time_of_day}
- 天气：{weather}

## 用户画像
- 是新用户：{is_new_user}
- 旅行偏好：{preferences}
- 最近行程：{recent_trips}

## 问候方向：服务介绍 + 邀请互动
- 简单提醒用户你能做哪些事（规划行程、查天气、推荐景点、讲解历史文化、扩充知识库等）
- 选1-2个最相关的功能重点提
- 鼓励用户随时来找你聊天或帮忙

## 要求
- 语气温暖自然，像老朋友在聊天
- 总长度 2-4 句话
- 不要用"尊贵的用户""您好"等客服腔
- 直接输出问候语，不要加前缀""",
}


def _time_greeting() -> str:
    h = datetime.now().hour
    if h < 6: return "深夜好"
    if h < 12: return "早上好"
    if h < 14: return "中午好"
    if h < 18: return "下午好"
    return "晚上好"


async def generate_greeting(device_id: str, client_ip: str | None = None) -> dict[str, Any]:
    """生成个性化开场问候。随机选择模式：天气/旅行回顾/推荐/服务介绍。"""
    from app.services.trip_service import query_trip_plans

    # 收集上下文
    prefs = get_all_preferences(device_id)
    recent_trips = query_trip_plans(device_id, limit=2)

    # 判断用户类型
    total_prefs = len(prefs)
    total_trips = len(recent_trips)
    is_new = (total_prefs == 0 and total_trips == 0)

    # 天气信息：优先偏好城市 → IP 定位 → 不显示天气
    weather_text = "未知"
    city = resolve_location(device_id, client_ip)
    if city:
        try:
            from app.services.weather_service import get_weather_with_fallback
            data = await get_weather_with_fallback(city)
            today = data.get("days", [{}])[0] if data.get("days") else {}
            day_weather = today.get("day_weather", "")
            day_temp = today.get("day_temp", "")
            night_temp = today.get("night_temp", "")
            day_wind = today.get("day_wind", "")
            weather_text = f"{city}今天{day_weather}，{day_temp}°C/{night_temp}°C，{day_wind}风"
        except Exception:
            weather_text = city if city else "未知"
    else:
        weather_text = "（天气未知）"

    # 格式化偏好和行程
    pref_text = "、".join(f"{p['key']}={p['value']}" for p in prefs[:5]) if prefs else "无"
    trip_text = " | ".join(t.get("destination", "") for t in recent_trips[:2]) if recent_trips else "无"

    # 随机选择问候模式
    mode = _random.choice(GREETING_MODES)
    prompt_template = GREETING_PROMPTS.get(mode, GREETING_PROMPTS["weather"])
    prompt = prompt_template.format(
        time_of_day=_time_greeting(),
        weather=weather_text,
        is_new_user=str(is_new),
        preferences=pref_text,
        recent_trips=trip_text,
    )

    greeting = await call_llm(
        messages=[{"role": "user", "content": "生成一条个性化开场问候"}],
        system_prompt=prompt,
        temperature=0.85,
        max_tokens=350,
    )

    return {"greeting": greeting, "is_new_user": is_new}


# ── 调度器管理 ──────────────────────────────────────────────

def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        # O29: 每周日凌晨3点执行数据清理
        async def _cleanup_job():
            from app.services.data_cleanup import cleanup_old_data
            cleanup_old_data()
        _scheduler.add_job(
            _cleanup_job,
            trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
            id="weekly_data_cleanup",
            replace_existing=True,
        )
        logger.info("APScheduler 调度器已启动（含每周数据清理）")


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler 调度器已关闭")


# ── F8: 定时天气巡检 ──────────────────────────────────────

PATROL_HOURS = [8, 12, 20]  # 每天 08:00 / 12:00 / 20:00

# ── O7: 推送冷却（同一异常1小时内不重复推送）──
_push_cooldown: dict[str, float] = {}  # key=f"{device_id}:{rule_name}", value=timestamp
COOLDOWN_SECONDS = 3600  # 1小时


def _is_cooled_down(device_id: str, rule_name: str) -> bool:
    """检查该异常是否在冷却期内。True=应跳过推送。"""
    import time
    key = f"{device_id}:{rule_name}"
    last_push = _push_cooldown.get(key, 0)
    return (time.time() - last_push) < COOLDOWN_SECONDS


def _mark_pushed(device_id: str, rule_name: str) -> None:
    """标记该异常已推送。"""
    import time
    _push_cooldown[f"{device_id}:{rule_name}"] = time.time()


async def _weather_patrol_job(device_id: str, city: str) -> None:
    """O7 完整联动链：天气→异常检测→TCI→阈值判断→推送/重排。"""
    try:
        from app.services.weather_anomaly_detector import detect_anomalies
        from app.services.weather_service import get_weather_with_fallback

        # Step 1: 获取天气数据（O4 四级降级）
        weather_data = await get_weather_with_fallback(city)

        # Step 2: 异常检测（O5 四条规则）
        report = detect_anomalies(weather_data, city)

        if not report.has_anomaly:
            logger.info("巡检正常: city=%s", city)
            return

        # Step 3: 过滤冷却期内的异常
        active_anomalies = [
            a for a in report.anomalies
            if not _is_cooled_down(device_id, a.rule_name)
        ]
        if not active_anomalies:
            logger.info("巡检有异常但均在冷却期: city=%s", city)
            return

        # Step 4: TCI 重算（O6）
        from app.services.comfort_index_service import calculate_tci, ComfortContext
        today = weather_data.get("days", [{}])[0] if weather_data.get("days") else {}
        try:
            temp = int(today.get("day_temp", 20) or 20)
        except (ValueError, TypeError):
            temp = 20
        ctx = ComfortContext(
            city=city, temperature=temp,
            weather_desc=today.get("day_weather", ""),
            wind=today.get("day_wind", ""),
            hour=datetime.now().hour,
        )
        tci = calculate_tci(ctx)

        # Step 5: 构建推送消息
        lines = [f"⚠️ {city}天气预警："]
        for a in active_anomalies:
            lines.append(f"  {a.title} — {a.suggestion}")
            _mark_pushed(device_id, a.rule_name)

        lines.append(f"\n🌡️ 当前旅行体感指数：{tci.score}分（{tci.level_emoji} {tci.level}）")

        # Step 6: TCI ≥20分下降 → 附加行程重排建议
        if tci.score < 60:
            try:
                from app.services.weather_linkage_engine import adjust_trip_by_weather
                # 获取该设备最近的行程
                from app.models.database import get_db
                conn = get_db()
                row = conn.execute(
                    "SELECT itinerary_json FROM trip_plans WHERE device_id = ? ORDER BY created_at DESC LIMIT 1",
                    (device_id,),
                ).fetchone()
                conn.close()
                if row and row["itinerary_json"]:
                    import json as _json
                    trip_plan = _json.loads(row["itinerary_json"])
                    result = await adjust_trip_by_weather(device_id, city, trip_plan, weather_data)
                    if result.get("adjusted"):
                        lines.append(f"\n📋 行程调整建议：\n{result['suggestion']}")
            except Exception as e:
                logger.warning("行程重排失败: %s", e)

        message = "\n".join(lines)
        await push_message(device_id, message, msg_type="weather_alert")
        logger.info("O7联动推送: city=%s, device=%s, tci=%d(%s), anomalies=%d",
                     city, device_id, tci.score, tci.level, len(active_anomalies))

    except Exception:
        logger.exception("天气巡检失败: device=%s, city=%s", device_id, city)


def setup_weather_patrol(device_id: str, city: str) -> list[str]:
    """设置每天 2 个时段的天气巡检（08:00 / 20:00）。"""
    job_ids = []
    for hour in PATROL_HOURS:
        job_id = f"patrol_{device_id}_{city}_{hour}"
        _scheduler.add_job(
            _weather_patrol_job,
            trigger=CronTrigger(hour=hour, minute=5),
            args=[device_id, city],
            id=job_id,
            replace_existing=True,
        )
        job_ids.append(job_id)
    logger.info("天气巡检已设置：%s → %s 每天 %s", device_id, city, PATROL_HOURS)
    return job_ids
