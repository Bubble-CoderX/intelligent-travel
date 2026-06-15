"""O2: 交通推荐服务——根据出发地、距离、人数、预算推荐大交通和当地交通。"""

from __future__ import annotations

import logging
import re

import httpx

from app.core.config import AMAP_API_KEY, AMAP_BASE_URL, AMAP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


# ── 距离计算 ──────────────────────────────────────────


def _geocode_city(city: str) -> dict | None:
    """城市名 → 经纬度。"""
    try:
        resp = httpx.get(
            f"{AMAP_BASE_URL}/geocode/geo",
            params={"key": AMAP_API_KEY, "address": city},
            timeout=AMAP_TIMEOUT_SECONDS,
        )
        data = resp.json()
        if data.get("status") == "1" and data.get("geocodes"):
            loc = data["geocodes"][0].get("location", "")
            lng, lat = loc.split(",") if "," in loc else ("", "")
            return {"lng": float(lng), "lat": float(lat)}
    except Exception:
        logger.debug("地理编码失败: %s", city)
    return None


def get_distance_km(departure: str, destination: str) -> int:
    """获取两城市之间的驾车距离（km），失败返回估算值。"""
    p1 = _geocode_city(departure)
    p2 = _geocode_city(destination)
    if not p1 or not p2:
        return _estimate_distance(departure, destination)
    try:
        resp = httpx.get(
            f"{AMAP_BASE_URL}/direction/driving",
            params={
                "key": AMAP_API_KEY,
                "origin": f"{p1['lng']},{p1['lat']}",
                "destination": f"{p2['lng']},{p2['lat']}",
            },
            timeout=AMAP_TIMEOUT_SECONDS,
        )
        data = resp.json()
        if data.get("status") == "1":
            route = data.get("route", {})
            distance_m = route.get("paths", [{}])[0].get("distance", 0)
            return int(int(distance_m) / 1000)
    except Exception:
        logger.debug("驾车距离查询失败: %s → %s", departure, destination)
    return _estimate_distance(departure, destination)


# 常见城市间距离估算表（km，无法调用API时兜底）
_DISTANCE_TABLE = {
    ("北京", "上海"): 1200, ("北京", "广州"): 1900, ("北京", "成都"): 1800,
    ("北京", "西安"): 1100, ("北京", "杭州"): 1200, ("北京", "武汉"): 1150,
    ("上海", "广州"): 1200, ("上海", "成都"): 1700, ("上海", "杭州"): 170,
    ("广州", "成都"): 1500, ("广州", "武汉"): 950, ("广州", "长沙"): 600,
    ("广州", "深圳"): 120, ("广州", "厦门"): 500, ("广州", "三亚"): 700,
    ("成都", "重庆"): 300, ("成都", "西安"): 700, ("成都", "大理"): 900,
    ("武汉", "长沙"): 300, ("武汉", "成都"): 1100,
}


def _estimate_distance(c1: str, c2: str) -> int:
    """从距离表估算，找不到返回 500（默认中距离）。"""
    for (a, b), d in _DISTANCE_TABLE.items():
        if (a in c1 and b in c2) or (b in c1 and a in c2):
            return d
    return 500


# ── 大交通推荐（出发地 → 目的地）─────────────────────


def recommend_transport(
    departure: str, destination: str, budget_tier: str, group_size: int
) -> dict:
    """根据出发地、目的地、预算、出行人数推荐大交通方式。"""
    distance_km = get_distance_km(departure, destination)

    if distance_km <= 50:
        if group_size >= 3:
            return {
                "mode": "自驾", "cost": "约50-100元", "duration": "约1小时",
                "reason": f"{group_size}人出行自驾最方便，分摊油费人均低",
                "distance_km": distance_km,
            }
        return {
            "mode": "地铁/公交", "cost": "约5-20元", "duration": "约1-1.5小时",
            "reason": "近距离公共交通最经济",
            "distance_km": distance_km,
        }

    if distance_km <= 500:
        return {
            "mode": "高铁", "cost": "约100-300元", "duration": "约1-3小时",
            "reason": "500km内高铁最快最稳",
            "distance_km": distance_km,
        }

    if distance_km <= 1500:
        if budget_tier in ("poor", "economic"):
            return {
                "mode": "高铁", "cost": "约300-600元", "duration": "约4-6小时",
                "reason": "经济条件下高铁性价比最高",
                "distance_km": distance_km,
            }
        return {
            "mode": "飞机", "cost": "约500-1200元", "duration": "约2-3小时（含值机）",
            "reason": "预算充足飞机节省时间",
            "distance_km": distance_km,
        }

    # 1500km以上
    if budget_tier == "poor":
        return {
            "mode": "火车硬卧/高铁", "cost": "约300-800元", "duration": "约10-20小时",
            "reason": "远距离穷游首选火车卧铺",
            "distance_km": distance_km,
        }
    return {
        "mode": "飞机", "cost": "约600-1500元", "duration": "约2-4小时",
        "reason": "远距离优先飞机",
        "distance_km": distance_km,
    }


