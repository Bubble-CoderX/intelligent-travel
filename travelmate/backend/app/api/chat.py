import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.context_service import save_message
from app.services.intent_router import route_intent
from app.utils.safety import check_rate_limit

from app.api.sessions import _generate_title, update_session_title

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 请求频率限制：每设备每分钟最多 30 次
    if not check_rate_limit(req.device_id):
        return ChatResponse(
            reply="请求太频繁了，请稍后再试～",
            intent="rate_limited",
            message_type="text",
        )

    session_id = req.session_id or "default"

    # F10: 情绪感知拦截——在意图识别前检测情绪
    try:
        from app.services.mood_companion_service import intercept_mood_in_chat
        mood_result = await intercept_mood_in_chat(req.message, req.device_id)
        if mood_result:
            save_message(req.device_id, session_id, "user", req.message, "MOOD")
            save_message(req.device_id, session_id, "assistant", mood_result["mood_response"], "MOOD")
            return ChatResponse(
                reply=mood_result["mood_response"],
                intent="CHAT",
                message_type="text",
                metadata={
                    "mood_type": mood_result["mood_type"],
                    "mood_label": mood_result["mood_label"],
                    "mood_confidence": mood_result["confidence"],
                },
            )
    except Exception:
        logger.debug("情绪检测失败，继续正常流程", exc_info=True)

    try:
        result = await route_intent(req.message, req.device_id, session_id=session_id, trip_style=req.trip_style)
    except Exception as exc:
        logger.exception("意图识别管道异常")
        return ChatResponse(
            reply=f"处理消息时出现错误：{type(exc).__name__}。请检查后端日志。",
            intent="error",
            message_type="text",
        )

    if result.get("intent") == "blocked":
        save_message(req.device_id, session_id, "user", req.message, "blocked")
        save_message(req.device_id, session_id, "assistant", result.get("reply", ""), "blocked")
        return ChatResponse(
            reply=result.get("reply", "抱歉，无法处理该请求。"),
            intent="blocked",
            message_type="text",
        )

    intent = result.get("intent", "CHAT")
    reply = result.get("reply", "")

    # 根据意图类型决定消息展示形式
    if intent == "TRIP_PLAN":
        message_type = "card"
    elif intent == "WEATHER":
        message_type = "weather"
    elif intent == "KNOWLEDGE":
        message_type = "knowledge"
    else:
        message_type = "text"

    metadata = {
        "layer": result.get("layer"),
        "sub_intent": result.get("sub_intent"),
        "confidence": result.get("confidence"),
        "safety": result.get("safety"),
    }

    # 安全提醒：WARN/URGENT 级别附加警告信息
    safety = result.get("safety", {})
    if safety.get("level") in ("WARN", "URGENT") and safety.get("warning"):
        metadata["safety_warning"] = safety["warning"]

    # 行程规划：传递结构化数据给前端 TripCard
    if intent == "TRIP_PLAN":
        extracted = result.get("extracted_data", {})
        trip_plan = extracted.get("_trip_plan")
        if trip_plan:
            metadata["trip_plan"] = trip_plan
            metadata["destination"] = trip_plan.get("destination", "")
            metadata["days"] = len(trip_plan.get("days", []))
        else:
            metadata["destination"] = extracted.get("destination", "")
            metadata["days"] = extracted.get("days", 0)
        metadata["trip_style"] = req.trip_style or "default"

    save_message(req.device_id, session_id, "user", req.message, intent)
    save_message(req.device_id, session_id, "assistant", reply, intent, metadata=metadata)

    # ── 会话自动命名 ──────────────────────────────────────
    from app.models.database import get_db as _get_db
    _conn = _get_db()
    _session = _conn.execute(
        "SELECT title FROM sessions WHERE session_id = ? AND device_id = ?",
        (session_id, req.device_id),
    ).fetchone()
    _conn.close()

    if _session:
        current_title = _session["title"] or ""
        # 行程规划生成了结构化方案 → 以目的地命名
        if intent == "TRIP_PLAN" and metadata.get("trip_plan"):
            dest = metadata.get("destination", "")
            days = metadata.get("days", 0)
            if dest:
                new_title = f"{dest}·{days}日游" if days else dest
                if new_title != current_title:
                    update_session_title(req.device_id, session_id, new_title)
        # 首条消息且仍是默认标题 → 用消息内容命名
        elif current_title in ("新会话", ""):
            new_title = _generate_title(req.device_id, session_id)
            if new_title != "新会话":
                update_session_title(req.device_id, session_id, new_title)

    return ChatResponse(
        reply=reply,
        intent=intent,
        message_type=message_type,
        metadata=metadata,
    )


