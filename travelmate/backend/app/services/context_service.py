from __future__ import annotations

import asyncio
import logging

from app.models.database import get_db

logger = logging.getLogger(__name__)

MAX_HISTORY = 50
RECENT_LIMIT = 20
SUMMARY_THRESHOLD = 30

# 摘要缓存：device_id → (message_count, summary_text)
_summary_cache: dict[str, tuple[int, str]] = {}


def save_message(device_id: str, session_id: str, role: str, content: str, intent: str = "") -> None:
    """保存单条消息到对话历史。"""
    conn = get_db()
    conn.execute(
        "INSERT INTO conversations (device_id, session_id, role, content, intent) VALUES (?, ?, ?, ?, ?)",
        (device_id, session_id, role, content, intent),
    )
    conn.commit()
    conn.close()


async def get_recent_history(device_id: str, limit: int = MAX_HISTORY) -> list[dict[str, str]]:
    """
    获取设备对话历史。
    - 消息数 ≤ SUMMARY_THRESHOLD：返回全部（最多 limit 条）
    - 消息数 > SUMMARY_THRESHOLD：旧消息摘要 + 最近 RECENT_LIMIT 条原文
    """
    conn = get_db()
    total = conn.execute(
        "SELECT COUNT(*) FROM conversations WHERE device_id = ? AND role != 'system'",
        (device_id,),
    ).fetchone()[0]

    # 消息不多，直接返回
    if total <= SUMMARY_THRESHOLD:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE device_id = ? "
            "AND role != 'system' ORDER BY id DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
        conn.close()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    # 取最近 RECENT_LIMIT 条原文
    recent_rows = conn.execute(
        "SELECT role, content FROM conversations WHERE device_id = ? "
        "AND role != 'system' ORDER BY id DESC LIMIT ?",
        (device_id, RECENT_LIMIT),
    ).fetchall()
    recent = [{"role": row["role"], "content": row["content"]} for row in reversed(recent_rows)]

    # 检查缓存：消息数变化 < 5 条时复用旧摘要
    cached_count, cached_summary = _summary_cache.get(device_id, (0, ""))
    if abs(total - cached_count) < 5 and cached_summary:
        summary_text = cached_summary
    else:
        # 取旧消息用于摘要
        older_rows = conn.execute(
            "SELECT role, content FROM conversations WHERE device_id = ? "
            "AND role != 'system' ORDER BY id ASC LIMIT ?",
            (device_id, total - RECENT_LIMIT),
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
            _summary_cache[device_id] = (total, summary_text.strip())
        except Exception as exc:
            logger.warning("摘要生成失败：%s", exc)
            summary_text = "（历史摘要生成失败）"

    conn = get_db()
    conn.close()

    return [{"role": "system", "content": f"[历史摘要] {summary_text.strip()}"}] + recent
