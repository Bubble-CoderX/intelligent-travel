"""天气服务：高德 API 查询 + 持久化 + 四级降级兜底。"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import (
    AMAP_API_KEY,
    AMAP_BASE_URL,
    AMAP_TIMEOUT_SECONDS,
    REDIS_WEATHER_TTL_SECONDS,
)
from app.services.cache_service import get_cached_json, set_cached_json
from app.services.map_service import geocode_address


logger = logging.getLogger(__name__)


# ── 高德 API 基础 ──────────────────────────────────────────

def _ensure_amap_api_key() -> None:
    """确保当前环境已经配置高德地图 Key。"""
    if not AMAP_API_KEY:
        raise RuntimeError("当前环境未配置 AMAP_API_KEY，无法调用天气服务。")


def _build_client() -> httpx.Client:
    """创建访问高德天气 API 的客户端。"""
    return httpx.Client(timeout=AMAP_TIMEOUT_SECONDS)


def _request_amap_weather(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """调用高德天气接口并返回 JSON 结果。"""
    _ensure_amap_api_key()

    request_params = {
        "key": AMAP_API_KEY,
        **params,
    }

    with _build_client() as client:
        response = client.get(f"{AMAP_BASE_URL}{path}", params=request_params)
        response.raise_for_status()
        payload = response.json()

    if payload.get("status") != "1":
        info = payload.get("info", "未知错误")
        raise RuntimeError(f"高德天气接口调用失败：{info}")

    return payload


def _normalize_cache_text(value: str | None) -> str:
    """把缓存 key 里用到的文本做简单标准化。"""
    if value is None:
        return ""
    return value.strip().lower()


# ── F1：天气数据持久化 ─────────────────────────────────────

def _persist_weather(city: str, weather_data: dict) -> None:
    """将天气快照写入 SQLite，humidity 从实时接口补充。"""
    try:
        from app.models.database import get_db
        today = weather_data.get("days", [{}])[0] if weather_data.get("days") else {}

        # 补充湿度：实时接口有 humidity，预报接口没有
        humidity = weather_data.get("humidity") or today.get("humidity", "")
        if not humidity:
            try:
                geocode = geocode_address(city, city=city)
                city_code = geocode.get("adcode") if geocode else city
                rt = _request_amap_weather("/weather/weatherInfo", {"city": city_code, "extensions": "base"})
                live = rt.get("lives", [{}])[0] if rt.get("lives") else {}
                humidity = live.get("humidity", "")
            except Exception:
                pass

        conn = get_db()
        conn.execute(
            "INSERT INTO weather_records (city, weather, temperature, humidity, wind_direction, wind_power, forecast_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                city,
                today.get("day_weather", ""),
                int(today.get("day_temp", 0) or 0),
                str(humidity),
                today.get("day_wind", ""),
                today.get("night_wind", ""),
                json.dumps(weather_data, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("天气数据持久化失败: %s", city)


def get_weather_history(city: str, limit: int = 7) -> list[dict]:
    """查询城市的历史天气记录。"""
    from app.models.database import get_db
    conn = get_db()
    rows = conn.execute(
        "SELECT city, weather, temperature, wind_direction, wind_power, forecast_json, fetched_at "
        "FROM weather_records WHERE city = ? ORDER BY fetched_at DESC LIMIT ?",
        (city, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── F2：四级降级策略 ───────────────────────────────────────

async def get_weather_with_fallback(city: str) -> dict[str, Any]:
    """
    四级降级获取天气：
      Level 1: 内存缓存（已有 Redis 缓存层）
      Level 2: SQLite 最近一条记录
      Level 3: 高德 API 实时请求
      Level 4: LLM 通用知识估算
    返回数据含 _source 字段标识来源。
    """
    # Level 1: Redis 缓存
    cache_key = f"weather:forecast:{_normalize_cache_text(city)}"
    cached = get_cached_json(cache_key)
    if cached is not None:
        cached["_source"] = "cache"
        # 缓存数据可能缺少 humidity（旧缓存），实时补充
        if not cached.get("humidity"):
            try:
                geocode = geocode_address(city, city=city)
                city_code = geocode.get("adcode") if geocode else city
                rt = _request_amap_weather("/weather/weatherInfo", {"city": city_code, "extensions": "base"})
                live = rt.get("lives", [{}])[0] if rt.get("lives") else {}
                humidity = live.get("humidity", "")
                if humidity:
                    cached["humidity"] = humidity
                    if cached.get("days"):
                        cached["days"][0]["humidity"] = humidity
            except Exception:
                pass
        return cached

    # Level 2: SQLite 历史记录（仅当数据在 30 分钟内时使用）
    from datetime import datetime, timedelta
    from app.models.database import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT forecast_json, fetched_at FROM weather_records WHERE city = ? ORDER BY fetched_at DESC LIMIT 1",
        (city,),
    ).fetchone()
    conn.close()
    if row and row["forecast_json"]:
        try:
            fetched_at = datetime.strptime(row["fetched_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - fetched_at < timedelta(minutes=30):
                db_data = json.loads(row["forecast_json"])
                db_data["_source"] = "database"
                return db_data
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Level 3: 高德 API
    try:
        result = get_weather_forecast(city)
        _persist_weather(city, result)
        result["_source"] = "api"
        return result
    except Exception:
        logger.warning("高德天气 API 失败: %s", city)

    # Level 4: LLM 通用知识估算
    try:
        from app.services.llm_client import call_llm
        estimate = await call_llm(
            messages=[{"role": "user", "content": f"请用1-2句话简要描述{city}当前季节的典型天气情况，包括气温范围和天气特征。只输出天气描述，不要其他内容。"}],
            system_prompt="你是天气助手，根据通用知识回答。",
            temperature=0.3,
            max_tokens=100,
        )
        return {
            "city": city,
            "days": [{"day_weather": estimate.strip(), "day_temp": "?", "night_temp": "?", "day_wind": "未知"}],
            "report_time": "LLM估算",
            "_source": "llm_estimate",
        }
    except Exception:
        return {"city": city, "days": [], "_source": "unavailable"}


# ── 核心查询（带持久化） ──────────────────────────────────

def get_weather_forecast(city: str) -> dict[str, Any]:
    """获取指定城市的未来天气预报。"""
    cache_key = f"weather:forecast:{_normalize_cache_text(city)}"
    cached_value = get_cached_json(cache_key)
    if cached_value is not None:
        logger.info("weather cache hit: city=%s", city)
        return cached_value
    logger.info("weather cache miss: city=%s", city)

    geocode = geocode_address(city, city=city)
    city_code = geocode.get("adcode") if geocode is not None else city

    payload = _request_amap_weather(
        "/weather/weatherInfo",
        {
            "city": city_code or city,
            "extensions": "all",
        },
    )

    forecasts = payload.get("forecasts", [])
    if not forecasts:
        raise RuntimeError("未获取到天气预报结果。")

    first = forecasts[0]
    casts = first.get("casts", [])

    days = [
        {
            "date": cast.get("date"),
            "week": cast.get("week"),
            "day_weather": cast.get("dayweather"),
            "night_weather": cast.get("nightweather"),
            "day_temp": cast.get("daytemp"),
            "night_temp": cast.get("nighttemp"),
            "day_wind": cast.get("daywind"),
            "night_wind": cast.get("nightwind"),
        }
        for cast in casts
    ]

    result = {
        "city": first.get("city") or city,
        "province": first.get("province"),
        "adcode": first.get("adcode"),
        "report_time": first.get("reporttime"),
        "days": days,
    }

    # 补充实时湿度（预报接口不含湿度，需调实时接口）
    try:
        realtime = _request_amap_weather(
            "/weather/weatherInfo",
            {"city": city_code or city, "extensions": "base"},
        )
        live = realtime.get("lives", [{}])[0] if realtime.get("lives") else {}
        humidity = live.get("humidity", "")
        if humidity and result.get("days"):
            result["days"][0]["humidity"] = humidity
            result["humidity"] = humidity
    except Exception:
        pass

    set_cached_json(cache_key, result, expire_seconds=REDIS_WEATHER_TTL_SECONDS)

    # 持久化到 SQLite
    _persist_weather(city, result)

    return result
