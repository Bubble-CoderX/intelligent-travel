import sqlite3
from pathlib import Path

from app.core.config import BACKEND_DIR

DB_DIR = BACKEND_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "travelmate.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            intent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            category TEXT,
            key TEXT,
            value TEXT,
            confidence REAL DEFAULT 1.0,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS trip_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            destination TEXT,
            days INTEGER,
            plan_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            device_id TEXT,
            title TEXT,
            greeted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_session
            ON conversations(device_id, session_id);
    """)
    conn.commit()

    # 增量迁移：conversations 表补 metadata 列（已存在则忽略）
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN metadata TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 列已存在

    # F1：天气数据持久化表
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS weather_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            weather TEXT,
            temperature INTEGER,
            humidity TEXT,
            wind_direction TEXT,
            wind_power TEXT,
            forecast_json TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_weather_city_time
            ON weather_records(city, fetched_at DESC);
    """)
    conn.commit()
    conn.close()

    # O16: 行程历史记录表
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trip_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            session_id TEXT,
            title TEXT NOT NULL DEFAULT '',
            destination TEXT NOT NULL DEFAULT '',
            departure_city TEXT DEFAULT '',
            days INTEGER DEFAULT 0,
            group_size INTEGER DEFAULT 2,
            composition TEXT DEFAULT '',
            budget_total REAL DEFAULT 0,
            itinerary_json TEXT,
            status TEXT DEFAULT 'planned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_trip_history_device "
        "ON trip_history(device_id, created_at DESC)"
    )
    conn.commit()
    conn.close()
