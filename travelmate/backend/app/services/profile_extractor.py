"""O1: 对话式旅行档案提取——从用户消息中自动提取出行档案字段并存储。"""

from __future__ import annotations

import json
import logging
import re

from app.services.memory_service import get_all_preferences, save_memory

logger = logging.getLogger(__name__)

# ── 兴趣标签映射 ─────────────────────────────────────────
_INTEREST_MAP = {
    "历史": "history", "文化": "history", "博物馆": "history",
    "美食": "food", "小吃": "food", "餐厅": "food",
    "购物": "shopping", "买": "shopping", "商圈": "shopping",
    "自然": "nature", "公园": "nature",
    "拍照": "photography", "出片": "photography", "网红": "photography",
    "带娃": "kid_friendly", "亲子": "kid_friendly", "孩子玩": "kid_friendly",
}

# ── 过敏原映射 ───────────────────────────────────────────
_ALLERGY_KEYWORDS = {
    "花粉过敏": ["花粉过敏"],
    "季节性鼻炎": ["鼻炎", "季节性鼻炎"],
    "尘螨过敏": ["尘螨过敏", "尘螨"],
    "宠物毛发过敏": ["宠物毛发过敏", "宠物过敏"],
}

# ── 口味偏好映射 ─────────────────────────────────────────
# taste_preference = 不喜欢/喜欢什么口味（口味偏好）
# dietary = 不能吃什么（过敏/医嘱忌口）
_TASTE_NEGATIVE = {
    "不吃辣": ["不吃辣", "不能吃辣", "不要辣", "不喜欢辣", "讨厌辣", "别放辣"],
    "不吃酸": ["不吃酸", "不能吃酸", "不要酸", "不喜欢酸", "讨厌酸"],
    "不吃甜": ["不吃甜", "不要甜", "不喜欢甜食", "讨厌甜"],
    "不吃咸": ["不吃咸", "不要太咸", "不喜欢咸"],
    "不吃油腻": ["不吃油腻", "不要油腻", "不喜欢油腻", "清淡点"],
}
_TASTE_POSITIVE = {
    "清淡": ["喜欢清淡", "要清淡", "清淡为主", "吃得清淡"],
    "重口味": ["重口味", "口味要重", "喜欢重口"],
}


