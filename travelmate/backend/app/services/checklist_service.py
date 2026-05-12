"""旅行准备清单自动生成服务。"""

from __future__ import annotations

import json
import logging

from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

CHECKLIST_PROMPT = """你是一位贴心的旅行助手。请根据以下信息，为用户生成一份旅行准备清单。

## 行程信息
- 目的地：{destination}
- 天数：{days}天
- 天气：{weather}

## 输出格式（严格 JSON）

{{
  "categories": [
    {{
      "name": "证件",
      "icon": "📄",
      "items": ["身份证", "护照"]
    }},
    {{
      "name": "衣物",
      "icon": "👗",
      "items": ["根据天气推荐"]
    }},
    {{
      "name": "药品",
      "icon": "💊",
      "items": ["感冒药", "创可贴"]
    }},
    {{
      "name": "电子设备",
      "icon": "📱",
      "items": ["充电宝", "数据线"]
    }},
    {{
      "name": "日用品",
      "icon": "🧴",
      "items": ["防晒霜", "洗漱用品"]
    }},
    {{
      "name": "其他",
      "icon": "📦",
      "items": ["雨伞（根据天气）"]
    }}
  ]
}}

## 要求
- 根据目的地特点、天数、天气给出有针对性的清单
- 每个分类 3-6 项
- items 直接列出具体物品名称，不要空泛
- 如果有特殊需求（如高原、海边、冬季），调整分类
- 直接输出 JSON，不要包裹在代码块中
"""


async def generate_checklist(destination: str, days: int, weather: str = "") -> dict:
    """生成旅行准备清单。返回 {"categories": [...]}"""
    prompt = CHECKLIST_PROMPT.format(
        destination=destination,
        days=days,
        weather=weather or f"{destination}常规天气",
    )

    raw = await call_llm(
        messages=[{"role": "user", "content": f"为{destination}{days}天旅行生成准备清单"}],
        system_prompt=prompt,
        temperature=0.4,
        max_tokens=800,
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning("清单 JSON 解析失败：%.200s", raw)
        return {
            "categories": [
                {"name": "基本清单", "icon": "📋", "items": ["身份证/护照", "手机及充电器", "换洗衣物", "个人药品"]}
            ]
        }
