from __future__ import annotations

import asyncio
import json
import logging
import re

from app.models.database import get_db
from app.services.context_service import get_recent_history
from app.services.llm_client import call_llm
from app.services.map_service import search_places
from app.services.memory_service import get_all_preferences, query_memory, save_memory
from app.services.profile_extractor import extract_travel_profile, get_travel_profile_text, _get_profile_field
from app.services.rag_service import query_knowledge
from app.services.regex_matcher import regex_match
from app.services.trip_service import generate_trip_plan, query_trip_plans
from app.services.weather_service import get_weather_forecast
from app.utils.safety import input_safety_check, output_safety_check, filter_llm_output

logger = logging.getLogger(__name__)

# 特殊模式：自我介绍 / 回忆问题 → 直接走 CHAT，绕过 AI 意图识别
_INTRO_RE = re.compile(r"我(叫|是|的名字)")
_RECALL_RE = re.compile(r"(你还?记得|之前.*说过|刚才.*说过|上回.*说过)")

# 纠正模式：用户指出信息错误时触发知识库纠正
_CORRECTION_RE = re.compile(r"(不对|错了|更正|纠正|应该是|其实是|说错了|搞错了|不是.*是)")

INTENT_RECOGNITION_PROMPT = """你是「AI智游伴」的意图识别引擎。

你的任务是分析用户输入，将其归类到以下意图类别之一，并提取关键参数。
你必须结合对话历史来判断意图，不能仅凭当前消息中的单个关键词就下结论。

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

## 意图优先级规则（必须结合对话历史判断）
1. PREFERENCE（用户明确表达偏好变更时最高优先）
2. **上下文延续**（如果上一轮助手在询问某个意图的补充信息，用户回复的内容应延续该意图。例如：上轮问天气城市 → 用户回复地名 → 继续 WEATHER；上轮问行程天数 → 用户回复数字 → 继续 TRIP_PLAN）
3. TRIP_PLAN（包含目的地+天数等明确旅行规划意图）
4. WEATHER（包含天气相关关键词）
5. KNOWLEDGE（包含景点名称或询问景点信息）
6. CHAT（以上都不匹配时）

## 最近对话历史（用于判断上下文）
{recent_context}

## 用户消息
{user_message}

## 用户历史偏好（供参考）
{user_preferences}
"""


def _get_user_preferences(device_id: str) -> str:
    """从记忆服务读取用户偏好+出行档案，拼成文本供 LLM 参考。"""
    # 出行档案（结构化数据，优先展示）
    profile_text = get_travel_profile_text(device_id)

    # 通用偏好（旧格式兼容）
    prefs = get_all_preferences(device_id)
    legacy = [
        f"- {p['category']}/{p['key']}: {p['value']}"
        for p in prefs
        if p.get("category") not in ("travel_profile",)
    ]
    legacy_text = "\n".join(legacy) if legacy else "（无通用偏好）"

    return f"## 出行档案\n{profile_text}\n\n## 通用偏好\n{legacy_text}"


# ── 中文数字解析 ────────────────────────────────────────
_CN_NUM_MAP = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

def _parse_chinese_days(text) -> int:
    """解析中文天数（如"三天"→3, "十五天"→15），解析失败返回0。"""
    if not text:
        return 0
    s = str(text).strip().replace("天", "").replace("日", "")
    # 纯阿拉伯数字
    try:
        return int(s)
    except (ValueError, TypeError):
        pass
    # "十X" 形式，如 "十二"
    if len(s) == 2 and s[0] == "十":
        return 10 + _CN_NUM_MAP.get(s[1], 0)
    # "X十" 形式，如 "二十"
    if len(s) == 2 and s[1] == "十":
        return _CN_NUM_MAP.get(s[0], 0) * 10
    # "X十Y" 形式，如 "十五"
    if len(s) == 3 and s[1] == "十":
        return _CN_NUM_MAP.get(s[0], 0) * 10 + _CN_NUM_MAP.get(s[2], 0)
    # 单字，如 "三"
    if len(s) == 1:
        return _CN_NUM_MAP.get(s, 0)
    return 0