# ── 当地交通推荐 ──────────────────────────────────────


def check_subway(city: str) -> bool:
    """判断城市是否有地铁。"""
    try:
        resp = httpx.get(
            f"{AMAP_BASE_URL}/place/text",
            params={
                "key": AMAP_API_KEY,
                "keywords": "地铁站",
                "city": city,
                "types": "150700",
                "offset": 1,
            },
            timeout=AMAP_TIMEOUT_SECONDS,
        )
        data = resp.json()
        return int(data.get("count", 0)) > 0
    except Exception:
        return False


def recommend_local_transport(
    group_size: int, budget_tier: str, has_subway: bool, city: str = ""
) -> dict:
    """推荐当地交通方式组合。"""
    if group_size >= 4:
        return {
            "primary": "打车（滴滴/高德打车）",
            "reason": f"{group_size}人打车人均≈地铁票价，更省心省力",
            "alternative": "地铁（高峰期或远距离时）",
            "cost_estimate": f"市内打车单程约15-40元，{group_size}人分摊约4-10元/人",
        }

    if group_size <= 2 and has_subway:
        return {
            "primary": "地铁",
            "reason": "1-2人地铁最经济，不堵车不用找停车位",
            "alternative": "打车（去地铁不方便的地方或深夜时）",
            "cost_estimate": "地铁单程2-7元，一天交通费约15-30元",
        }

    if group_size <= 2 and not has_subway:
        return {
            "primary": "打车 + 公交",
            "reason": f"{city or '目的地'}暂无地铁，打车为主、公交补充",
            "alternative": "租车自驾（景点分散时更方便）",
            "cost_estimate": "打车单程约10-25元，公交2元，一天约40-80元",
        }

    return {
        "primary": "地铁+打车混搭",
        "reason": "根据距离和场景灵活选择最合适的",
        "alternative": "",
        "cost_estimate": "视具体行程而定",
    }


# ── 格式化为 Prompt 文本 ─────────────────────────────


def get_transport_text(
    departure: str, destination: str, group_size: int, budget_tier: str
) -> str:
    """生成完整的交通推荐文本，供注入行程规划 Prompt。"""
    if not departure or departure == destination:
        return (
            f"本地游（{destination}），无需大交通。\n"
            f"- 请在 Day1 的 transport 数组中省略出发地到目的地的大交通条目"
        )

    # 大交通
    main_transport = recommend_transport(departure, destination, budget_tier, group_size)

    # 大交通费用：不预计算，交给LLM根据内部数据估算二等座/经济舱票价
    distance_km = main_transport["distance_km"]
    if main_transport["mode"] == "高铁":
        cost_hint = "请根据你对中国高铁二等座票价的知识，给出合理的单程票价估算（人民币元）"
    elif main_transport["mode"] == "飞机":
        cost_hint = "请根据你对国内航线经济舱票价的知识，给出合理的单程票价估算（人民币元）"
    elif main_transport["mode"] == "地铁/公交":
        big_transport_cost = 15
        cost_hint = ""
    elif main_transport["mode"] == "自驾":
        big_transport_cost = max(50, int(distance_km * 0.5))
        cost_hint = ""
    elif main_transport["mode"] == "火车硬卧/高铁":
        cost_hint = "请根据你对中国火车硬卧/高铁票价的知识，给出合理的单程票价估算（人民币元）"
    else:
        big_transport_cost = 300
        cost_hint = ""

    # 当地交通
    has_subway = check_subway(destination)
    local_transport = recommend_local_transport(group_size, budget_tier, has_subway, destination)

    lines = [
        f"## 交通安排（必须严格按照以下信息填写JSON中的transport和budget_breakdown）",
        f"",
        f"### 大交通（{departure}→{destination}，{distance_km}km）",
        f"- 方式：{main_transport['mode']}",
        f"- 耗时：{main_transport['duration']}",
    ]

    # 如果有预估费用（地铁/自驾），直接给出数字；否则让LLM估算
    if cost_hint:
        lines.extend([
            f"- 费用：{cost_hint}",
            f"- 要求：{group_size}人往返费用必须写入Day1的transport和budget_breakdown.transport",
        ])
    else:
        lines.extend([
            f"- 单程费用：约{big_transport_cost}元/人",
            f"- 往返费用：约{big_transport_cost * 2}元/人",
            f"- {group_size}人总费用：约{big_transport_cost * 2 * group_size}元",
        ])

    lines.extend([
        f"",
        f"### 当地交通",
        f"- 主要方式：{local_transport['primary']}",
        f"- {local_transport['reason']}",
        f"- 费用估算：{local_transport['cost_estimate']}",
        f"",
        f"### 必须遵守的规则",
        f"1. Day1 的 transport 数组第一条必须是大交通条目（含费用金额）",
        f"2. budget_breakdown.transport 必须包含大交通费用 + 当地交通费用",
        f"3. 机场/火车站仅作为出发日和返程日的交通节点，不作为游览景点",
        f"4. 每天最后一个活动结束后必须安排回酒店的交通",
    ])

    return "\n".join(lines)