def extract_travel_profile(device_id: str, user_message: str) -> list[str]:
    """从用户消息中提取旅行档案信息并存储。返回本次提取到的字段名列表。"""
    msg = user_message
    extracted: list[str] = []

    # ── 出行人数 ────────────────────────────────────────
    # 优先匹配"一家X口"（更准确），支持阿拉伯数字和中文数字
    _CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    family_match = re.search(r'一家([一二两三四五六七八九十\d])口', msg)
    if family_match:
        raw = family_match.group(1)
        count = _CN_NUM.get(raw, int(raw) if raw.isdigit() else 0)
        if 1 <= count <= 20:
            save_memory(device_id, "travel_profile", "group_size", str(count))
            extracted.append("group_size")
    else:
        num_match = re.search(r'(\d+)\s*(?:个人|人|个人一起|个人去|个朋友)', msg)
        if num_match:
            count = int(num_match.group(1))
            if 1 <= count <= 20:
                save_memory(device_id, "travel_profile", "group_size", str(count))
                extracted.append("group_size")

    # ── 儿童信息 ────────────────────────────────────────
    child_match = re.search(r'(\d+)\s*岁[的小]*(?:孩子|女儿|儿子|宝宝|小孩|儿童)', msg)
    has_child = False
    if child_match:
        age = int(child_match.group(1))
        if age <= 18:
            save_memory(device_id, "travel_profile", "child_age", str(age))
            has_child = True
            # 婴儿(0-3) vs 儿童(4-12) vs 青少年(13-18)
            if age <= 3:
                save_memory(device_id, "travel_profile", "composition", "family_baby")
            else:
                save_memory(device_id, "travel_profile", "composition", "family_child")
            extracted.extend(["child_age", "composition"])

    # ── 老人信息 ────────────────────────────────────────
    elder_keywords = ["爸妈", "父母", "爷爷", "奶奶", "外公", "外婆", "长辈", "老人"]
    has_elder = any(w in msg for w in elder_keywords)
    if has_elder:
        elder_count = (
            msg.count("爸") + msg.count("妈")
            + msg.count("爷") + msg.count("奶")
            + msg.count("公") + msg.count("婆")
        )
        if elder_count == 0:
            elder_count = 2
        elder_count = min(elder_count, 4)
        save_memory(device_id, "travel_profile", "elder_count", str(elder_count))
        extracted.append("elder_count")
        # 同时有小孩和老人 → family_child_elder
        if has_child:
            save_memory(device_id, "travel_profile", "composition", "family_child_elder")
            if "composition" not in extracted:
                extracted.append("composition")
        elif not child_match:
            save_memory(device_id, "travel_profile", "composition", "family_elder")
            extracted.append("composition")

    # ── 简单人群推断 ────────────────────────────────────
    if "自己" in msg or "一个人" in msg or "独自" in msg:
        save_memory(device_id, "travel_profile", "group_size", "1")
        save_memory(device_id, "travel_profile", "composition", "solo")
        extracted.extend(["group_size", "composition"])
    elif any(w in msg for w in ["情侣", "和对象", "和女朋友", "和男朋友", "和另一半"]):
        save_memory(device_id, "travel_profile", "group_size", "2")
        save_memory(device_id, "travel_profile", "composition", "couple")
        extracted.extend(["group_size", "composition"])

    # ── 旅行风格 ────────────────────────────────────────
    if any(w in msg for w in ["慢慢玩", "不赶时间", "休闲", "放松", "度假", "悠闲"]):
        save_memory(device_id, "travel_profile", "travel_style", "leisure")
        extracted.append("travel_style")
    elif any(w in msg for w in ["打卡", "都去", "多去几个", "尽量多", "多玩"]):
        save_memory(device_id, "travel_profile", "travel_style", "checkin")
        extracted.append("travel_style")
    elif any(w in msg for w in ["深度", "仔细看", "了解历史", "文化", "深入"]):
        save_memory(device_id, "travel_profile", "travel_style", "deep")
        extracted.append("travel_style")

    # ── 兴趣标签 ────────────────────────────────────────
    new_interests: list[str] = []
    for keyword, tag in _INTEREST_MAP.items():
        if keyword in msg and tag not in new_interests:
            new_interests.append(tag)
    if new_interests:
        existing = _get_profile_field(device_id, "interests", [])
        merged = list(dict.fromkeys(existing + new_interests))
        save_memory(device_id, "travel_profile", "interests", json.dumps(merged, ensure_ascii=False))
        extracted.append("interests")

    # ── 饮食忌口（仅过敏/医嘱相关，口味偏好归 taste_preference）──
    new_dietary: list[str] = []
    if "海鲜" in msg and ("过敏" in msg or "不能吃" in msg or "不吃" in msg):
        new_dietary.append("海鲜过敏")
    if "芒果" in msg and ("过敏" in msg or "不能吃" in msg):
        new_dietary.append("芒果过敏")
    if "素食" in msg or "吃素" in msg:
        new_dietary.append("素食")
    if "清真" in msg:
        new_dietary.append("清真")
    if "医嘱" in msg or "医生说" in msg:
        # 医嘱忌口：提取具体忌口内容
        if "辣" in msg:
            new_dietary.append("医嘱忌辣")
        if "酒" in msg:
            new_dietary.append("医嘱忌酒")
        if "海鲜" in msg:
            new_dietary.append("医嘱忌海鲜")
    if new_dietary:
        existing = _get_profile_field(device_id, "dietary", [])
        merged = list(dict.fromkeys(existing + new_dietary))
        save_memory(device_id, "travel_profile", "dietary", json.dumps(merged, ensure_ascii=False))
        extracted.append("dietary")

    # ── 口味偏好（不喜欢/喜欢什么口味）────────────────────
    new_taste: list[str] = []
    for taste_val, keywords in _TASTE_NEGATIVE.items():
        if any(kw in msg for kw in keywords):
            new_taste.append(taste_val)
    for taste_val, keywords in _TASTE_POSITIVE.items():
        if any(kw in msg for kw in keywords):
            new_taste.append(taste_val)
    if new_taste:
        existing = _get_profile_field(device_id, "taste_preference", [])
        merged = list(dict.fromkeys(existing + new_taste))
        save_memory(device_id, "travel_profile", "taste_preference", json.dumps(merged, ensure_ascii=False))
        extracted.append("taste_preference")

    # ── 住宿偏好 ────────────────────────────────────────
    if "民宿" in msg:
        save_memory(device_id, "travel_profile", "accommodation", "民宿")
        extracted.append("accommodation")
    elif "酒店" in msg or "宾馆" in msg:
        save_memory(device_id, "travel_profile", "accommodation", "酒店")
        extracted.append("accommodation")
    elif "青旅" in msg or "背包" in msg:
        save_memory(device_id, "travel_profile", "accommodation", "青旅")
        extracted.append("accommodation")

    # ── 过敏史 ──────────────────────────────────────────
    new_allergies: list[str] = []
    for allergy_name, keywords in _ALLERGY_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            new_allergies.append(allergy_name)
    if new_allergies:
        existing = _get_profile_field(device_id, "allergies", [])
        merged = list(dict.fromkeys(existing + new_allergies))
        save_memory(device_id, "travel_profile", "allergies", json.dumps(merged, ensure_ascii=False))
        extracted.append("allergies")

    # ── 日均预算 ────────────────────────────────────────
    budget_match = re.search(r'(?:预算|每天|日均|一天)[^\d]*(\d+)\s*(?:元|块|¥|左右|上)', msg)
    if not budget_match:
        budget_match = re.search(r'(\d+)\s*(?:元|块|¥)\s*(?:每天|日均|一天|预算)', msg)
    if budget_match:
        daily = int(budget_match.group(1))
        if 10 <= daily <= 50000:
            save_memory(device_id, "travel_profile", "budget_daily", str(daily))
            tier_info = calculate_budget_tier(daily)
            save_memory(device_id, "travel_profile", "budget_tier", tier_info["tier"])
            extracted.extend(["budget_daily", "budget_tier"])

    if extracted:
        logger.info("旅行档案提取：%s → %s", device_id, extracted)

    return extracted


