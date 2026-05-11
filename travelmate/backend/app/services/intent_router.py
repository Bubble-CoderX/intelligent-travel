from __future__ import annotations

import asyncio
import json
import logging

from app.models.database import get_db
from app.services.llm_client import call_llm
from app.services.map_service import search_places
from app.services.memory_service import get_all_preferences, query_memory, save_memory
from app.services.rag_service import query_knowledge
from app.services.regex_matcher import regex_match
from app.services.trip_service import generate_trip_plan, query_trip_plans
from app.services.weather_service import get_weather_forecast
from app.utils.safety import input_safety_check, output_safety_check, filter_llm_output

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
    """从记忆服务读取用户偏好，拼成文本供 LLM 参考。"""
    prefs = get_all_preferences(device_id)
    if not prefs:
        return "（暂无历史偏好）"
    return "\n".join(f"- {p['category']}/{p['key']}: {p['value']}" for p in prefs)


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
    intent_prompt = INTENT_RECOGNITION_PROMPT.replace(
        "{user_message}", user_message
    ).replace(
        "{user_preferences}", _get_user_preferences(device_id)
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

    intent = intent_data.get("intent", "CHAT")
    reasoning = intent_data.get("reasoning", "")
    extracted = intent_data.get("extracted_data", {})

    # 阶段四：PREFERENCE 意图自动写入记忆系统
    if intent == "PREFERENCE" and extracted.get("key"):
        cat = extracted.get("category", "通用")
        key = extracted.get("key", "")
        val = extracted.get("value", "")
        saved = save_memory(device_id, cat, key, val)
        if saved:
            reply = f"已记住你的偏好：{key} - {val}。之后的推荐会参考这个偏好哦～"
        else:
            reply = f"已识别你的偏好：{key} - {val}，但保存时遇到了问题。"

    # 阶段六：TRIP_PLAN 意图 → 调用行程生成服务
    elif intent == "TRIP_PLAN":
        destination = extracted.get("destination", "")
        trip_days = extracted.get("days")
        if not destination:
            reply = "请问你想去哪里旅行呢？告诉我目的地和天数，我来帮你规划～"
        elif not trip_days:
            reply = f"好的，你想去{destination}！请问计划玩几天呢？"
            # WARN/URGENT 安全前缀
            if safety.get("level") in ("WARN", "URGENT") and safety.get("warning"):
                reply = f"请注意：{safety['warning']}\n\n{reply}"
        else:
            # URGENT 场景：优先安全，暂不生成完整行程
            if safety.get("level") == "URGENT":
                reply = f"{safety.get('warning', '')}\n\n当前不适宜生成完整行程计划，请先确保安全情况。"
            else:
                try:
                    result = await generate_trip_plan(device_id, destination, int(trip_days))
                    reply = result["itinerary"]
                    if safety.get("level") == "WARN" and safety.get("warning"):
                        reply = f"> {safety['warning']}\n\n{reply}"
                except Exception as exc:
                    logger.warning("行程生成失败：%s", exc)
                    reply = f"生成{destination}行程时遇到了问题：{type(exc).__name__}。请稍后再试。"

    # 阶段五：WEATHER 意图 → 调用天气服务
    elif intent == "WEATHER":
        city = extracted.get("city", "")
        if not city:
            reply = "请问你想查哪个城市的天气呢？"
        else:
            try:
                weather_data = await asyncio.to_thread(get_weather_forecast, city)
                days = weather_data.get("days", [])
                if days:
                    today = days[0]
                    reply = (
                        f"🌤 **{city}天气预报**（{weather_data.get('report_time', '')}更新）\n\n"
                        f"**今日**：白天 {today['day_weather']} {today['day_temp']}℃，"
                        f"夜间 {today['night_weather']} {today['night_temp']}℃，"
                        f"{today['day_wind']}风\n"
                    )
                    if len(days) > 1:
                        future = " | ".join(
                            f"{d['date'][-5:]} {d['day_weather']} {d['day_temp']}~{d['night_temp']}℃"
                            for d in days[1:]
                        )
                        reply += f"\n**未来几天**：{future}"
                else:
                    reply = f"已查询{city}天气，但暂无预报数据。"
            except Exception as exc:
                logger.warning("天气查询失败：%s", exc)
                reply = f"查询{city}天气时遇到了问题：{type(exc).__name__}。请稍后再试。"

    # 阶段五+七：KNOWLEDGE 意图 → RAG 知识检索 + LLM 导游式回答
    elif intent == "KNOWLEDGE":
        spot = extracted.get("spot_name", "")
        city = extracted.get("city", "")
        keyword = spot or city
        if not keyword:
            reply = "请问你想了解哪个景点或城市的信息呢？"
        else:
            try:
                reply = await query_knowledge(user_message)
            except Exception as exc:
                logger.warning("知识查询失败：%s", exc)
                reply = f"查询「{keyword}」时遇到了问题：{type(exc).__name__}。请稍后再试。"

    else:
        # CHAT 意图：调用 LLM 生成真正的回复（精简 prompt 减少 token 消耗）
        chat_prompt = "你是「AI智游伴」，友好专业的旅行助手。简洁温暖，1-3句话。"
        reply = await call_llm(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=chat_prompt,
            temperature=0.7,
            max_tokens=300,
        )

    # 输出安全过滤
    reply = await filter_llm_output(reply)

    return {
        "intent": intent,
        "sub_intent": intent_data.get("sub_intent", "chat_general"),
        "confidence": intent_data.get("confidence", 0.5),
        "reasoning": reasoning,
        "extracted_data": extracted,
        "reply": reply,
        "layer": "ai",
        "safety": safety,
    }
