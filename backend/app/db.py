from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1


def get_db_path() -> Path:
    configured_path = os.environ.get("SUOYI_BACKEND_DB_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "data" / "suoyi-dev.sqlite"


def get_db_path_label() -> str:
    return "custom-env" if os.environ.get("SUOYI_BACKEND_DB_PATH") else "backend/data/suoyi-dev.sqlite"


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS knowledge_sources (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            status TEXT NOT NULL,
            checksum TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_active_checksum
            ON knowledge_sources(checksum)
            WHERE status = 'active';

        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            keywords_json TEXT NOT NULL,
            embedding_json TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES knowledge_sources(id)
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_status
            ON knowledge_chunks(source_id, status);
        """
    )
    connection.execute(
        """
        INSERT INTO app_meta(key, value, updated_at)
        VALUES('schemaVersion', ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (str(SCHEMA_VERSION),),
    )
    connection.commit()
