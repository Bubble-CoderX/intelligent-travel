from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.database import get_db

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    device_id: str = Field(..., description="设备 ID")
    title: str | None = Field(default=None, description="会话标题，为空时自动生成")


class RenameSessionRequest(BaseModel):
    title: str = Field(..., description="新标题")


def _generate_title(device_id: str, session_id: str) -> str:
    """从该会话的第一条用户消息截取标题（用于初始化时的占位）。"""
    conn = get_db()
    row = conn.execute(
        "SELECT content FROM conversations "
        "WHERE device_id = ? AND session_id = ? AND role = 'user' "
        "ORDER BY id ASC LIMIT 1",
        (device_id, session_id),
    ).fetchone()
    conn.close()
    if row and row["content"]:
        text = row["content"].strip()
        return text[:15] + ("..." if len(text) > 15 else "")
    return "新会话"


def update_session_title(device_id: str, session_id: str, title: str) -> None:
    """更新会话标题（供 chat 端点调用）。"""
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP "
        "WHERE session_id = ? AND device_id = ?",
        (title, session_id, device_id),
    )
    conn.commit()
    conn.close()


@router.get("")
async def list_sessions(device_id: str):
    """获取设备的所有会话列表。"""
    conn = get_db()
    rows = conn.execute(
        """SELECT s.session_id, s.title, s.created_at, s.updated_at,
                  (SELECT COUNT(*) FROM conversations c
                   WHERE c.device_id = s.device_id AND c.session_id = s.session_id
                   AND c.role != 'system') AS message_count,
                  (SELECT c.content FROM conversations c
                   WHERE c.device_id = s.device_id AND c.session_id = s.session_id
                   AND c.role = 'user'
                   ORDER BY c.id DESC LIMIT 1) AS last_message
           FROM sessions s
           WHERE s.device_id = ?
           ORDER BY s.updated_at DESC""",
        (device_id,),
    ).fetchall()
    conn.close()

    sessions = []
    for r in rows:
        sessions.append({
            "session_id": r["session_id"],
            "title": r["title"] or "新会话",
            "message_count": r["message_count"] or 0,
            "last_message": (r["last_message"] or "")[:50],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    return {"device_id": device_id, "sessions": sessions, "total": len(sessions)}


@router.post("")
async def create_session(req: CreateSessionRequest):
    """创建新会话。"""
    session_id = uuid.uuid4().hex[:12]
    title = req.title or "新会话"

    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (session_id, device_id, title) VALUES (?, ?, ?)",
        (session_id, req.device_id, title),
    )
    conn.commit()
    conn.close()

    return {"session_id": session_id, "title": title}


@router.delete("/{session_id}")
async def delete_session(session_id: str, device_id: str):
    """删除会话及其所有消息。"""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM sessions WHERE session_id = ? AND device_id = ?",
        (session_id, device_id),
    ).fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="会话不存在")

    conn.execute(
        "DELETE FROM conversations WHERE session_id = ? AND device_id = ?",
        (session_id, device_id),
    )
    conn.execute(
        "DELETE FROM sessions WHERE session_id = ? AND device_id = ?",
        (session_id, device_id),
    )
    conn.commit()
    conn.close()

    return {"status": "ok"}


@router.put("/{session_id}/rename")
async def rename_session(session_id: str, device_id: str, req: RenameSessionRequest):
    """重命名会话。"""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM sessions WHERE session_id = ? AND device_id = ?",
        (session_id, device_id),
    ).fetchone()

    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="会话不存在")

    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP "
        "WHERE session_id = ? AND device_id = ?",
        (req.title, session_id, device_id),
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "title": req.title}


@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str, device_id: str, limit: int = 100):
    """获取会话的消息历史（供前端切换会话时加载）。"""
    import json as _json

    conn = get_db()
    rows = conn.execute(
        "SELECT role, content, intent, metadata, created_at FROM conversations "
        "WHERE device_id = ? AND session_id = ? AND role != 'system' "
        "ORDER BY id DESC LIMIT ?",
        (device_id, session_id, limit),
    ).fetchall()
    conn.close()

    messages = []
    for r in reversed(rows):
        meta = None
        raw_meta = r["metadata"]
        if raw_meta:
            try:
                meta = _json.loads(raw_meta)
            except _json.JSONDecodeError:
                pass
        messages.append({
            "role": r["role"],
            "content": r["content"],
            "intent": r["intent"],
            "metadata": meta,
            "created_at": r["created_at"],
        })

    return {"session_id": session_id, "messages": messages, "total": len(messages)}
