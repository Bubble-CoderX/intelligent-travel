"""工具注册中心：将可调用的工具函数统一注册，供 Agent 核心按名称调度。"""
from __future__ import annotations

from typing import Any, Callable

from app.services.map_service import geocode_address, search_places
from app.services.weather_service import get_weather_forecast

TOOLS: dict[str, dict[str, Any]] = {}


def _register(name: str, func: Callable, description: str, parameters: dict[str, str]) -> None:
    TOOLS[name] = {
        "function": func,
        "description": description,
        "parameters": parameters,
    }


_register(
    name="get_weather",
    func=get_weather_forecast,
    description="查询指定城市的实时天气及未来3天预报",
    parameters={"city": "城市名称，如：杭州"},
)

_register(
    name="search_poi",
    func=search_places,
    description="根据关键词搜索地点（餐厅、景点、酒店等）",
    parameters={
        "keyword": "搜索关键词，如：西湖",
        "city": "城市名称（可选）",
        "page_size": "返回数量，默认5",
    },
)

_register(
    name="geocode",
    func=geocode_address,
    description="将地址文本转换为经纬度坐标",
    parameters={"address": "地址文本，如：杭州西湖", "city": "城市名称（可选）"},
)


def get_tool(name: str) -> Callable | None:
    """按名称获取工具函数，不存在时返回 None。"""
    entry = TOOLS.get(name)
    return entry["function"] if entry else None


def list_tools() -> list[dict[str, str]]:
    """返回所有已注册工具的名称和描述。"""
    return [{"name": k, "description": v["description"]} for k, v in TOOLS.items()]