# ── O9: 流式输出 SSE 端点 ────────────────────────────────

@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """流式对话：CHAT/WEATHER/KNOWLEDGE 逐字输出，TRIP_PLAN 整体返回。"""
    if not check_rate_limit(req.device_id):
        async def rate_limit_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': '请求太频繁了，请稍后再试～'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(rate_limit_gen(), media_type="text/event-stream")

    session_id = req.session_id or "default"

    # 意图识别（非流式，快速判断意图类型）
    try:
        result = await route_intent(req.message, req.device_id, session_id=session_id, trip_style=req.trip_style)
    except Exception as exc:
        logger.exception("意图识别异常")
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'content': f'处理消息时出现错误：{type(exc).__name__}'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    intent = result.get("intent", "CHAT")
    reply = result.get("reply", "")

    # TRIP_PLAN 等结构化意图：整体返回（不适合流式）
    if intent in ("TRIP_PLAN", "blocked"):
        # 构建 metadata
        metadata = {}
        if intent == "TRIP_PLAN":
            extracted = result.get("extracted_data", {})
            trip_plan = extracted.get("_trip_plan")
            if trip_plan:
                metadata["trip_plan"] = trip_plan
                metadata["destination"] = trip_plan.get("destination", "")
                metadata["days"] = len(trip_plan.get("days", []))
            else:
                metadata["destination"] = extracted.get("destination", "")
                metadata["days"] = extracted.get("days", 0)
            metadata["trip_style"] = req.trip_style or "default"

        save_message(req.device_id, session_id, "user", req.message, intent)
        save_message(req.device_id, session_id, "assistant", reply, intent, metadata=metadata if metadata else None)

        # 会话自动命名
        from app.api.sessions import _generate_title, update_session_title
        from app.models.database import get_db as _get_db
        _conn = _get_db()
        _session = _conn.execute(
            "SELECT title FROM sessions WHERE session_id = ? AND device_id = ?",
            (session_id, req.device_id),
        ).fetchone()
        _conn.close()
        if _session:
            current_title = _session["title"] or ""
            if intent == "TRIP_PLAN" and metadata.get("trip_plan"):
                dest = metadata.get("destination", "")
                days = metadata.get("days", 0)
                if dest:
                    new_title = f"{dest}·{days}日游" if days else dest
                    if new_title != current_title:
                        update_session_title(req.device_id, session_id, new_title)
            elif current_title in ("新会话", ""):
                new_title = _generate_title(req.device_id, session_id)
                if new_title and new_title != "新会话":
                    update_session_title(req.device_id, session_id, new_title)

        async def full_gen():
            yield f"data: {json.dumps({'type': 'full', 'content': reply, 'intent': intent, 'metadata': metadata}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(full_gen(), media_type="text/event-stream")

    # CHAT/WEATHER/KNOWLEDGE：流式输出
    async def stream_gen():
        from app.services.llm_client import call_llm_stream
        from app.services.context_service import get_recent_history

        # 构建对话历史
        chat_prompt = (
            "你是「AI智游伴」，友好专业的旅行助手。回答要详细有料，3-5句话左右。"
            "如果用户问景点，要包含历史背景、文化特色、游玩亮点和实用建议。"
            "前面的消息是你们的对话历史，你必须基于历史回答。"
        )
        history = await get_recent_history(req.device_id, session_id=session_id)
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": req.message})

        full_reply = ""
        try:
            async for chunk in call_llm_stream(
                messages=messages,
                system_prompt=chat_prompt,
                temperature=0.7,
                max_tokens=500,
            ):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.warning("流式输出异常: %s", exc)
            if not full_reply:
                full_reply = reply  # 降级到非流式回复
                yield f"data: {json.dumps({'type': 'chunk', 'content': full_reply}, ensure_ascii=False)}\n\n"

        # 保存消息
        save_message(req.device_id, session_id, "user", req.message, intent)
        save_message(req.device_id, session_id, "assistant", full_reply, intent)

        # 会话自动命名（流式路径也需执行）
        from app.api.sessions import _generate_title, update_session_title
        from app.models.database import get_db as _get_db
        _conn = _get_db()
        _session = _conn.execute(
            "SELECT title FROM sessions WHERE session_id = ? AND device_id = ?",
            (session_id, req.device_id),
        ).fetchone()
        _conn.close()
        if _session:
            current_title = _session["title"] or ""
            if current_title in ("新会话", ""):
                new_title = _generate_title(req.device_id, session_id)
                if new_title and new_title != "新会话":
                    update_session_title(req.device_id, session_id, new_title)

        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")


