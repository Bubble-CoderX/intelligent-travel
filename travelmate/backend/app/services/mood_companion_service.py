"""F10: 旅途情绪感知与陪伴——多维度情绪检测 + 按情绪类型生成有温度的回应。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ── 情绪词典 ──────────────────────────────────────────────

MOOD_DICT: dict[str, list[str]] = {
    "anxious": [
        "焦虑", "着急", "赶不上", "来不及", "怎么办", "急死", "慌", "担心",
        "害怕", "恐惧", "不安", "紧张", "忐忑", "慌张", "手足无措",
    ],
    "down": [
        "难过", "伤心", "失望", "无聊", "没意思", "不想", "好累", "疲惫",
        "心累", "郁闷", "孤单", "孤独", "想家", "不开心", "低落", "消沉",
    ],
    "annoyed": [
        "烦", "讨厌", "气死", "受够", "受不了", "什么破", "太差", "垃圾",
        "坑", "被骗", "不公平", "倒霉", "服了", "无语", "醉了", "火大",
    ],
    "happy": [
        "开心", "高兴", "太棒", "好美", "好看", "震撼", "值得", "推荐",
        "满意", "享受", "舒服", "惬意", "完美", "绝了", "爱了", "惊喜",
        "感动", "不错", "好玩", "好吃",
    ],
}

MOOD_LABELS = {
    "anxious": "焦虑",
    "down": "低落",
    "annoyed": "烦躁",
    "happy": "开心",
    "neutral": "平静",
}


# ── 功能性查询排除列表 ────────────────────────────────────

# 这些正则匹配的消息是功能查询，不应被情绪检测拦截
_FUNCTIONAL_PATTERNS = [
    re.compile(r"(天气|温度|气温|下雨|晴|多云|穿什么|带伞)"),
    re.compile(r"(行程|规划|攻略|路线|旅游|旅行|景点|推荐|好玩|好吃)"),
    re.compile(r"(历史|故事|文化|介绍|知识|讲解|攻略)"),
    re.compile(r"(偏好|设置|删除|新建|切换|重命名)"),
    re.compile(r"(体感|舒适度|TCI|出行指数)"),
    re.compile(r"(日报|周报|天气报告)"),
]


def _is_functional_query(text: str) -> bool:
    """判断消息是否为功能性查询（天气/行程/知识等），如果是则跳过情绪检测。"""
    return any(p.search(text) for p in _FUNCTIONAL_PATTERNS)


# ── 情绪检测 ──────────────────────────────────────────────

@dataclass
class MoodResult:
    """情绪检测结果。"""
    primary_mood: str        # 主要情绪类型
    confidence: float        # 置信度 0-1
    mood_label: str          # 中文标签
    signals: list[str]       # 触发的信号描述


def _count_mood_words(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """统计文本中某类情绪词的出现次数和匹配词。"""
    matched = [kw for kw in keywords if kw in text]
    return len(matched), matched


def _detect_mood_from_text(text: str) -> MoodResult:
    """从文本内容检测情绪。"""
    scores: dict[str, tuple[int, list[str]]] = {}
    for mood, keywords in MOOD_DICT.items():
        count, matched = _count_mood_words(text, keywords)
        if count > 0:
            scores[mood] = (count, matched)

    if not scores:
        return MoodResult("neutral", 0.3, MOOD_LABELS["neutral"], [])

    # 选得分最高的
    best_mood = max(scores, key=lambda m: scores[m][0])
    count, matched = scores[best_mood]
    confidence = min(1.0, 0.3 + count * 0.2)

    signals = [f"检测到情绪词「{w}」" for w in matched[:3]]
    return MoodResult(best_mood, confidence, MOOD_LABELS[best_mood], signals)


def _detect_mood_from_time(hour: int) -> str | None:
    """时段信号：深夜更易低落。"""
    if 0 <= hour <= 5:
        return "late_night"
    return None


def detect_mood(text: str, recent_texts: list[str] | None = None) -> MoodResult:
    """
    综合情绪检测：
    1. 文本情绪词检测（主信号）
    2. 消息频率分析（辅助）
    3. 时段信号（辅助）
    """
    # 文本检测
    result = _detect_mood_from_text(text)

    # 时段辅助：深夜只加强已有情绪，不凭空创造
    time_signal = _detect_mood_from_time(datetime.now().hour)
    if time_signal == "late_night" and result.primary_mood not in ("neutral",):
        result.confidence = min(1.0, result.confidence + 0.1)
        result.signals.append("深夜时段加强")

    # 消息频率辅助：连续短消息可能暗示焦虑
    if recent_texts:
        recent_short = sum(1 for t in recent_texts[-5:] if len(t) < 5)
        if recent_short >= 3 and result.primary_mood not in ("neutral",):
            result.confidence = min(1.0, result.confidence + 0.1)
            result.signals.append("连续短消息加强")

    return result


# ── 情绪回应生成 ──────────────────────────────────────────

MOOD_SYSTEM_PROMPTS: dict[str, str] = {
    "anxious": (
        "你是「AI智游伴」，用户此刻感到焦虑不安。"
        "请用平静温和的语气安抚，给出具体可行的建议。"
        "不要说「别焦虑」这种空话，而是给出实际帮助。2-3句话。"
    ),
    "down": (
        "你是「AI智游伴」，用户此刻情绪低落。"
        "请用温暖理解的语气陪伴，不要强行正能量。"
        "可以说「理解你的心情」，然后轻轻转移话题到美好的事物。2-3句话。"
    ),
    "annoyed": (
        "你是「AI智游伴」，用户此刻感到烦躁。"
        "请先表示理解和共情，不要辩解或反驳。"
        "然后提供一个解决问题的思路或替代方案。2-3句话。"
    ),
    "happy": (
        "你是「AI智游伴」，用户此刻很开心。"
        "请分享用户的快乐，热情回应！"
        "可以追问细节或推荐相关体验，让快乐延续。2-3句话。"
    ),
}


async def generate_mood_response(
    mood: MoodResult,
    user_message: str,
    city: str = "",
    **kwargs,
) -> str:
    """根据情绪类型生成有温度的回应。"""
    from app.services.llm_client import call_llm

    system_prompt = MOOD_SYSTEM_PROMPTS.get(mood.primary_mood)
    if not system_prompt:
        return ""  # neutral 情绪不干预

    context_parts = [f"用户消息：{user_message}"]
    if city:
        context_parts.append(f"当前城市：{city}")
    context_parts.append(f"情绪检测：{mood.mood_label}（置信度{mood.confidence:.0%}）")
    context_parts.append(f"信号：{'、'.join(mood.signals)}")

    full_prompt = system_prompt + "\n\n" + "\n".join(context_parts)

    response = await call_llm(
        messages=[{"role": "user", "content": user_message}],
        system_prompt=full_prompt,
        temperature=0.8,
        max_tokens=200,
    )
    return response.strip()


# ── 意图管道集成入口 ──────────────────────────────────────

async def intercept_mood_in_chat(
    user_message: str,
    device_id: str = "",
    city: str = "",
    recent_texts: list[str] | None = None,
) -> dict | None:
    """
    在意图识别前拦截情绪响应。
    如果检测到高置信度情绪，返回 {"mood_response": str, "mood": MoodResult}
    否则返回 None，让正常意图流程继续。
    """
    # 功能性查询直接跳过，不拦截
    if _is_functional_query(user_message):
        return None

    mood = detect_mood(user_message, recent_texts)

    if mood.confidence < 0.4 or mood.primary_mood == "neutral":
        return None

    response = await generate_mood_response(mood, user_message, city=city)

    return {
        "mood_response": response,
        "mood_type": mood.primary_mood,
        "mood_label": mood.mood_label,
        "confidence": mood.confidence,
        "signals": mood.signals,
    }
