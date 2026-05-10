from __future__ import annotations

import re
from typing import Optional

GREETING_PATTERNS = [
    r"^(你好|您好|嗨|hi|hello|hey|哈喽)[！!？?。.]*$",
]

FAREWELL_PATTERNS = [
    r"^(再见|拜拜|bye|goodbye|下次见)[！!？?。.]*$",
]

THANKS_PATTERNS = [
    r"^(谢谢|感谢|多谢|thanks|thx)[你您！!？?。.]*$",
]

CONFIRM_PATTERNS = [
    r"^(好的|没问题|ok|嗯|可以|行)[！!？?。.]*$",
]

MATCHERS = [
    ("greeting", GREETING_PATTERNS, "你好呀！我是 AI 智游伴，你的专属旅行助手。有什么旅行问题可以问我哦～"),
    ("farewell", FAREWELL_PATTERNS, "再见！祝你旅途愉快，期待下次为你服务～"),
    ("thanks", THANKS_PATTERNS, "不客气！能帮到你我也很开心～"),
    ("confirm", CONFIRM_PATTERNS, "好的，收到！"),
]


def regex_match(text: str) -> Optional[tuple[str, str]]:
    """第一层正则匹配，返回 (intent, response) 或 None。"""
    text = text.strip()
    if len(text) > 50:
        return None

    for intent, patterns, response in MATCHERS:
        for pattern in patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return (intent, response)

    return None