# ── O8: 图片/文件上传分析 ──────────────────────────────

import base64
from pydantic import BaseModel, Field


class ImageAnalyzeRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    session_id: str = Field(default="", description="会话 ID")
    image_base64: str = Field(..., description="图片 Base64 编码")
    question: str = Field(default="请分析这张图片", description="用户对图片的问题")
    filename: str = Field(default="", description="文件名")


@router.post("/chat/image")
async def analyze_image(req: ImageAnalyzeRequest):
    """O8: 分析上传的图片（千问VL识别 + 自动调研知识库）。"""
    session_id = req.session_id or "default"

    # 1. 保存图片到磁盘
    image_url = ""
    try:
        import uuid
        from pathlib import Path
        ext = req.filename.split(".")[-1] if "." in req.filename else "jpg"
        img_name = f"{uuid.uuid4().hex[:12]}.{ext}"
        img_path = Path(__file__).resolve().parent.parent.parent / "data" / "uploads" / img_name
        img_data = base64.b64decode(req.image_base64)
        img_path.write_bytes(img_data)
        image_url = f"/uploads/{img_name}"
    except Exception as exc:
        logger.warning("图片保存失败: %s", exc)

    # 2. 用千问 VL 识别图片内容
    try:
        from app.services.qwen_vl_client import analyze_image as qwen_analyze
        identification = await qwen_analyze(
            req.image_base64,
            "请仔细观察这张图片，按以下步骤详细分析：\n"
            "1. 描述你看到的主要建筑物/地标/场景的外观特征（形状、颜色、高度、文字、周围环境等）\n"
            "2. 根据外观特征判断这是什么景点或场所\n"
            "3. 给出景点名称和所在城市\n"
            "4. 详细介绍这个景点（4-5句话）：包括历史背景、文化意义、建筑特色、游玩亮点、适合什么人群、最佳游览时间等\n\n"
            "输出格式：\n"
            "识别结果：[景点名称]，城市：[城市名]\n"
            "特征描述：[你看到的外观特征]\n"
            "详细介绍：[4-5句话的景点介绍]\n"
            "推荐理由：[为什么值得去]"
        )
    except Exception as exc:
        logger.warning("千问VL识别失败: %s", exc)
        identification = f"图片识别暂时不可用（{type(exc).__name__}）。请描述图片内容，我来帮你分析。"

    # 2. 解析识别结果，提取景点名和城市
    spot_name = ""
    city = ""
    for line in identification.split("\n"):
        line = line.strip()
        # 匹配 "识别结果：XXX" 或 "景点：XXX"
        import re
        result_match = re.search(r'识别结果[：:]\s*(.+?)[，,。\s]', line)
        spot_match = re.search(r'景点[：:]\s*(.+?)[，,。\s]', line)
        city_match = re.search(r'城市[：:]\s*(.+?)[，,。\s]', line)
        if result_match:
            spot_name = result_match.group(1).strip()
        elif spot_match:
            spot_name = spot_match.group(1).strip()
        if city_match:
            city = city_match.group(1).strip()

    # 3. 如果识别出景点，自动调研知识库
    knowledge_msg = ""
    if spot_name:
        try:
            from app.services.knowledge_expander import auto_expand, has_local_knowledge
            if not has_local_knowledge(spot_name):
                # 判断分类：检查cities目录下是否已有同名文件
                from pathlib import Path
                cities_dir = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge" / "cities"
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', spot_name)
                if cities_dir.exists() and (cities_dir / f"{safe_name}.md").exists():
                    category = "cities"
                else:
                    category = "spots"
                result = await auto_expand(spot_name, category=category)
                if result.get("status") == "ok":
                    knowledge_msg = f"\n\n📚 已自动调研「{spot_name}」的知识信息并保存到知识库。"
        except Exception as exc:
            logger.warning("自动调研失败: %s", exc)

    reply = identification + knowledge_msg

    # 4. 保存消息（含 image_url）
    metadata = {"image_url": image_url} if image_url else None
    save_message(req.device_id, session_id, "user", "", "IMAGE", metadata=metadata)
    save_message(req.device_id, session_id, "assistant", reply, "IMAGE")

    return {"reply": reply, "intent": "IMAGE", "image_url": image_url}
