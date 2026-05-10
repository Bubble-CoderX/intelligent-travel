from __future__ import annotations

import json
import logging

from app.models.database import get_db
from app.services.llm_client import call_llm
from app.services.regex_matcher import regex_match
from app.utils.safety import input_safety_check, output_safety_check

logger = logging.getLogger(__name__)

INTENT_RECOGNITION_PROMPT = """你是「AI智游伴」的意图识别引擎。

你的任务是分析用户输入，将其归类到以下意图类别之一，并提取关键参数。

## 意图分类体系

| 意图类别 | 代码 | 子意图 | 说明 |
|----------|------|--------|------|
| 行程规划 | TRIP_PLAN | trip_create / trip_modify / trip_query | 创建、修改或查询旅行计划 |
| 天气查询 | WEATHER | weather_current / weather_forecast | 查询当前天气或未来天气 |
| 偏好记录 | PREFERENCE | pref_set / pref_query | 用户设置或查询个人偏好（饮食、预算等） |
| 景点知识 | KNOWLEDGE | spot_intro / spot_nearby / spot_history | 景点介绍、周边查询、历史故事 |
| 闲聊问答 | CHAT | chat_general / chat_travel_tips | 普通对话、旅行小贴士 |

## 输出格式（严格 JSON）

{
  "intent": "意图代码",
  "sub_intent": "子意图代码",
  "confidence": 0.0-1.0,
  "reasoning": "简要推理过程",
  "extracted_data": {
    // 根据意图不同提取不同字段
    // TRIP_PLAN: {"destination": "...", "days": N, "budget": N, "preferences": ["..."]}
    // WEATHER: {"city": "...", "date": "..."}
    // PREFERENCE: {"category": "...", "key": "...", "value": "..."}
    // KNOWLEDGE: {"spot_name": "...", "info_type": "..."}
    // CHAT: {}
  }
}

## 意图优先级规则
1. PREFERENCE（用户明确表达偏好变更时最高优先）
2. TRIP_PLAN（包含目的地、天数等旅行规划关键词）
3. WEATHER（包含天气相关关键词）
4. KNOWLEDGE（包含景点名称或询问景点信息）
5. CHAT（以上都不匹配时）

## 用户消息
{user_message}

## 用户历史偏好（供参考）
{user_preferences}
"""


def _get_user_preferences(device_id: str) -> str:
    """从数据库读取用户偏好，拼成文本供 LLM 参考。"""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT category, key, value FROM user_preferences WHERE device_id = ?",
            (device_id,),
        ).fetchall()
        conn.close()
        if not rows:
            return "（暂无历史偏好）"
        return "\n".join(f"- {r['category']}/{r['key']}: {r['value']}" for r in rows)
    except Exception:
        return "（暂无历史偏好）"


async def route_intent(user_message: str, device_id: str) -> dict:
    """
    完整意图识别管道：
    输入安全检查 → 第一层正则 → 第二层 AI → 输出安全检查 → 返回结果
    """
    # 0. 输入安全检查
    safety = input_safety_check(user_message)
    if not safety["passed"]:
        return {
            "intent": "blocked",
            "reply": "抱歉，我无法处理这类请求。如果你遇到了旅行中的问题，我很乐意帮你解决。",
            "safety": safety,
        }

    # 1. 第一层：正则快速匹配
    regex_result = regex_match(user_message)
    if regex_result:
        intent, reply = regex_result
        return {"intent": intent, "reply": reply, "layer": "regex", "safety": safety}

    # 2. 第二层：AI 意图识别
    intent_prompt = INTENT_RECOGNITION_PROMPT.format(
        user_message=user_message,
        user_preferences=_get_user_preferences(device_id),
    )
    raw_response = await call_llm(
        messages=[{"role": "user", "content": user_message}],
        system_prompt=intent_prompt,
        temperature=0.1,
        max_tokens=500,
    )

    # 解析 AI 返回的 JSON
    try:
        intent_data = json.loads(raw_response)
    except json.JSONDecodeError:
        logger.warning("AI 意图识别返回非 JSON：%.200s", raw_response)
        intent_data = {
            "intent": "CHAT",
            "sub_intent": "chat_general",
            "confidence": 0.5,
            "reasoning": "LLM 返回格式异常，降级为闲聊",
            "extracted_data": {},
        }

    # 3. 输出安全检查
    output_safety = output_safety_check(raw_response)

    return {
        "intent": intent_data.get("intent", "CHAT"),
        "sub_intent": intent_data.get("sub_intent", "chat_general"),
        "confidence": intent_data.get("confidence", 0.5),
        "reasoning": intent_data.get("reasoning", ""),
        "extracted_data": intent_data.get("extracted_data", {}),
        "layer": "ai",
        "safety": output_safety,
    }
