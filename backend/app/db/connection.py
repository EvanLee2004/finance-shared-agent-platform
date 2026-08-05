"""SQLite connection helpers — WAL, foreign_keys, busy_timeout."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Repo root = parents[3] of this file: backend/app/db/connection.py
_REPO_ROOT = Path(__file__).resolve().parents[3]


def default_data_root() -> Path:
    """FSA_DATA_ROOT or repo-adjacent data/."""
    env = os.environ.get("FSA_DATA_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return (_REPO_ROOT / "data").resolve()


def db_path(data_root: Path | None = None) -> Path:
    root = data_root if data_root is not None else default_data_root()
    return root / "app.db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open SQLite with mandatory PRAGMAs for the mid-platform."""
    if path is None:
        path = db_path()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def pragma_snapshot(conn: sqlite3.Connection) -> dict[str, str | int]:
    """Read runtime PRAGMAs used by tests."""
    foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    return {
        "foreign_keys": int(foreign_keys),
        "journal_mode": str(journal_mode).upper(),
        "busy_timeout": int(busy_timeout),
    }
