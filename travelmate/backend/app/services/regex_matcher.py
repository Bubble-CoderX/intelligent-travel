from __future__ import annotations

import re
from typing import Optional

# 预编译所有正则表达式
_GREETING_PATTERNS = [
    re.compile(r"^(你好|您好|嗨|hi|hello|hey|哈喽)[！!？?。.]*$", re.IGNORECASE),
]

_FAREWELL_PATTERNS = [
    re.compile(r"^(再见|拜拜|bye|goodbye|下次见)[！!？?。.]*$", re.IGNORECASE),
]

_THANKS_PATTERNS = [
    re.compile(r"^(谢谢|感谢|多谢|thanks|thx)[你您！!？?。.]*$", re.IGNORECASE),
]

_CONFIRM_PATTERNS = [
    re.compile(r"^(好的|没问题|ok|嗯|可以|行)[！!？?。.]*$", re.IGNORECASE),
]

_MATCHERS = [
    ("greeting", _GREETING_PATTERNS, "你好呀！我是 AI 智游伴，你的专属旅行助手。有什么旅行问题可以问我哦～"),
    ("farewell", _FAREWELL_PATTERNS, "再见！祝你旅途愉快，期待下次为你服务～"),
    ("thanks", _THANKS_PATTERNS, "不客气！能帮到你我也很开心～"),
    ("confirm", _CONFIRM_PATTERNS, "好的，收到！"),
]


def regex_match(text: str) -> Optional[tuple[str, str]]:
    """第一层正则匹配，返回 (intent, response) 或 None。使用预编译正则。"""
    text = text.strip()
    if len(text) > 50:
        return None

    for intent, patterns, response in _MATCHERS:
        for pattern in patterns:
            if pattern.match(text):
                return (intent, response)

    return None
