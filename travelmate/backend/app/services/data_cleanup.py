"""O29: 数据清理机制 — 定期清理过期数据。"""
from __future__ import annotations

import logging

from app.models.database import get_db

logger = logging.getLogger(__name__)


def cleanup_old_data() -> dict:
    """清理过期数据。返回清理统计。"""
    db = get_db()
    stats = {}

    # 1. 保留最近200条行程记录，删除更早的
    result = db.execute(
        """DELETE FROM trip_plans WHERE id NOT IN (
            SELECT id FROM trip_plans ORDER BY created_at DESC LIMIT 200
        )"""
    )
    stats["trip_plans_deleted"] = result.rowcount

    # 2. 删除60天前的天气记录
    result = db.execute(
        "DELETE FROM weather_records WHERE fetched_at < datetime('now', '-60 days')"
    )
    stats["weather_deleted"] = result.rowcount

    # 3. 删除90天前的对话历史
    result = db.execute(
        "DELETE FROM conversations WHERE created_at < datetime('now', '-90 days')"
    )
    stats["conversations_deleted"] = result.rowcount

    db.commit()
    db.close()

    logger.info("数据清理完成: %s", stats)
    return stats
