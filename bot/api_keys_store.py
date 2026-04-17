"""
bot/api_keys_store.py
~~~~~~~~~~~~~~~~~~~~~
Persistent storage for Google API keys managed via the admin panel.
Keys are saved to DB (PostgreSQL) or data/api_keys.json as fallback.
Each entry is a dict: {"key": "AIza...", "project_id": "my-project-123" | None}
On first startup env-var keys are migrated into the store automatically.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import bot.db as _db

logger = logging.getLogger(__name__)

_STORE_PATH = Path(os.environ.get("API_KEYS_FILE", str(Path(__file__).resolve().parent.parent / "data" / "api_keys.json")))


def _normalize(entry) -> dict:
    if isinstance(entry, str):
        return {"key": entry, "project_id": None}
    if isinstance(entry, dict):
        return {"key": entry.get("key", ""), "project_id": entry.get("project_id") or None}
    return {"key": str(entry), "project_id": None}


def _load() -> list[dict]:
    if _db.is_available():
        rows = _db.load_api_keys()
        return [_normalize(r) for r in rows]
    try:
        if _STORE_PATH.exists():
            data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [_normalize(e) for e in data if (isinstance(e, str) and e.strip()) or (isinstance(e, dict) and e.get("key", "").strip())]
    except Exception as e:
        logger.warning("api_keys_store: failed to load: %s", e)
    return []


def _save(entries: list[dict]) -> None:
    if _db.is_available():
        _db.save_api_keys(entries)
        return
    try:
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STORE_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("api_keys_store: failed to save: %s", e)


def migrate_env_keys() -> None:
    if _db.is_available():
        if _db.api_keys_table_has_rows():
            return
    elif _STORE_PATH.exists():
        return

    env_keys: list[dict] = []
    seen: set[str] = set()
    for var in ("GOOGLE_CLOUD_API_KEY", "GOOGLE_CLOUD_API_KEY_1",
                "GOOGLE_CLOUD_API_KEY_2", "GOOGLE_CLOUD_API_KEY_3"):
        val = os.environ.get(var, "").strip()
        if val and val not in seen:
            seen.add(val)
            env_keys.append({"key": val, "project_id": None})

    if not env_keys:
        return

    _save(env_keys)
    logger.info("api_keys_store: first-time setup, migrated %d env key(s) into store", len(env_keys))


def get_all_keys() -> list[dict]:
    return _load()


def get_all_keys_plain() -> list[str]:
    return [e["key"] for e in _load()]


def add_key(key: str, project_id: str | None = None) -> bool:
    key = key.strip()
    if not key:
        return False
    entries = _load()
    if any(e["key"] == key for e in entries):
        return False
    entries.append({"key": key, "project_id": project_id.strip() if project_id else None})
    _save(entries)
    return True


def update_key(index: int, new_key: str | None = None, new_project_id: str | None = ...) -> bool:
    entries = _load()
    if index < 0 or index >= len(entries):
        return False
    if new_key is not None:
        nk = new_key.strip()
        if not nk:
            return False
        if any(i != index and e["key"] == nk for i, e in enumerate(entries)):
            return False
        entries[index]["key"] = nk
    if new_project_id is not ...:
        entries[index]["project_id"] = new_project_id.strip() if new_project_id else None
    _save(entries)
    return True


def remove_key(index: int) -> str | None:
    entries = _load()
    if index < 0 or index >= len(entries):
        return None
    removed = entries.pop(index)
    _save(entries)
    return removed["key"]


def mask_key(key: str) -> str:
    if len(key) <= 12:
        return key[:4] + "..." + key[-2:]
    return key[:8] + "..." + key[-4:]
