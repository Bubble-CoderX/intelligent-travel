"""O11: 旅行清单生成器 — 规则驱动 + 天气/人群/健康联动 + LLM智能补充。"""

from __future__ import annotations

import json
import logging
import re
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


# ── 天气驱动清单（按实际天气条件触发） ──────────────────

WEATHER_RULES = {
    "rain": {"category": "雨具", "icon": "☂️", "items": [
        {"name": "折叠雨伞", "packed": False, "essential": True, "note": "随身携带"},
        {"name": "防水鞋套", "packed": False, "essential": False, "note": "雨天出行"},
    ]},
    "high_temp": {"category": "防晒防暑", "icon": "🧴", "items": [
        {"name": "防晒霜 SPF50+", "packed": False, "essential": True, "note": "高温必备"},
        {"name": "遮阳帽", "packed": False, "essential": True, "note": ""},
        {"name": "太阳镜", "packed": False, "essential": False, "note": ""},
        {"name": "便携水壶", "packed": False, "essential": True, "note": "多补水"},
        {"name": "藿香正气水", "packed": False, "essential": True, "note": "防中暑"},
    ]},
    "low_temp": {"category": "保暖", "icon": "🧥", "items": [
        {"name": "厚外套/羽绒服", "packed": False, "essential": True, "note": "低温必备"},
        {"name": "保暖内衣", "packed": False, "essential": False, "note": ""},
        {"name": "手套围巾", "packed": False, "essential": False, "note": ""},
    ]},
    "strong_wind": {"category": "防风", "icon": "💨", "items": [
        {"name": "防风外套", "packed": False, "essential": True, "note": "强风天气"},
    ]},
    "smog": {"category": "防护", "icon": "😷", "items": [
        {"name": "口罩（N95）", "packed": False, "essential": True, "note": "雾霾天必备"},
    ]},
}


# ── 人群驱动清单（按实际年龄段和构成触发） ──────────────

PEOPLE_RULES = {
    "family_baby": {"category": "婴儿用品", "icon": "🍼", "items": [
        {"name": "纸尿布", "packed": False, "essential": True, "note": "根据天数准备"},
        {"name": "退烧贴×3", "packed": False, "essential": True, "note": "婴儿退烧备用"},
        {"name": "奶瓶/奶粉/辅食", "packed": False, "essential": True, "note": "婴儿必备"},
        {"name": "婴儿湿巾", "packed": False, "essential": True, "note": ""},
        {"name": "折叠推车", "packed": False, "essential": False, "note": "走累了可选"},
    ]},
    "family_child": {"category": "儿童用品", "icon": "🧒", "items": [
        {"name": "儿童退烧贴×3", "packed": False, "essential": True, "note": "发烧备用"},
        {"name": "小零食/饼干", "packed": False, "essential": False, "note": "孩子饿了应急"},
        {"name": "儿童防晒霜", "packed": False, "essential": False, "note": "户外活动时"},
        {"name": "小水壶", "packed": False, "essential": True, "note": "随时补水"},
    ]},
    "family_elder": {"category": "老人用品", "icon": "👴", "items": [
        {"name": "舒适平底鞋", "packed": False, "essential": True, "note": "避免高跟鞋/硬底鞋"},
        {"name": "折叠拐杖", "packed": False, "essential": False, "note": "行走不便时使用"},
    ]},
    "family_child_elder": {"category": "家庭出行用品", "icon": "👨‍👩‍👧‍👦", "items": [
        {"name": "儿童退烧贴×3", "packed": False, "essential": True, "note": "发烧备用"},
        {"name": "小零食/饼干", "packed": False, "essential": False, "note": "孩子饿了应急"},
        {"name": "小水壶", "packed": False, "essential": True, "note": "随时补水"},
        {"name": "舒适平底鞋（老人）", "packed": False, "essential": True, "note": "避免硬底鞋"},
    ]},
}


# ── 特殊需求驱动清单（按用户实际健康状况触发） ──────────

