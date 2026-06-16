from __future__ import annotations

import asyncio
import json as _json
import logging

from app.models.database import get_db

logger = logging.getLogger(__name__)

MAX_HISTORY = 50
RECENT_LIMIT = 20
SUMMARY_THRESHOLD = 30

# 摘要缓存：device_id → (message_count, summary_text)
_summary_cache: dict[str, tuple[int, str]] = {}


def save_message(device_id: str, session_id: str, role: str, content: str, intent: str = "", metadata: dict | None = None) -> None:
    """保存单条消息到对话历史。时间使用 UTC+8 本地时间。"""
    from datetime import datetime, timezone, timedelta
    meta_json = _json.dumps(metadata, ensure_ascii=False) if metadata else None
    local_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (device_id, session_id, role, content, intent, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (device_id, session_id, role, content, intent, meta_json, local_time),
    )
    conn.commit()
    conn.close()


def _format_history_row(row) -> dict[str, str]:
    """格式化对话历史行，主动服务消息加标记前缀。"""
    role = row["role"]
    content = row["content"]
    meta_raw = row["metadata"]
    if meta_raw and role == "assistant":
        try:
            meta = _json.loads(meta_raw)
            if meta.get("proactive_type"):
                content = f"[AI主动消息，请仅作为对话上下文参考，不要复述此标记] {content}"
        except (ValueError, _json.JSONDecodeError):
            pass
    return {"role": role, "content": content}


async def get_recent_history(
    device_id: str,
    session_id: str | None = None,
    limit: int = MAX_HISTORY,
) -> list[dict[str, str]]:
    """
    获取设备对话历史（按 session_id 隔离）。
    - 消息数 ≤ SUMMARY_THRESHOLD：返回全部（最多 limit 条）
    - 消息数 > SUMMARY_THRESHOLD：旧消息摘要 + 最近 RECENT_LIMIT 条原文
    - 主动服务消息保留但加标记，让 LLM 理解上下文但不复述
    """
    conn = get_db()

    if session_id:
        where = "device_id = ? AND session_id = ? AND role != 'system'"
        params_count: tuple = (device_id, session_id)
        params_list: tuple = (device_id, session_id, limit)
    else:
        where = "device_id = ? AND role != 'system'"
        params_count = (device_id,)
        params_list = (device_id, limit)

    total = conn.execute(
        f"SELECT COUNT(*) FROM conversations WHERE {where}", params_count
    ).fetchone()[0]

    # 消息不多，直接返回
    if total <= SUMMARY_THRESHOLD:
        rows = conn.execute(
            f"SELECT role, content, metadata FROM conversations WHERE {where} "
            "ORDER BY id DESC LIMIT ?",
            params_list,
        ).fetchall()
        conn.close()
        return [_format_history_row(row) for row in reversed(rows)]

    # 取最近 RECENT_LIMIT 条原文
    recent_params = params_list[:2] + (RECENT_LIMIT,) if session_id else (device_id, RECENT_LIMIT)
    recent_rows = conn.execute(
        f"SELECT role, content, metadata FROM conversations WHERE {where} "
        "ORDER BY id DESC LIMIT ?",
        recent_params,
    ).fetchall()
    recent = [_format_history_row(row) for row in reversed(recent_rows)]

    # 缓存 key 包含 session_id 以隔离不同会话
    cache_key = f"{device_id}:{session_id}" if session_id else device_id
    cached_count, cached_summary = _summary_cache.get(cache_key, (0, ""))
    if abs(total - cached_count) < 5 and cached_summary:
        summary_text = cached_summary
    else:
        # 取旧消息用于摘要
        older_params = params_count + (total - RECENT_LIMIT,)
        older_rows = conn.execute(
            f"SELECT role, content, metadata FROM conversations WHERE {where} "
            "ORDER BY id ASC LIMIT ?",
            older_params,
        ).fetchall()
        conn.close()

        older_text = "\n".join(
            f"{'用户' if row['role'] == 'user' else '助手'}：{row['content'][:150]}"
            for row in older_rows
        )

        try:
            from app.services.llm_client import call_llm
            summary_text = await call_llm(
                messages=[{
                    "role": "user",
                    "content": (
                        "请用 2-3 句话概括以下对话的关键信息，"
                        "重点提取：用户偏好、旅行计划、个人信息、去过的地方。\n\n"
                        f"{older_text}"
                    ),
                }],
                system_prompt="你是对话摘要助手，只输出摘要，不要多余内容。",
                temperature=0.0,
                max_tokens=200,
            )
            _summary_cache[cache_key] = (total, summary_text.strip())
        except Exception as exc:
            logger.warning("摘要生成失败：%s", exc)
            summary_text = "（历史摘要生成失败）"

    conn = get_db()
    conn.close()

    return [{"role": "system", "content": f"[历史摘要] {summary_text.strip()}"}] + recent