async def route_intent(user_message: str, device_id: str, session_id: str | None = None, trip_style: str | None = None) -> dict:
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

    # 0.5 对话式旅行档案自动提取（每条用户消息都执行）
    try:
        extract_travel_profile(device_id, user_message)
    except Exception:
        logger.debug("旅行档案提取失败，跳过", exc_info=True)

    # 1. 第一层：正则快速匹配
    regex_result = regex_match(user_message)
    if regex_result:
        intent, reply = regex_result
        return {"intent": intent, "reply": reply, "layer": "regex", "safety": safety}

    # 2. 特殊模式拦截：自我介绍 / 回忆问题 → 直接走 CHAT，不调 AI
    personal_keys = {"名字", "姓名", "年龄", "家乡", "职业", "性别", "爱好", "工作", "称呼", "身份"}
    intro_match = _INTRO_RE.search(user_message)
    recall_match = _RECALL_RE.search(user_message)
    if intro_match or recall_match:
        intent_data = {
            "intent": "CHAT",
            "sub_intent": "chat_general",
            "confidence": 1.0,
            "reasoning": "自我介绍/回忆类问题，直接走闲聊",
            "extracted_data": {},
        }
        raw_response = ""
        intent = "CHAT"
        reasoning = intent_data["reasoning"]
        extracted = {}
    else:
        # 3. 第二层：AI 意图识别（注入最近对话历史，让 LLM 理解上下文）
        recent = await get_recent_history(device_id, session_id=session_id, limit=6)
        recent_lines = []
        for m in recent[-6:]:
            role_label = "助手" if m["role"] == "assistant" else "用户"
            recent_lines.append(f"{role_label}：{m['content'][:80]}")
        recent_ctx = "\n".join(recent_lines) if recent_lines else "（无历史）"

        intent_prompt = INTENT_RECOGNITION_PROMPT.replace(
            "{user_message}", user_message
        ).replace(
            "{recent_context}", recent_ctx
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

        # 4. 输出安全检查
        output_safety = output_safety_check(raw_response)

        intent = intent_data.get("intent", "CHAT")
        reasoning = intent_data.get("reasoning", "")
        extracted = intent_data.get("extracted_data", {})

        # 个人信息不存为偏好，提前改回 CHAT
        if intent == "PREFERENCE" and extracted.get("key") in personal_keys:
            intent = "CHAT"

    # 阶段四：PREFERENCE 意图自动写入记忆系统
    if intent == "PREFERENCE" and extracted.get("key") and extracted.get("key") not in personal_keys:
        cat = extracted.get("category", "通用")
        key = extracted.get("key", "")
        val = extracted.get("value", "")

        # value 为空 → 查询意图（如"我的过敏史"），查找已有偏好回复
        if not val:
            # 中文key → travel_profile key 映射
            _CN_TO_PROFILE_KEY = {
                "过敏史": "allergies", "饮食忌口": "dietary", "旅行风格": "travel_style",
                "住宿偏好": "accommodation", "日均预算": "budget_daily", "预算等级": "budget_tier",
                "兴趣标签": "interests", "出行人数": "group_size", "人员构成": "composition",
                "特殊需求": "special_needs", "出行方式": "transport_preference",
            }
            profile_key = _CN_TO_PROFILE_KEY.get(key)
            if profile_key:
                val = _get_profile_field(device_id, profile_key, "")
                if val:
                    # 列表型值格式化
                    if isinstance(val, list):
                        val = "、".join(str(v) for v in val)
                    reply = f"你当前的{key}设置是：{val}。"
                else:
                    reply = f"目前还没有设置过「{key}」，你可以告诉我，我帮你记下～"
            else:
                existing_prefs = get_all_preferences(device_id)
                found = [p for p in existing_prefs if p.get("key") == key]
                if found:
                    reply = f"你当前的{key}设置是：{found[0]['value']}。"
                else:
                    reply = f"目前还没有设置过「{key}」，你可以告诉我，我帮你记下～"
        else:
            saved = save_memory(device_id, cat, key, str(val))
            if saved:
                reply = f"好的，已记住你的偏好：{val}。之后的推荐会参考它～"
            else:
                reply = f"收到你的偏好：{key} - {val}，但保存时遇到了问题。"

    # 阶段六：TRIP_PLAN 意图 → 调用行程生成服务
    elif intent == "TRIP_PLAN":
        destination = extracted.get("destination", "")
        trip_days = extracted.get("days")

        # 缺少目的地时，从对话历史中补全（代词消解："三天"→ 上文的"杭州"）
        if not destination:
            history = await get_recent_history(device_id, session_id=session_id)
            resolve_prompt = (
                "从以下对话历史中，提取用户最近提到的旅行目的地（城市或景点名），"
                "只返回名称，没有则返回\"无\"。"
            )
            hist_text = "\n".join(f"{m['role']}: {m['content']}" for m in history) if history else "（无历史）"
            resolved = await call_llm(
                messages=[{"role": "user", "content": f"历史：{hist_text}\n当前：{user_message}"}],
                system_prompt=resolve_prompt,
                temperature=0.0,
                max_tokens=50,
            )
            destination = resolved.strip() if resolved.strip() != "无" else ""

        if not destination:
            reply = "请问你想去哪里旅行呢？告诉我目的地和天数，我来帮你规划～"
        elif not trip_days:
            reply = f"好的，你想去{destination}！请问计划玩几天呢？"
            # WARN/URGENT 安全前缀
            if safety.get("level") in ("WARN", "URGENT") and safety.get("warning"):
                reply = f"请注意：{safety['warning']}\n\n{reply}"
        else:
            # 中文天数 → 阿拉伯数字
            try:
                days_num = int(trip_days)
            except (ValueError, TypeError):
                days_num = _parse_chinese_days(trip_days)

            if days_num <= 0 or days_num > 30:
                reply = f"天数{trip_days}不太合理，请告诉我1-30天之间的天数～"
                days_num = 0

            if days_num:
                # URGENT 场景：优先安全，暂不生成完整行程
                if safety.get("level") == "URGENT":
                    reply = f"{safety.get('warning', '')}\n\n当前不适宜生成完整行程计划，请先确保安全情况。"
                else:
                    # 提取出发地：从用户消息中匹配"从XX出发/去/到/飞"
                    departure = ""
                    dep_match = re.search(r'从([一-龥]{2,6})(?:出发|去|到|飞|坐|自驾)', user_message)
                    if dep_match:
                        departure = dep_match.group(1)
                    else:
                        # 兜底：尝试从AI提取的destination中解析（如"从武汉去上海"）
                        full_dest = extracted.get("destination", "")
                        dep_match2 = re.search(r'从([一-龥]{2,6})(?:出发|去|到|飞|坐|自驾)', full_dest)
                        if dep_match2:
                            departure = dep_match2.group(1)
                            # 清理destination中的出发地部分
                            destination = re.sub(r'从[一-龥]{2,6}(?:出发|去|到|飞|坐|自驾)', '', full_dest).strip()
                    logger.info("出发地提取: user_message=%.50s → departure=%s, destination=%s", user_message, departure, destination)
                    print(f"[DEBUG] 出发地提取: departure={departure}, destination={destination}")

                    try:
                        result = await generate_trip_plan(
                            device_id, destination, days_num,
                            style=trip_style or "default",
                            departure=departure,
                        )
                        reply = result["summary"]
                        extracted["_trip_plan"] = result.get("itinerary_json")
                        if safety.get("level") == "WARN" and safety.get("warning"):
                            reply = f"> {safety['warning']}\n\n{reply}"
                    except Exception as exc:
                        logger.warning("行程生成失败：%s", exc)
                        reply = f"生成{destination}行程时遇到了问题：{type(exc).__name__}。请稍后再试。"

    # 阶段五：WEATHER 意图 → 调用天气服务
    elif intent == "WEATHER":
        city = extracted.get("city", "")
        if not city:
            # 自动检测当前位置：偏好城市 → IP定位
            from app.services.memory_service import get_all_preferences as _gap
            for p in _gap(device_id):
                if p.get("category") == "location" and p.get("key") == "home_city":
                    city = p.get("value")
                    break
            if not city:
                import httpx as _httpx
                try:
                    resp = _httpx.get("http://ip-api.com/json/", timeout=3)
                    data = resp.json()
                    if data.get("status") == "success":
                        city = data.get("city")
                except Exception:
                    pass

        # 英文/拼音城市名 → 中文
        if city:
            from app.api.weather import _EN_TO_CN_CITY
            city = _EN_TO_CN_CITY.get(city, city)
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
        # 无关键词时从对话历史中补全（代词消解）
        if not keyword:
            history = await get_recent_history(device_id, session_id=session_id)
            from app.services.llm_client import call_llm as _llm
            resolve_prompt = "从以下对话历史中提取最近提到的景点或城市名称，只返回名称，没有则返回\"无\"。"
            hist_text = "\n".join(f"{m['role']}: {m['content']}" for m in history) if history else "（无历史）"
            resolved = await _llm(
                messages=[{"role": "user", "content": f"历史：{hist_text}\n当前：{user_message}"}],
                system_prompt=resolve_prompt,
                temperature=0.0,
                max_tokens=50,
            )
            keyword = resolved.strip() if resolved.strip() != "无" else ""
        if not keyword:
            reply = "请问你想了解哪个景点或城市的信息呢？"
        else:
            try:
                reply = await query_knowledge(user_message, spot_name=keyword or None)
            except Exception as exc:
                logger.warning("知识查询失败：%s", exc)
                reply = f"查询「{keyword}」时遇到了问题：{type(exc).__name__}。请稍后再试。"

    else:
        # ── CHAT 意图 ──

        # 检测纠正意图：用户指出信息错误 → 触发知识库纠正闭环
        if _CORRECTION_RE.search(user_message):
            try:
                from app.services.knowledge_expander import correct_knowledge
                correction_result = await correct_knowledge(user_message)
                if correction_result.get("status") == "ok":
                    spot = correction_result.get("spot_name", "")
                    reply = (
                        f"感谢你的纠正！已更新「{spot}」的知识记录：\n"
                        f"✅ {correction_result.get('corrected_fact', '')}\n"
                        f"之后的问答会基于更准确的信息来回答～"
                    )
                else:
                    # 纠正失败，正常走 LLM 回复
                    reply = None
            except Exception as exc:
                logger.warning("知识纠正失败：%s", exc)
                reply = None

            # 如果纠正失败或未触发，走正常 LLM 回复
            if reply is None:
                chat_prompt = (
                    "你是「AI智游伴」，友好专业的旅行助手。简洁温暖，1-3句话。"
                    "前面的消息是你们的对话历史，你必须基于历史回答。如果用户问是否记得某信息，先检查历史中有没有提到。"
                )
                history = await get_recent_history(device_id, session_id=session_id)
                messages = [{"role": m["role"], "content": m["content"]} for m in history]
                messages.append({"role": "user", "content": user_message})
                reply = await call_llm(
                    messages=messages,
                    system_prompt=chat_prompt,
                    temperature=0.7,
                    max_tokens=300,
                )
        else:
            # 正常 CHAT 回复
            chat_prompt = (
                "你是「AI智游伴」，友好专业的旅行助手。简洁温暖，1-3句话。"
                "前面的消息是你们的对话历史，你必须基于历史回答。如果用户问是否记得某信息，先检查历史中有没有提到。"
            )
            history = await get_recent_history(device_id, session_id=session_id)
            messages = [{"role": m["role"], "content": m["content"]} for m in history]
            messages.append({"role": "user", "content": user_message})
            reply = await call_llm(
                messages=messages,
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