SPECIAL_NEEDS_RULES = {
    "高血压": {"category": "慢病用药", "icon": "💊", "items": [
        {"name": "降压药（按医嘱剂量）", "packed": False, "essential": True, "note": "高血压患者必备"},
        {"name": "便携血压计", "packed": False, "essential": False, "note": "随时监测"},
    ]},
    "糖尿病": {"category": "慢病用药", "icon": "💊", "items": [
        {"name": "降糖药/胰岛素", "packed": False, "essential": True, "note": "糖尿病患者必备"},
        {"name": "血糖仪+试纸", "packed": False, "essential": True, "note": "随时监测"},
        {"name": "糖果/葡萄糖片", "packed": False, "essential": True, "note": "低血糖应急"},
    ]},
    "心脏病": {"category": "慢病用药", "icon": "💊", "items": [
        {"name": "心脏药物（按医嘱）", "packed": False, "essential": True, "note": "心脏病患者必备"},
        {"name": "速效救心丸", "packed": False, "essential": True, "note": "急救备用"},
    ]},
    "哮喘": {"category": "慢病用药", "icon": "💊", "items": [
        {"name": "哮喘喷雾剂", "packed": False, "essential": True, "note": "随身携带"},
        {"name": "口罩", "packed": False, "essential": True, "note": "防粉尘/花粉"},
    ]},
    "孕妇": {"category": "孕期用品", "icon": "🤰", "items": [
        {"name": "孕妇维生素/叶酸", "packed": False, "essential": True, "note": "按医嘱"},
        {"name": "孕妇枕/腰垫", "packed": False, "essential": False, "note": "乘车/住宿时"},
        {"name": "产检资料复印件", "packed": False, "essential": True, "note": "应急就医用"},
    ]},
    "腰椎间盘突出": {"category": "康复用品", "icon": "🏥", "items": [
        {"name": "护腰带", "packed": False, "essential": True, "note": "长时间行走时"},
        {"name": "止痛药（布洛芬）", "packed": False, "essential": True, "note": "疼痛应急"},
    ]},
    "膝关节不好": {"category": "康复用品", "icon": "🏥", "items": [
        {"name": "护膝", "packed": False, "essential": True, "note": "保护膝关节"},
        {"name": "登山杖", "packed": False, "essential": False, "note": "减轻膝盖负担"},
    ]},
}


# ── 过敏史驱动清单 ──────────────────────────────────────

ALLERGY_RULES = {
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
    "宠物毛发过敏": {"category": "过敏防护", "icon": "🤧", "items": [
        {"name": "抗过敏药", "packed": False, "essential": True, "note": "宠物毛发过敏"},
    ]},
    "紫外线过敏": {"category": "过敏防护", "icon": "🤧", "items": [
        {"name": "高倍防晒霜（SPF50+）", "packed": False, "essential": True, "note": "紫外线过敏必备"},
        {"name": "防晒衣/长袖", "packed": False, "essential": True, "note": "物理防晒"},
    ]},
}


# ── 通用药品（仅在没有特定健康需求时添加） ────────────

COMMON_MEDICINE = {"category": "药品与健康", "icon": "💊", "items": [
    {"name": "感冒药", "packed": False, "essential": True, "note": "通用"},
    {"name": "创可贴", "packed": False, "essential": False, "note": "通用"},
    {"name": "肠胃药", "packed": False, "essential": True, "note": "水土不服备用"},
    {"name": "晕车药", "packed": False, "essential": False, "note": "晕车者必备"},
]}


# ── 饮食忌口驱动清单 ──────────────────────────────────

DIETARY_RULES = {
    "素食": {"category": "饮食提醒", "icon": "🥬", "items": [
        {"name": "素食能量棒/坚果", "packed": False, "essential": False, "note": "找不到素食餐厅时应急"},
    ]},
    "清真": {"category": "饮食提醒", "icon": "🥬", "items": [
        {"name": "提前查好清真餐厅", "packed": False, "essential": True, "note": "清真饮食需求"},
    ]},
}


