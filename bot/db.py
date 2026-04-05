"""
bot/db.py
~~~~~~~~~
Optional PostgreSQL persistence layer.

If DATABASE_URL env-var is set, all user settings and API keys
are stored in PostgreSQL. Otherwise the module is a no-op and
the file-based fallback is used.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DATABASE_URL: str | None = os.environ.get("DATABASE_URL", "").strip() or None
_conn = None


def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        import psycopg2
        _conn = psycopg2.connect(_DATABASE_URL)
        _conn.autocommit = True
    return _conn


def is_available() -> bool:
    return bool(_DATABASE_URL)


def init_tables() -> None:
    if not _DATABASE_URL:
        return
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_user_settings (
                    user_id BIGINT PRIMARY KEY,
                    data    TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_api_keys (
                    id  SERIAL PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL
                )
            """)
        logger.info("db: tables ready (PostgreSQL)")
    except Exception:
        logger.exception("db: failed to init tables")


# ── User settings ──────────────────────────────────────────────────────────────

def load_all_users() -> dict[int, dict[str, Any]]:
    """Return {user_id: settings_dict} for all rows."""
    if not _DATABASE_URL:
        return {}
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, data FROM bot_user_settings")
            rows = cur.fetchall()
        result = {}
        for uid, raw in rows:
            try:
                result[int(uid)] = json.loads(raw)
            except Exception:
                pass
        logger.info("db: loaded %d users from PostgreSQL", len(result))
        return result
    except Exception:
        logger.exception("db: failed to load users")
        return {}


def save_all_users(snapshot: dict[int, dict[str, Any]]) -> None:
    """Upsert all users in one transaction."""
    if not _DATABASE_URL:
        return
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            for uid, data in snapshot.items():
                cur.execute("""
                    INSERT INTO bot_user_settings (user_id, data)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET data = EXCLUDED.data
                """, (uid, json.dumps(data, ensure_ascii=False)))
        logger.info("db: saved %d users to PostgreSQL", len(snapshot))
    except Exception:
        logger.exception("db: failed to save users")


# ── API keys ───────────────────────────────────────────────────────────────────

def load_api_keys() -> list[str]:
    if not _DATABASE_URL:
        return []
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT key FROM bot_api_keys ORDER BY id")
            return [row[0] for row in cur.fetchall()]
    except Exception:
        logger.exception("db: failed to load api keys")
        return []


def save_api_keys(keys: list[str]) -> None:
    if not _DATABASE_URL:
        return
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bot_api_keys")
            for key in keys:
                cur.execute(
                    "INSERT INTO bot_api_keys (key) VALUES (%s) ON CONFLICT DO NOTHING",
                    (key,)
                )
        logger.info("db: saved %d api keys to PostgreSQL", len(keys))
    except Exception:
        logger.exception("db: failed to save api keys")


def api_keys_table_has_rows() -> bool:
    """Check if any API keys exist in DB (used for migration guard)."""
    if not _DATABASE_URL:
        return False
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM bot_api_keys LIMIT 1")
            return cur.fetchone() is not None
    except Exception:
        return False