# ── 预算等级自动计算 ──────────────────────────────────────


def calculate_budget_tier(daily_budget: int) -> dict:
    """根据日均预算计算等级和行程策略。"""
    if daily_budget <= 200:
        return {
            "tier": "poor",
            "label": "穷游",
            "strategy": {
                "transport": "公共交通为主（地铁/公交/共享单车），不打车",
                "accommodation": "青旅/民宿多人间/经济型酒店",
                "food": "街边小吃/快餐/超市自带",
                "attractions": "免费景点为主，收费景点最多1个/天",
                "budget_split": {"transport": 0.10, "accommodation": 0.35, "food": 0.25, "ticket": 0.15, "other": 0.15},
            }
        }
    elif daily_budget <= 500:
        return {
            "tier": "economic",
            "label": "经济",
            "strategy": {
                "transport": "地铁/公交为主，短途可打车",
                "accommodation": "经济型酒店/民宿整套",
                "food": "当地特色餐厅+街边小吃混搭",
                "attractions": "热门景点+免费景点混搭",
                "budget_split": {"transport": 0.15, "accommodation": 0.40, "food": 0.20, "ticket": 0.15, "other": 0.10},
            }
        }
    elif daily_budget <= 1000:
        return {
            "tier": "comfortable",
            "label": "舒适",
            "strategy": {
                "transport": "打车+地铁混搭，远途可高铁",
                "accommodation": "中档酒店/品质民宿",
                "food": "评分高的特色餐厅",
                "attractions": "热门景点+小众景点混搭",
                "budget_split": {"transport": 0.15, "accommodation": 0.40, "food": 0.20, "ticket": 0.15, "other": 0.10},
            }
        }
    else:
        return {
            "tier": "luxury",
            "label": "奢华",
            "strategy": {
                "transport": "全程打车/租车",
                "accommodation": "高档酒店/精品民宿",
                "food": "高端餐厅+米其林/黑珍珠推荐",
                "attractions": "首选景点，可安排VIP/专属导览",
                "budget_split": {"transport": 0.15, "accommodation": 0.35, "food": 0.25, "ticket": 0.15, "other": 0.10},
            }
        }