def _classify_weather(weather_text: str) -> list[str]:
    """从天气文本中智能提取天气标签，基于实际温度判断。"""
    tags = []
    temp = None

    # 提取温度数字
    temps = re.findall(r'(\d+)', weather_text)
    for t in temps:
        try:
            val = int(t)
            if 0 <= val <= 50:  # 合理温度范围
                temp = val
                break
        except ValueError:
            continue

    # 雨天判断
    if any(k in weather_text for k in ("雨", "雷", "阵雨", "暴雨", "小雨", "中雨", "大雨")):
        tags.append("rain")

    # 温度驱动（精确判断，不瞎猜）
    if temp is not None:
        if temp >= 33:
            tags.append("high_temp")
        elif temp <= 10:
            tags.append("low_temp")
        # 10-33°C 不加保暖也不加防晒（舒适区间）
    else:
        # 无温度数据时，通过天气关键词粗略判断
        if any(k in weather_text for k in ("高温", "炎热", "酷暑")):
            tags.append("high_temp")
        elif any(k in weather_text for k in ("低温", "寒冷", "降温")):
            tags.append("low_temp")

    # 大风判断
    if any(k in weather_text for k in ("大风", "强风", "台风", "风暴")):
        tags.append("strong_wind")
    # 数字风级判断
    wind_match = re.search(r'(\d+)级', weather_text)
    if wind_match and int(wind_match.group(1)) >= 6:
        tags.append("strong_wind")

    # 雾霾判断
    if any(k in weather_text for k in ("雾", "霾")):
        tags.append("smog")

    return tags


def _get_all_used_names(categories: list[dict]) -> set[str]:
    """获取所有已添加物品的名称集合（去重用）。"""
    return {item["name"] for cat in categories for item in cat["items"]}


async def generate_checklist(
    destination: str,
    days: int,
    weather: str = "",
    composition: str = "",
    allergies: list[str] | None = None,
    special_needs: list[str] | None = None,
    dietary: list[str] | None = None,
    child_age: int | None = None,
    group_size: int = 2,
    budget_tier: str = "",
) -> dict:
    """
    智能清单生成：根据出行档案 + 天气 + 健康状况动态生成。

    参数:
        destination: 目的地
        days: 旅行天数
        weather: 天气文本（如"中雨 28°C"）
        composition: 人员构成（family_baby/family_child/family_elder/family_child_elder）
        allergies: 过敏列表（如["花粉过敏","尘螨过敏"]）
        special_needs: 特殊需求（如["高血压","糖尿病"]）
        dietary: 饮食忌口（如["素食","清真"]）
        child_age: 儿童年龄
        group_size: 出行人数
        budget_tier: 预算等级
    """
    categories = []
    used_names = set()

    def _add_items(cat_data: dict):
        """去重后添加物品到分类。"""
        nonlocal used_names
        new_items = [i for i in cat_data["items"] if i["name"] not in used_names]
        if new_items:
            categories.append({
                "category": cat_data["category"],
                "icon": cat_data["icon"],
                "items": new_items,
            })
            used_names.update(i["name"] for i in new_items)

    # ── 1. 固定清单 ─────────────────────────────────────
    categories.append({
        "category": "证件与钱",
        "icon": "📄",
        "items": FIXED_ITEMS.copy(),
    })
    used_names.update(i["name"] for i in FIXED_ITEMS)

    # ── 2. 天气驱动（基于实际天气条件） ──────────────────
    weather_tags = _classify_weather(weather)
    for tag in weather_tags:
        rule = WEATHER_RULES.get(tag)
        if rule:
            _add_items(rule)

    # ── 3. 人群驱动（按实际构成和年龄） ──────────────────
    if composition in PEOPLE_RULES:
        rule = PEOPLE_RULES[composition]
        _add_items(rule)

    # ── 4. 特殊需求驱动（健康状况 → 对应药品/用品） ──────
    if special_needs:
        for need in special_needs:
            rule = SPECIAL_NEEDS_RULES.get(need)
            if rule:
                _add_items(rule)

    # ── 5. 过敏史驱动 ──────────────────────────────────
    if allergies:
        for allergy in allergies:
            rule = ALLERGY_RULES.get(allergy)
            if rule:
                _add_items(rule)

    # ── 6. 饮食忌口驱动 ────────────────────────────────
    if dietary:
        for d in dietary:
            rule = DIETARY_RULES.get(d)
            if rule:
                _add_items(rule)

    # ── 7. 通用药品（仅在没有特定健康需求时添加） ──────
    has_medicine = any(
        cat["category"] in ("慢病用药", "康复用药", "药品与健康")
        for cat in categories
    )
    if not has_medicine:
        _add_items(COMMON_MEDICINE)

    # ── 8. LLM 智能补充（传入完整档案） ────────────────
    try:
        extra_items = await _llm_supplement(
            destination=destination,
            days=days,
            weather=weather,
            composition=composition,
            allergies=allergies or [],
            special_needs=special_needs or [],
            dietary=dietary or [],
            group_size=group_size,
            budget_tier=budget_tier,
        )
        if extra_items:
            # 去重后添加
            new_extras = [i for i in extra_items if i.get("name") not in used_names]
            if new_extras:
                categories.append({
                    "category": f"{destination}特色",
                    "icon": "🎯",
                    "items": new_extras,
                })
    except Exception:
        logger.debug("LLM特色物品补充跳过")

    # 生成元信息
    generated_from = {
        "destination": destination,
        "days": days,
        "weather": weather,
        "weather_tags": weather_tags,
        "composition": composition,
        "allergies": allergies or [],
        "special_needs": special_needs or [],
        "dietary": dietary or [],
        "child_age": child_age,
        "group_size": group_size,
        "budget_tier": budget_tier,
    }

    return {
        "categories": categories,
        "generated_from": generated_from,
    }


