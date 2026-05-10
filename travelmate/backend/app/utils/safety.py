from __future__ import annotations

# ── 输入安全关键词 ────────────────────────────────────────

BLOCK_KEYWORDS = [
    "怎么偷", "怎么骗", "怎么逃票", "怎么逃单",
    "翻越围栏", "闯红灯", "禁止进入",
]

WARN_KEYWORDS = [
    ("独自旅行", "独自旅行请注意安全，建议告知家人朋友你的行程。"),
    ("夜路", "夜间出行建议使用正规交通工具，注意人身安全。"),
    ("偏远地区", "前往偏远地区建议提前告知他人行程，携带必要物资。"),
]

URGENT_KEYWORDS = [
    "高原反应", "中暑", "溺水", "食物中毒", "受伤",
]

# ── 输出安全关键词 ────────────────────────────────────────

DANGEROUS_OUTPUT_PHRASES = [
    "建议你去翻越", "可以尝试逃票", "不用担心安全",
]


def input_safety_check(text: str) -> dict:
    """输入安全检查。"""
    for keyword in BLOCK_KEYWORDS:
        if keyword in text:
            return {"passed": False, "level": "BLOCK", "reason": f"包含违禁内容：{keyword}"}

    for keyword, msg in WARN_KEYWORDS:
        if keyword in text:
            return {"passed": True, "level": "WARN", "warning": msg}

    for keyword in URGENT_KEYWORDS:
        if keyword in text:
            return {
                "passed": True,
                "level": "URGENT",
                "warning": f"检测到「{keyword}」相关表述，如您遇到紧急情况请拨打110或120。",
            }

    return {"passed": True, "level": "SAFE"}


def output_safety_check(text: str) -> dict:
    """输出安全检查——确保 AI 回复不包含危险信息。"""
    for phrase in DANGEROUS_OUTPUT_PHRASES:
        if phrase in text:
            return {"passed": False, "reason": f"回复包含不当内容：{phrase}"}
    return {"passed": True}
