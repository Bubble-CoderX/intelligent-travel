from __future__ import annotations

import logging
from typing import Optional

from app.models.database import get_db

logger = logging.getLogger(__name__)


def save_memory(
    device_id: str,
    category: str,
    key: str,
    value: str,
    source: str = "conversation",
) -> bool:
    """写入或更新用户偏好记忆。"""
    try:
        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM user_preferences WHERE device_id = ? AND category = ? AND key = ?",
            (device_id, category, key),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE user_preferences
                   SET value = ?, source = ?, updated_at = CURRENT_TIMESTAMP,
                       confidence = MIN(confidence + 0.1, 1.0)
                 WHERE device_id = ? AND category = ? AND key = ?""",
                (value, source, device_id, category, key),
            )
        else:
            conn.execute(
                """INSERT INTO user_preferences
                   (device_id, category, key, value, source)
                 VALUES (?, ?, ?, ?, ?)""",
                (device_id, category, key, value, source),
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception("save_memory 失败")
        return False


def get_all_preferences(device_id: str) -> list[dict]:
    """获取用户所有偏好。"""
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT category, key, value, confidence, source, updated_at
               FROM user_preferences
               WHERE device_id = ?
               ORDER BY updated_at DESC""",
            (device_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        logger.exception("get_all_preferences 失败")
        return []


def query_memory(device_id: str, query_text: str, top_k: int = 5) -> list[dict]:
    """根据查询文本检索相关偏好（SQLite LIKE 语义匹配）。"""
    try:
        conn = get_db()
        rows = conn.execute(
            """SELECT category, key, value, confidence
               FROM user_preferences
               WHERE device_id = ?
                 AND (key LIKE ? OR value LIKE ? OR category LIKE ?)
               ORDER BY confidence DESC, updated_at DESC
               LIMIT ?""",
            (device_id, f"%{query_text}%", f"%{query_text}%", f"%{query_text}%", top_k),
        ).fetchall()
        conn.close()
        if rows:
            return [dict(r) for r in rows]
        return _fuzzy_query(conn, device_id, query_text, top_k)
    except Exception:
        logger.exception("query_memory 失败")
        return []


def _fuzzy_query(
    conn, device_id: str, query_text: str, top_k: int
) -> list[dict]:
    """当精确 LIKE 无结果时，按词拆分做 OR 模糊匹配。"""
    keywords = [w.strip() for w in query_text if len(w.strip()) >= 2]
    if not keywords:
        return []
    conditions = " OR ".join(
        ["key LIKE ?"] * len(keywords)
        + ["value LIKE ?"] * len(keywords)
    )
    params = (
        [device_id]
        + [f"%{k}%" for k in keywords]
        + [f"%{k}%" for k in keywords]
        + [top_k],
    )
    sql = f"""
        SELECT category, key, value, confidence
        FROM user_preferences
        WHERE device_id = ? AND ({conditions})
        ORDER BY confidence DESC, updated_at DESC
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def update_memory(
    device_id: str,
    category: str,
    key: str,
    new_value: str,
) -> bool:
    """更新已有偏好。"""
    try:
        conn = get_db()
        conn.execute(
            """UPDATE user_preferences
               SET value = ?, updated_at = CURRENT_TIMESTAMP,
                   confidence = MIN(confidence + 0.1, 1.0)
             WHERE device_id = ? AND category = ? AND key = ?""",
            (new_value, device_id, category, key),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception("update_memory 失败")
        return False


def forget_memory(
    device_id: str,
    category: Optional[str] = None,
    key: Optional[str] = None,
) -> bool:
    """删除用户记忆。支持按 category 或 category+key 精确删除。"""
    try:
        conn = get_db()
        if category and key:
            conn.execute(
                "DELETE FROM user_preferences WHERE device_id = ? AND category = ? AND key = ?",
                (device_id, category, key),
            )
        elif category:
            conn.execute(
                "DELETE FROM user_preferences WHERE device_id = ? AND category = ?",
                (device_id, category),
            )
        else:
            conn.execute(
                "DELETE FROM user_preferences WHERE device_id = ?",
                (device_id,),
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception("forget_memory 失败")
        return False
