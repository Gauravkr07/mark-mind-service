"""Temporary YAML-file storage, standing in for the Postgres/SQLAlchemy layer
(see app/database.py, app/models.py — commented out for now).

Each entity lives in its own .yml file under DATA_DIR. Not safe for concurrent
writers; fine for the current low-traffic single-process setup.
"""

import threading
import uuid
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()

_FILES = {
    "jobs": DATA_DIR / "jobs.yml",
    "applications": DATA_DIR / "applications.yml",
    "contact_messages": DATA_DIR / "contact_messages.yml",
}


def _load(entity: str) -> list[dict[str, Any]]:
    path = _FILES[entity]
    if not path.exists():
        return []
    with path.open("r") as f:
        data = yaml.safe_load(f)
    return data or []


def _save(entity: str, rows: list[dict[str, Any]]) -> None:
    path = _FILES[entity]
    with path.open("w") as f:
        yaml.safe_dump(rows, f, sort_keys=False, default_flow_style=False)


def list_all(entity: str) -> list[dict[str, Any]]:
    with _lock:
        return _load(entity)


def get_by(entity: str, **filters: Any) -> dict[str, Any] | None:
    with _lock:
        rows = _load(entity)
    for row in rows:
        if all(row.get(k) == v for k, v in filters.items()):
            return row
    return None


def find_all_by(entity: str, **filters: Any) -> list[dict[str, Any]]:
    with _lock:
        rows = _load(entity)
    return [row for row in rows if all(row.get(k) == v for k, v in filters.items())]


def insert(entity: str, row: dict[str, Any]) -> dict[str, Any]:
    row = {**row}
    row.setdefault("id", str(uuid.uuid4()))
    with _lock:
        rows = _load(entity)
        rows.append(row)
        _save(entity, rows)
    return row


def update(entity: str, row_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    with _lock:
        rows = _load(entity)
        updated = None
        for row in rows:
            if row.get("id") == row_id:
                row.update(changes)
                updated = row
                break
        if updated is not None:
            _save(entity, rows)
    return updated


def delete(entity: str, row_id: str) -> bool:
    with _lock:
        rows = _load(entity)
        remaining = [row for row in rows if row.get("id") != row_id]
        if len(remaining) == len(rows):
            return False
        _save(entity, remaining)
    return True
