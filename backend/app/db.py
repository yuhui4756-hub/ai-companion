from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 4


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

        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS provider_configs (
            id TEXT PRIMARY KEY,
            provider_name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            model TEXT NOT NULL,
            options_json TEXT NOT NULL,
            api_key_ref TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS companions (
            id TEXT PRIMARY KEY,
            json TEXT NOT NULL,
            status TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            companion_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_messages_companion_order
            ON messages(companion_id, sort_order, created_at);

        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            scope TEXT NOT NULL,
            companion_id TEXT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER NOT NULL,
            confidence REAL NOT NULL,
            sensitivity TEXT NOT NULL,
            status TEXT NOT NULL,
            json TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_memories_scope_status
            ON memories(scope, companion_id, status);

        CREATE TABLE IF NOT EXISTS style_summaries (
            id TEXT PRIMARY KEY,
            json TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS migration_runs (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            snapshot_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            counts_json TEXT NOT NULL,
            errors_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_migration_runs_created_at
            ON migration_runs(created_at);
        """
    )
    ensure_knowledge_v3_schema(connection)
    ensure_embedding_v4_schema(connection)
    connection.execute(
        """
        INSERT INTO app_meta(key, value, updated_at)
        VALUES('schemaVersion', ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (str(SCHEMA_VERSION),),
    )
    connection.commit()


def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def add_column_if_missing(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in table_columns(connection, table_name):
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def sqlite_supports_fts5(connection: sqlite3.Connection) -> bool:
    try:
        connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.suoyi_fts5_probe USING fts5(value)")
        connection.execute("DROP TABLE IF EXISTS temp.suoyi_fts5_probe")
        return True
    except sqlite3.Error:
        return False


def set_app_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO app_meta(key, value, updated_at)
        VALUES(?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value),
    )


def ensure_knowledge_v3_schema(connection: sqlite3.Connection) -> None:
    add_column_if_missing(connection, "knowledge_chunks", "heading_path", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(connection, "knowledge_chunks", "chunk_type", "TEXT NOT NULL DEFAULT 'paragraph'")
    add_column_if_missing(connection, "knowledge_chunks", "content_hash", "TEXT NOT NULL DEFAULT ''")
    add_column_if_missing(connection, "knowledge_chunks", "chunker_version", "TEXT NOT NULL DEFAULT 'v1'")
    add_column_if_missing(connection, "knowledge_chunks", "token_estimate", "INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(connection, "knowledge_chunks", "metadata_json", "TEXT NOT NULL DEFAULT '{}'")
    add_column_if_missing(connection, "knowledge_chunks", "search_text", "TEXT NOT NULL DEFAULT ''")

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_type_version
            ON knowledge_chunks(chunk_type, chunker_version)
        """
    )

    fts_available = sqlite_supports_fts5(connection)
    set_app_meta(connection, "fts5Available", "true" if fts_available else "false")
    if not fts_available:
        return

    try:
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts
            USING fts5(
                chunk_id UNINDEXED,
                source_id UNINDEXED,
                source_title,
                heading_path,
                content,
                search_text,
                tokenize = 'unicode61'
            )
            """
        )
    except sqlite3.Error:
        set_app_meta(connection, "fts5Available", "false")


def ensure_embedding_v4_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS embedding_provider_configs (
            id TEXT PRIMARY KEY,
            provider_name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            batch_size INTEGER NOT NULL,
            timeout_ms INTEGER NOT NULL,
            enabled INTEGER NOT NULL,
            api_key_ref TEXT NOT NULL,
            last_checked_at TEXT,
            last_status TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS knowledge_embeddings (
            id TEXT PRIMARY KEY,
            chunk_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            chunker_version TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            vector_json TEXT,
            vector_norm REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_indexed_at TEXT,
            FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(id),
            FOREIGN KEY(source_id) REFERENCES knowledge_sources(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_embeddings_unique_revision
            ON knowledge_embeddings(chunk_id, provider_id, model, dimensions, content_hash, chunker_version);

        CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_lookup
            ON knowledge_embeddings(provider_id, model, dimensions, status, chunk_id);

        CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_source_status
            ON knowledge_embeddings(source_id, status);
        """
    )
