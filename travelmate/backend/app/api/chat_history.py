"""O19: 对话历史 API — 获取指定设备的所有对话记录。"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat-history", tags=["chat-history"])


@router.get("/list")
async def list_conversations(device_id: str, limit: int = 50, offset: int = 0):
    """获取设备的对话记录列表（按 session 分组）。"""
    db = get_db()

    # 获取所有有消息的会话
    rows = db.execute(
        """SELECT s.session_id, s.title, s.created_at,
                  (SELECT COUNT(*) FROM conversations c
                   WHERE c.device_id = s.device_id AND c.session_id = s.session_id
                   AND c.role != 'system') AS msg_count,
                  (SELECT c.content FROM conversations c
                   WHERE c.device_id = s.device_id AND c.session_id = s.session_id
                   AND c.role = 'user' ORDER BY c.id DESC LIMIT 1) AS last_msg,
                  (SELECT c.created_at FROM conversations c
                   WHERE c.device_id = s.device_id AND c.session_id = s.session_id
                   ORDER BY c.id DESC LIMIT 1) AS last_time
           FROM sessions s
           WHERE s.device_id = ?
           ORDER BY last_time DESC
           LIMIT ? OFFSET ?""",
        (device_id, limit, offset),
    ).fetchall()
    db.close()

    return {
        "conversations": [dict(r) for r in rows],
        "total": len(rows),
    }


@router.get("/{session_id}/messages")
async def get_conversation_messages(session_id: str, device_id: str, limit: int = 100):
    """获取某个会话的完整消息记录。"""
    db = get_db()
    rows = db.execute(
        """SELECT role, content, intent, metadata, created_at
           FROM conversations
           WHERE device_id = ? AND session_id = ? AND role != 'system'
           ORDER BY id ASC
           LIMIT ?""",
        (device_id, session_id, limit),
    ).fetchall()
    db.close()

    import json
    messages = []
    for r in rows:
        meta = None
        raw_meta = r["metadata"]
        if raw_meta:
            try:
                meta = json.loads(raw_meta)
            except Exception:
                pass
        messages.append({
            "role": r["role"],
            "content": r["content"],
            "intent": r["intent"],
            "metadata": meta,
            "created_at": r["created_at"],
        })

    return {"session_id": session_id, "messages": messages, "total": len(messages)}