# ── 出发地解析 ──────────────────────────────────────────


def resolve_departure(user_message: str, device_id: str, client_ip: str = "") -> str:
    """获取出发地。优先级：对话指定 > 偏好存储 > IP定位。"""
    # 1. 对话中是否提到了出发地
    departure_match = re.search(r'从([一-龥]{2,6})(?:出发|去|到|飞|坐|自驾)', user_message)
    if departure_match:
        return departure_match.group(1)

    # 2. 偏好中是否有手动设置的出发地
    prefs = get_all_preferences(device_id)
    for p in prefs:
        if p.get("key") == "departure_city" and p.get("value"):
            return p["value"]

    # 3. IP定位兜底
    if client_ip:
        from app.services.proactive_service import _ip_to_city
        city = _ip_to_city(client_ip)
        if city:
            return city

    return ""


# ── 工具函数 ────────────────────────────────────────────


def _get_profile_field(device_id: str, key: str, default=None):
    """从用户偏好中读取 travel_profile 的某个字段，自动反序列化 JSON 列表。"""
    prefs = get_all_preferences(device_id)
    for p in prefs:
        if p.get("category") == "travel_profile" and p.get("key") == key:
            val = p.get("value", "")
            # 尝试 JSON 反序列化（列表型字段）
            if isinstance(val, str) and val.startswith("["):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return default
            return val
    return default


def get_travel_profile_text(device_id: str) -> str:
    """将用户出行档案格式化为可注入 Prompt 的文本。"""
    prefs = get_all_preferences(device_id)
    profile = {p["key"]: p["value"] for p in prefs if p.get("category") == "travel_profile"}

    if not profile:
        return "（暂无出行档案记录）"

    LABEL_MAP = {
        "group_size": "出行人数",
        "composition": "人员构成",
        "child_age": "儿童年龄",
        "elder_count": "老人数量",
        "travel_style": "旅行风格",
        "interests": "兴趣标签",
        "fitness_level": "体力水平",
        "photo_need": "拍照需求",
        "dietary": "饮食忌口",
        "taste_preference": "口味偏好",
        "accommodation": "住宿偏好",
        "atmosphere": "氛围偏好",
        "budget_daily": "日均预算",
        "budget_tier": "预算等级",
        "allergies": "过敏史",
        "special_needs": "特殊需求",
        "transport_preference": "出行方式偏好",
        "departure_city": "出发地",
        "current_city": "当前城市",
    }

    COMPOSITION_MAP = {
        "solo": "独自出行",
        "couple": "情侣出行",
        "family_baby": "家庭（带婴儿）",
        "family_child": "家庭（带小孩）",
        "family_elder": "家庭（带老人）",
        "family_child_elder": "家庭（带小孩+老人）",
        "group": "多人结伴",
    }

    STYLE_MAP = {
        "deep": "深度游",
        "checkin": "打卡游",
        "leisure": "休闲游",
        "adventure": "探险游",
    }

    lines = []
    for key in [
        "group_size", "composition", "child_age", "elder_count",
        "travel_style", "interests", "taste_preference", "dietary",
        "accommodation", "budget_daily", "budget_tier",
        "allergies", "special_needs", "departure_city",
    ]:
        val = profile.get(key, "")
        if not val:
            continue
        label = LABEL_MAP.get(key, key)
        display = val
        # 解析列表型 JSON
        if isinstance(val, str) and val.startswith("["):
            try:
                parsed = json.loads(val)
                display = "、".join(str(v) for v in parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        elif key == "composition":
            display = COMPOSITION_MAP.get(val, val)
        elif key == "travel_style":
            display = STYLE_MAP.get(val, val)

        lines.append(f"- {label}：{display}")

    return "\n".join(lines) if lines else "（暂无出行档案记录）"
