"""O11: 旅行清单生成器 — 规则驱动 + 天气/人群/过敏联动 + 结构化数据。"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)


# ── 固定清单（所有人都要带） ────────────────────────────

FIXED_ITEMS = [
    {"name": "身份证", "packed": False, "essential": True, "note": "必带"},
    {"name": "手机+充电线", "packed": False, "essential": True, "note": ""},
    {"name": "充电宝", "packed": False, "essential": True, "note": "建议10000mAh以上"},
    {"name": "现金+银行卡", "packed": False, "essential": True, "note": "备少量现金"},
    {"name": "换洗衣物", "packed": False, "essential": True, "note": "根据天数准备"},
]

# ── 天气驱动清单 ────────────────────────────────────────

WEATHER_RULES = {
    "雨": {"category": "雨具", "icon": "☂️", "items": [
        {"name": "折叠雨伞", "packed": False, "essential": True, "note": "随身携带"},
        {"name": "防水鞋套", "packed": False, "essential": False, "note": "雨天出行"},
    ]},
    "高温": {"category": "防晒防暑", "icon": "🧴", "items": [
        {"name": "防晒霜 SPF50+", "packed": False, "essential": True, "note": "高温必备"},
        {"name": "遮阳帽", "packed": False, "essential": True, "note": ""},
        {"name": "太阳镜", "packed": False, "essential": False, "note": ""},
        {"name": "便携水壶", "packed": False, "essential": True, "note": "多补水"},
        {"name": "藿香正气水", "packed": False, "essential": True, "note": "防中暑"},
    ]},
    "低温": {"category": "保暖", "icon": "🧥", "items": [
        {"name": "厚外套/羽绒服", "packed": False, "essential": True, "note": "低温必备"},
        {"name": "保暖内衣", "packed": False, "essential": False, "note": ""},
        {"name": "手套围巾", "packed": False, "essential": False, "note": ""},
    ]},
    "大风": {"category": "防风", "icon": "💨", "items": [
        {"name": "防风外套", "packed": False, "essential": True, "note": "强风天气"},
    ]},
    "雾霾": {"category": "防护", "icon": "😷", "items": [
        {"name": "口罩（N95）", "packed": False, "essential": True, "note": "雾霾天必备"},
    ]},
}

# ── 人群驱动清单 ────────────────────────────────────────

PEOPLE_RULES = {
    "family_child": {"category": "婴儿/儿童用品", "icon": "🍼", "items": [
        {"name": "纸尿布", "packed": False, "essential": True, "note": "根据天数准备"},
        {"name": "退烧贴×3", "packed": False, "essential": True, "note": "儿童退烧备用"},
        {"name": "小零食/饼干", "packed": False, "essential": False, "note": "孩子饿了应急"},
        {"name": "折叠推车", "packed": False, "essential": False, "note": "走累了可选"},
        {"name": "奶瓶/奶粉", "packed": False, "essential": True, "note": "婴儿必备"},
    ]},
    "family_elder": {"category": "老人用品", "icon": "👴", "items": [
        {"name": "常用药物（高血压/糖尿病等）", "packed": False, "essential": True, "note": "老人日常用药"},
        {"name": "护膝", "packed": False, "essential": False, "note": "膝盖不好的老人"},
        {"name": "折叠拐杖", "packed": False, "essential": False, "note": "行走不便时使用"},
        {"name": "舒适平底鞋", "packed": False, "essential": True, "note": "避免高跟鞋/硬底鞋"},
    ]},
}

# ── 健康驱动清单 ────────────────────────────────────────

HEALTH_RULES = {
    "花粉过敏": {"category": "过敏防护", "icon": "🤧", "items": [
        {"name": "防花粉口罩×5", "packed": False, "essential": True, "note": "花粉过敏史"},
        {"name": "氯雷他定（抗过敏药）", "packed": False, "essential": True, "note": "花粉过敏史"},
    ]},
    "季节性鼻炎": {"category": "过敏防护", "icon": "🤧", "items": [
        {"name": "鼻炎喷雾", "packed": False, "essential": True, "note": "鼻炎患者必备"},
        {"name": "口罩", "packed": False, "essential": True, "note": "防沙尘/油烟"},
    ]},
    "尘螨过敏": {"category": "过敏防护", "icon": "🤧", "items": [
        {"name": "抗过敏药", "packed": False, "essential": True, "note": "尘螨过敏"},
        {"name": "防螨枕套", "packed": False, "essential": False, "note": "住宿时使用"},
    ]},
}

# ── 通用药品 ────────────────────────────────────────────

COMMON_MEDICINE = {"category": "药品与健康", "icon": "💊", "items": [
    {"name": "感冒药", "packed": False, "essential": True, "note": "通用"},
    {"name": "创可贴", "packed": False, "essential": False, "note": "通用"},
    {"name": "肠胃药", "packed": False, "essential": True, "note": "水土不服备用"},
    {"name": "晕车药", "packed": False, "essential": False, "note": "晕车者必备"},
]}


def _classify_weather(weather_text: str) -> list[str]:
    """从天气文本中提取天气类型标签。"""
    tags = []
    if any(k in weather_text for k in ("雨", "雷", "阵雨", "暴雨")):
        tags.append("雨")
    if any(k in weather_text for k in ("高温", "炎热")):
        tags.append("高温")
    # 通过温度判断
    import re
    temps = re.findall(r'(\d+)°?C', weather_text)
    for t in temps:
        temp = int(t)
        if temp >= 33:
            tags.append("高温")
        elif temp <= 5:
            tags.append("低温")
    if any(k in weather_text for k in ("大风", "强风", "台风")):
        tags.append("大风")
    if any(k in weather_text for k in ("雾", "霾")):
        tags.append("雾霾")
    # 雨天默认带低温考虑
    if "雨" in tags and "高温" not in tags and "低温" not in tags:
        tags.append("低温")
    return tags


async def generate_checklist(
    destination: str,
    days: int,
    weather: str = "",
    composition: str = "",
    allergies: list[str] | None = None,
    child_age: int | None = None,
) -> dict:
    """
    结构化清单生成：规则驱动 + LLM 补充目的地特色物品。
    """
    categories = []

    # 1. 固定清单
    categories.append({
        "category": "证件与钱",
        "icon": "📄",
        "items": FIXED_ITEMS.copy(),
    })

    # 2. 天气驱动清单
    weather_tags = _classify_weather(weather)
    for tag in weather_tags:
        rule = WEATHER_RULES.get(tag)
        if rule:
            # 检查是否已有同类（避免重复）
            existing_names = {i["name"] for cat in categories for i in cat["items"]}
            new_items = [item for item in rule["items"] if item["name"] not in existing_names]
            if new_items:
                categories.append({
                    "category": rule["category"],
                    "icon": rule["icon"],
                    "items": new_items,
                })

    # 3. 人群驱动清单
    if composition in PEOPLE_RULES:
        rule = PEOPLE_RULES[composition]
        categories.append({
            "category": rule["category"],
            "icon": rule["icon"],
            "items": rule["items"].copy(),
        })

    # 4. 健康驱动清单
    if allergies:
        for allergy in allergies:
            rule = HEALTH_RULES.get(allergy)
            if rule:
                existing_names = {i["name"] for cat in categories for i in cat["items"]}
                new_items = [item for item in rule["items"] if item["name"] not in existing_names]
                if new_items:
                    categories.append({
                        "category": rule["category"],
                        "icon": rule["icon"],
                        "items": new_items,
                    })

    # 5. 通用药品（如果没有健康驱动的药品分类）
    has_medicine = any(cat["category"] == "药品与健康" for cat in categories)
    if not has_medicine:
        categories.append(COMMON_MEDICINE.copy())

    # 6. LLM 补充目的地特色物品
    try:
        extra_items = await _llm_supplement(destination, days, weather, composition)
        if extra_items:
            categories.append({
                "category": f"{destination}特色",
                "icon": "🎯",
                "items": extra_items,
            })
    except Exception:
        logger.debug("LLM特色物品补充跳过")

    # 生成元信息
    generated_from = {
        "destination": destination,
        "days": days,
        "weather": weather,
        "composition": composition,
        "allergies": allergies or [],
        "child_age": child_age,
    }

    return {
        "categories": categories,
        "generated_from": generated_from,
    }


async def _llm_supplement(
    destination: str, days: int, weather: str, composition: str
) -> list[dict]:
    """用 LLM 补充目的地特色物品。"""
    prompt = (
        f"你是旅行清单助手。请为去{destination}旅行{days}天的用户，"
        f"补充3-5个{destination}特色物品（如：海边→防水袋，高原→氧气瓶，山区→登山鞋）。\n"
        f"天气：{weather}，人群：{composition or '普通'}\n"
        f"输出JSON数组，格式：[{{\"name\":\"物品\",\"packed\":false,\"essential\":false,\"note\":\"原因\"}}]\n"
        f"只输出JSON，不要其他文字。"
    )
    raw = await call_llm(
        messages=[{"role": "user", "content": f"为{destination}旅行补充特色物品"}],
        system_prompt=prompt,
        temperature=0.3,
        max_tokens=300,
    )
    try:
        items = json.loads(raw)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    return []