async def _llm_supplement(
    destination: str,
    days: int,
    weather: str,
    composition: str,
    allergies: list[str],
    special_needs: list[str],
    dietary: list[str],
    group_size: int,
    budget_tier: str,
) -> list[dict]:
    """用 LLM 补充目的地特色物品（传入完整出行档案）。"""
    # 构建用户画像摘要
    profile_lines = []
    if composition:
        profile_lines.append(f"人员构成：{composition}")
    if group_size:
        profile_lines.append(f"出行人数：{group_size}人")
    if allergies:
        profile_lines.append(f"过敏史：{'、'.join(allergies)}")
    if special_needs:
        profile_lines.append(f"特殊需求：{'、'.join(special_needs)}")
    if dietary:
        profile_lines.append(f"饮食忌口：{'、'.join(dietary)}")
    if budget_tier:
        profile_lines.append(f"预算等级：{budget_tier}")

    profile_text = "\n".join(profile_lines) if profile_lines else "普通用户"

    prompt = f"""你是旅行清单专家。请根据以下信息，为用户补充3-6个目的地特色物品。

## 目的地信息
- 目的地：{destination}
- 天数：{days}天
- 天气：{weather or '未知'}

## 用户画像
{profile_text}

## 要求
1. 根据目的地特点推荐特色物品（如海边→防水袋，高原→氧气瓶，山区→登山杖）
2. 根据用户健康状况推荐相关物品（如高血压→低盐食品，糖尿病→糖果）
3. 根据天气推荐实际需要的物品（不要推荐与天气矛盾的东西）
4. 根据人群特点推荐（如带老人→折叠椅，带小孩→玩具）
5. 每个物品必须有合理的note说明

输出JSON数组格式：
[{{"name":"物品名","packed":false,"essential":false,"note":"推荐原因"}}]

只输出JSON，不要其他文字。"""

    raw = await call_llm(
        messages=[{"role": "user", "content": f"为{destination}旅行补充特色物品"}],
        system_prompt=prompt,
        temperature=0.3,
        max_tokens=500,
    )
    try:
        items = json.loads(raw)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        # 尝试从文本中提取JSON
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []
