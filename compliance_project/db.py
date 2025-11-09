"""Database utilities for the compliance project."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "compliance.db"


SCHEMA_NODES = """
CREATE TABLE IF NOT EXISTS compliance_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    category TEXT,
    tags TEXT,
    image_meta TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

SCHEMA_BLOCKS = """
CREATE TABLE IF NOT EXISTS compliance_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id TEXT NOT NULL UNIQUE,
    node_id TEXT NOT NULL,
    block_type TEXT,
    content TEXT NOT NULL,
    source TEXT,
    source_page INTEGER,
    metadata TEXT,
    sequence INTEGER DEFAULT 0,
    FOREIGN KEY(node_id) REFERENCES compliance_nodes(node_id) ON DELETE CASCADE
)
"""


@contextmanager
def connect(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """Context manager that yields a SQLite connection with sane defaults."""

    resolved = Path(db_path) if db_path else DB_PATH
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure the compliance tables exist."""

    conn.execute(SCHEMA_NODES)
    conn.execute(SCHEMA_BLOCKS)
    conn.commit()
