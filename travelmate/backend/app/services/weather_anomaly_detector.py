"""F3: 天气异常检测引擎——检测降雨/高温/骤降/强风，主动推送预警。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── 异常类型 ──────────────────────────────────────────────

RAIN_KEYWORDS = {"雨", "雷", "阵雨", "暴雨", "小雨", "中雨", "大雨", "雷阵雨"}
HIGH_TEMP_THRESHOLD = 35       # 高温阈值 °C
TEMP_DROP_THRESHOLD = 8        # 骤降阈值 °C（24小时内降幅）
STRONG_WIND_KEYWORDS = {"大风", "强风", "风暴", "台风"}
STRONG_WIND_LEVEL = 6          # ≥6级大风阈值


@dataclass
class AnomalyResult:
    """一条异常检测结果。"""
    rule_name: str
    severity: str          # "info" | "warning" | "alert"
    title: str
    detail: str
    suggestion: str = ""


@dataclass
class AnomalyReport:
    """一次检测的完整报告。"""
    city: str
    anomalies: list[AnomalyResult] = field(default_factory=list)
    has_anomaly: bool = False


# ── 规则函数 ──────────────────────────────────────────────

def _check_rain_forecast(today: dict, tomorrow: dict | None) -> AnomalyResult | None:
    """规则1：未来24小时内有降雨。"""
    for day_label, day_data in [("今天", today), ("明天", tomorrow)]:
        if day_data is None:
            continue
        day_w = day_data.get("day_weather", "")
        night_w = day_data.get("night_weather", "")
        if any(k in day_w or k in night_w for k in RAIN_KEYWORDS):
            return AnomalyResult(
                rule_name="rain_forecast",
                severity="warning",
                title=f"🌧️ {day_label}有雨",
                detail=f"{day_label}天气：白天{day_w}，夜间{night_w}",
                suggestion="建议随身携带雨具，户外活动可适当调整为室内项目。",
            )
    return None


def _check_extreme_heat(today: dict, tomorrow: dict | None) -> AnomalyResult | None:
    """规则2：明天高温预警（明天最高温≥35°C）。"""
    target = tomorrow or today
    try:
        temp = int(target.get("day_temp", 0) or 0)
    except (ValueError, TypeError):
        return None
    if temp >= HIGH_TEMP_THRESHOLD:
        label = "明天" if tomorrow else "今天"
        return AnomalyResult(
            rule_name="extreme_heat",
            severity="warning",
            title=f"🌡️ {label}高温预警：{temp}°C",
            detail=f"{label}最高气温{temp}°C，已超过{HIGH_TEMP_THRESHOLD}°C高温阈值。",
            suggestion="注意防暑降温，避免长时间户外活动，多补充水分。",
        )
    return None


def _check_temperature_drop(today: dict, tomorrow: dict | None) -> AnomalyResult | None:
    """规则3：气温骤降。"""
    if tomorrow is None:
        return None
    try:
        today_temp = int(today.get("day_temp", 0) or 0)
        tomorrow_temp = int(tomorrow.get("day_temp", 0) or 0)
    except (ValueError, TypeError):
        return None
    drop = today_temp - tomorrow_temp
    if drop >= TEMP_DROP_THRESHOLD:
        return AnomalyResult(
            rule_name="temperature_drop",
            severity="alert",
            title=f"📉 明日气温骤降{drop}°C",
            detail=f"今日{today_temp}°C → 明日{tomorrow_temp}°C，降幅{drop}°C。",
            suggestion="气温骤降请注意添衣保暖，感冒风险较高。",
        )
    return None


def _check_strong_wind(today: dict) -> AnomalyResult | None:
    """规则4：强风预警（关键词匹配 或 风力数值≥6级）。"""
    day_wind = today.get("day_wind", "")
    night_wind = today.get("night_wind", "")

    # 关键词匹配
    has_keyword = any(k in day_wind or k in night_wind for k in STRONG_WIND_KEYWORDS)

    # 数值判断（提取风力级数）
    import re
    wind_level = 0
    for w in (day_wind, night_wind):
        m = re.search(r'(\d+)', w)
        if m:
            wind_level = max(wind_level, int(m.group(1)))

    if has_keyword or wind_level >= STRONG_WIND_LEVEL:
        return AnomalyResult(
            rule_name="strong_wind",
            severity="warning",
            title="💨 强风预警",
            detail=f"今日风力：白天{day_wind}，夜间{night_wind}（{wind_level}级）。",
            suggestion="强风天气注意出行安全，避免高空活动和水上项目。",
        )
    return None


# ── 引擎入口 ──────────────────────────────────────────────

RULES = [
    _check_rain_forecast,
    _check_extreme_heat,
    _check_temperature_drop,
    _check_strong_wind,
]


def detect_anomalies(weather_data: dict[str, Any], city: str = "") -> AnomalyReport:
    """
    对天气数据执行全部异常检测规则，返回报告。
    weather_data 为 get_weather_forecast() 或 get_weather_with_fallback() 的返回值。
    """
    days = weather_data.get("days", [])
    today = days[0] if len(days) > 0 else {}
    tomorrow = days[1] if len(days) > 1 else None

    report = AnomalyReport(city=city or weather_data.get("city", "未知"))

    for rule_fn in RULES:
        result = rule_fn(today, tomorrow) if rule_fn in (_check_rain_forecast, _check_temperature_drop, _check_extreme_heat) else rule_fn(today)
        if result is not None:
            report.anomalies.append(result)

    report.has_anomaly = len(report.anomalies) > 0
    return report


async def detect_and_push(city: str, device_id: str) -> AnomalyReport:
    """检测异常并通过 WebSocket 推送通知。返回检测报告。"""
    from app.services.weather_service import get_weather_with_fallback

    weather_data = await get_weather_with_fallback(city)
    report = detect_anomalies(weather_data, city)

    if report.has_anomaly:
        lines = [f"⚠️ {city}天气预警："]
        for a in report.anomalies:
            lines.append(f"  {a.title} — {a.suggestion}")
        message = "\n".join(lines)

        from app.services.proactive_service import push_message
        await push_message(device_id, message, msg_type="weather_alert")
        logger.info("天气异常推送: city=%s, device=%s, anomalies=%d", city, device_id, len(report.anomalies))

    return report
