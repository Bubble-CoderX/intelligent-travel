from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import chromadb
from app.models.database import get_db

logger = logging.getLogger(__name__)

# ── ChromaDB 初始化 ──────────────────────────────────────────
_chroma_dir = Path(__file__).resolve().parent.parent.parent / "db" / "chroma_memory"
_chroma_dir.mkdir(parents=True, exist_ok=True)

_chroma_client = chromadb.PersistentClient(path=str(_chroma_dir))
_memory_collection = _chroma_client.get_or_create_collection(
    name="user_preferences",
    metadata={"hnsw:space": "cosine"},
)


def save_memory(
    device_id: str,
    category: str,
    key: str,
    value: str,
    source: str = "conversation",
) -> bool:
    """写入或更新用户偏好记忆（双写：SQLite + ChromaDB）。"""
    try:
        # 1. SQLite 写入
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

        # 2. ChromaDB 向量化写入
        doc_text = f"用户偏好：{category}-{key}：{value}"
        doc_id = f"{device_id}_{category}_{key}"
        _memory_collection.upsert(
            ids=[doc_id],
            documents=[doc_text],
            metadatas=[{
                "device_id": device_id,
                "category": category,
                "key": key,
                "value": value,
            }],
        )
        return True
    except Exception:
        logger.exception("save_memory 失败")
        return False


def get_all_preferences(device_id: str) -> list[dict]:
    """获取用户所有偏好（从 SQLite 结构化查询）。"""
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
    """语义检索用户偏好（ChromaDB 向量相似度搜索）。"""
    try:
        results = _memory_collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where={"device_id": device_id},
        )
        memories = []
        if results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                memories.append({
                    "category": meta.get("category", ""),
                    "key": meta.get("key", ""),
                    "value": meta.get("value", ""),
                    "text": doc,
                })
        return memories
    except Exception:
        logger.exception("query_memory ChromaDB 检索失败，回退到 SQLite")
        return _fallback_query(device_id, query_text, top_k)


def _fallback_query(device_id: str, query_text: str, top_k: int) -> list[dict]:
    """ChromaDB 不可用时回退到 SQLite LIKE 查询。"""
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
        return [dict(r) for r in rows]
    except Exception:
        return []


def forget_memory(
    device_id: str,
    category: Optional[str] = None,
    key: Optional[str] = None,
) -> bool:
    """删除用户记忆（SQLite + ChromaDB 双删）。"""
    try:
        # 1. SQLite 删除
        conn = get_db()
        if category and key:
            conn.execute(
                "DELETE FROM user_preferences WHERE device_id = ? AND category = ? AND key = ?",
                (device_id, category, key),
            )
            _memory_collection.delete(ids=[f"{device_id}_{category}_{key}"])
        elif category:
            conn.execute(
                "DELETE FROM user_preferences WHERE device_id = ? AND category = ?",
                (device_id, category),
            )
            # 批量删除 ChromaDB 中该 category 下的所有 doc
            existing = conn.execute(
                "SELECT key FROM user_preferences WHERE device_id = ? AND category = ?",
                (device_id, category),
            ).fetchall()
        else:
            conn.execute(
                "DELETE FROM user_preferences WHERE device_id = ?",
                (device_id,),
            )
            # 批量删除 ChromaDB 中该 device 的所有 doc
            _memory_collection.delete(
                where={"device_id": device_id}
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception("forget_memory 失败")
        return False
