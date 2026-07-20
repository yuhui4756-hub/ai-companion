from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any

from .knowledge import now_iso
from .schemas import (
    CoreCounts,
    CoreMigrationResponse,
    CoreProviderConfigWithoutKey,
    CoreSnapshot,
    CoreStatusResponse,
)

PROVIDER_CONFIG_ID = "default"
SECRET_FIELD_PATTERN = re.compile(r"(api[_-]?key|access[_-]?token|token|cookie|authorization|secret)", re.IGNORECASE)


def _redact_secret_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\u0000", "")
    normalized = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[redacted-api-key]", normalized)
    normalized = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}", "Bearer [redacted]", normalized, flags=re.IGNORECASE)
    normalized = re.sub(
        r"(api[_-]?key|access[_-]?token|token|cookie|authorization|secret)(\s*[:=]\s*)[\"']?[^\"'\s,;，；}]+[\"']?",
        r"\1\2[redacted]",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def redact_known_secret_patterns(value: str) -> str:
    return (
        _redact_secret_text(value)
        .replace("\ufeff", "")
    )


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            string_key = str(key)
            if SECRET_FIELD_PATTERN.search(string_key):
                sanitized[string_key] = "[redacted]"
            else:
                sanitized[string_key] = redact_secrets(item)
        return sanitized
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        return redact_known_secret_patterns(value)
    return value


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def snapshot_hash(snapshot: CoreSnapshot) -> str:
    payload = snapshot.model_dump(mode="json")
    payload.pop("snapshotHash", None)
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def _safe_string(value: Any, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def _safe_number(value: Any, fallback: float) -> float:
    return value if isinstance(value, (int, float)) else fallback


def _sanitize_provider_config(config: CoreProviderConfigWithoutKey) -> CoreProviderConfigWithoutKey:
    return CoreProviderConfigWithoutKey(
        providerName=redact_known_secret_patterns(config.providerName.strip()),
        baseURL=redact_known_secret_patterns(config.baseURL.strip()),
        model=redact_known_secret_patterns(config.model.strip()),
        options=redact_secrets(config.options) if isinstance(config.options, dict) else {},
        apiKeyRemoved=True,
    )


def _normalize_entity(entity: dict[str, Any], fallback_prefix: str) -> dict[str, Any]:
    sanitized = redact_secrets(entity)
    entity_id = _safe_string(sanitized.get("id")).strip()
    if not entity_id:
        entity_id = f"{fallback_prefix}-{hashlib.sha256(stable_json(sanitized).encode('utf-8')).hexdigest()[:24]}"
    sanitized["id"] = entity_id
    return sanitized


def _normalize_message(companion_id: str, message: dict[str, Any], sort_order: int) -> dict[str, Any]:
    sanitized = redact_secrets(message)
    role = _safe_string(sanitized.get("role"))
    if role not in {"user", "assistant"}:
        role = "user"
    created_at = _safe_string(sanitized.get("createdAt"), now_iso())
    content = _safe_string(sanitized.get("content"))
    message_id = _safe_string(sanitized.get("id")).strip()
    if not message_id:
        seed = f"{companion_id}|{role}|{content}|{created_at}"
        message_id = f"message-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:32]}"
    sanitized.update(
        {
            "id": message_id,
            "role": role,
            "content": content,
            "createdAt": created_at,
            "_sortOrder": sort_order,
        }
    )
    return sanitized


def sanitize_core_snapshot(snapshot: CoreSnapshot) -> CoreSnapshot:
    provider_config = _sanitize_provider_config(snapshot.providerConfigWithoutApiKey)
    companions = [
        _normalize_entity(companion, "companion")
        for companion in snapshot.companions
        if isinstance(companion, dict)
    ]
    messages_by_companion: dict[str, list[dict[str, Any]]] = {}
    for companion_id, messages in snapshot.messagesByCompanionId.items():
        if not isinstance(messages, list):
            continue
        safe_companion_id = _safe_string(companion_id).strip()
        if not safe_companion_id:
            continue
        messages_by_companion[safe_companion_id] = [
            _normalize_message(safe_companion_id, message, index)
            for index, message in enumerate(messages)
            if isinstance(message, dict)
        ]

    memories = [
        _normalize_entity(memory, "memory")
        for memory in snapshot.memories
        if isinstance(memory, dict)
    ]
    style_summaries = [
        _normalize_entity(summary, "style-summary")
        for summary in snapshot.styleSummaries
        if isinstance(summary, dict)
    ]

    normalized = CoreSnapshot(
        snapshotVersion=snapshot.snapshotVersion or "core-snapshot-v1",
        activeCompanionId=redact_known_secret_patterns(snapshot.activeCompanionId.strip()),
        providerConfigWithoutApiKey=provider_config,
        companions=companions,
        messagesByCompanionId=messages_by_companion,
        memories=memories,
        styleSummaries=style_summaries,
    )
    normalized.snapshotHash = snapshot_hash(normalized)
    return normalized


def get_core_counts(connection: sqlite3.Connection) -> CoreCounts:
    def count(table: str) -> int:
        return int(connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])

    return CoreCounts(
        companions=count("companions"),
        messages=count("messages"),
        memories=count("memories"),
        styleSummaries=count("style_summaries"),
        providerConfigs=count("provider_configs"),
        migrationRuns=count("migration_runs"),
    )


def _upsert_app_state(connection: sqlite3.Connection, key: str, value: str, updated_at: str) -> None:
    connection.execute(
        """
        INSERT INTO app_state(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, value, updated_at),
    )


def _upsert_provider_config(connection: sqlite3.Connection, config: CoreProviderConfigWithoutKey, updated_at: str) -> None:
    connection.execute(
        """
        INSERT INTO provider_configs(id, provider_name, base_url, model, options_json, api_key_ref, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            provider_name = excluded.provider_name,
            base_url = excluded.base_url,
            model = excluded.model,
            options_json = excluded.options_json,
            api_key_ref = excluded.api_key_ref,
            updated_at = excluded.updated_at
        """,
        (
            PROVIDER_CONFIG_ID,
            config.providerName,
            config.baseURL,
            config.model,
            stable_json(config.options),
            "renderer-localStorage",
            updated_at,
        ),
    )


def _upsert_companions(connection: sqlite3.Connection, companions: list[dict[str, Any]], updated_at: str) -> None:
    for index, companion in enumerate(companions):
        created_at = _safe_string(companion.get("createdAt"), updated_at)
        connection.execute(
            """
            INSERT INTO companions(id, json, status, sort_order, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                json = excluded.json,
                status = excluded.status,
                sort_order = excluded.sort_order,
                updated_at = excluded.updated_at
            """,
            (
                companion["id"],
                stable_json(companion),
                _safe_string(companion.get("status"), "active"),
                index,
                created_at,
                _safe_string(companion.get("updatedAt"), updated_at),
            ),
        )


def _upsert_messages(connection: sqlite3.Connection, messages_by_companion_id: dict[str, list[dict[str, Any]]]) -> None:
    for companion_id, messages in messages_by_companion_id.items():
        for message in messages:
            connection.execute(
                """
                INSERT INTO messages(id, companion_id, role, content, sort_order, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    companion_id = excluded.companion_id,
                    role = excluded.role,
                    content = excluded.content,
                    sort_order = excluded.sort_order,
                    created_at = excluded.created_at
                """,
                (
                    message["id"],
                    companion_id,
                    message["role"],
                    message["content"],
                    int(message.get("_sortOrder", 0)),
                    message["createdAt"],
                ),
            )


def _upsert_memories(connection: sqlite3.Connection, memories: list[dict[str, Any]], updated_at: str) -> None:
    for index, memory in enumerate(memories):
        created_at = _safe_string(memory.get("createdAt"), updated_at)
        connection.execute(
            """
            INSERT INTO memories(
                id, scope, companion_id, category, content, importance, confidence,
                sensitivity, status, json, sort_order, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                scope = excluded.scope,
                companion_id = excluded.companion_id,
                category = excluded.category,
                content = excluded.content,
                importance = excluded.importance,
                confidence = excluded.confidence,
                sensitivity = excluded.sensitivity,
                status = excluded.status,
                json = excluded.json,
                sort_order = excluded.sort_order,
                updated_at = excluded.updated_at
            """,
            (
                memory["id"],
                _safe_string(memory.get("scope"), "global"),
                _safe_string(memory.get("companionId")) or None,
                _safe_string(memory.get("category"), "preference"),
                _safe_string(memory.get("content")),
                int(_safe_number(memory.get("importance"), 2)),
                float(_safe_number(memory.get("confidence"), 0.72)),
                _safe_string(memory.get("sensitivity"), "normal"),
                _safe_string(memory.get("status"), "active"),
                stable_json(memory),
                index,
                created_at,
                _safe_string(memory.get("updatedAt"), updated_at),
            ),
        )


def _upsert_style_summaries(connection: sqlite3.Connection, style_summaries: list[dict[str, Any]], updated_at: str) -> None:
    for index, summary in enumerate(style_summaries):
        created_at = _safe_string(summary.get("createdAt"), updated_at)
        connection.execute(
            """
            INSERT INTO style_summaries(id, json, sort_order, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                json = excluded.json,
                sort_order = excluded.sort_order,
                updated_at = excluded.updated_at
            """,
            (
                summary["id"],
                stable_json(summary),
                index,
                created_at,
                _safe_string(summary.get("updatedAt"), updated_at),
            ),
        )


def save_core_snapshot(
    connection: sqlite3.Connection,
    snapshot: CoreSnapshot,
    *,
    source: str,
    replace: bool,
    record_migration: bool,
) -> CoreMigrationResponse:
    normalized = sanitize_core_snapshot(snapshot)
    updated_at = now_iso()

    with connection:
        if replace:
            connection.execute("DELETE FROM messages")
            connection.execute("DELETE FROM companions")
            connection.execute("DELETE FROM memories")
            connection.execute("DELETE FROM style_summaries")

        _upsert_app_state(connection, "activeCompanionId", normalized.activeCompanionId, updated_at)
        _upsert_app_state(connection, "snapshotHash", normalized.snapshotHash or "", updated_at)
        _upsert_provider_config(connection, normalized.providerConfigWithoutApiKey, updated_at)
        _upsert_companions(connection, normalized.companions, updated_at)
        _upsert_messages(connection, normalized.messagesByCompanionId)
        _upsert_memories(connection, normalized.memories, updated_at)
        _upsert_style_summaries(connection, normalized.styleSummaries, updated_at)

        counts = get_core_counts(connection)
        if record_migration:
            run_id = f"{source}:{normalized.snapshotHash}"
            connection.execute(
                """
                INSERT INTO migration_runs(id, source, snapshot_hash, status, counts_json, errors_json, created_at)
                VALUES(?, ?, ?, 'success', ?, '[]', ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    counts_json = excluded.counts_json
                """,
                (run_id, source, normalized.snapshotHash, stable_json(counts.model_dump()), updated_at),
            )
            counts = get_core_counts(connection)

    return CoreMigrationResponse(
        ok=True,
        status="success",
        snapshotHash=normalized.snapshotHash or "",
        counts=counts,
        message="核心数据已写入本机 SQLite；旧 localStorage 未清空。",
    )


def load_core_snapshot(connection: sqlite3.Connection) -> CoreSnapshot:
    active_row = connection.execute(
        "SELECT value FROM app_state WHERE key = 'activeCompanionId' LIMIT 1"
    ).fetchone()
    provider_row = connection.execute(
        "SELECT provider_name, base_url, model, options_json FROM provider_configs WHERE id = ?",
        (PROVIDER_CONFIG_ID,),
    ).fetchone()
    companions = [
        json.loads(row["json"])
        for row in connection.execute("SELECT json FROM companions ORDER BY sort_order ASC, updated_at DESC").fetchall()
    ]
    messages_by_companion_id: dict[str, list[dict[str, Any]]] = {}
    for row in connection.execute(
        "SELECT id, companion_id, role, content, created_at FROM messages ORDER BY companion_id ASC, sort_order ASC, created_at ASC"
    ).fetchall():
        messages_by_companion_id.setdefault(row["companion_id"], []).append(
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "createdAt": row["created_at"],
            }
        )
    memories = [
        json.loads(row["json"])
        for row in connection.execute("SELECT json FROM memories ORDER BY sort_order ASC, updated_at DESC").fetchall()
    ]
    style_summaries = [
        json.loads(row["json"])
        for row in connection.execute("SELECT json FROM style_summaries ORDER BY sort_order ASC, updated_at DESC").fetchall()
    ]

    provider_config = CoreProviderConfigWithoutKey()
    if provider_row:
        try:
            options = json.loads(provider_row["options_json"])
        except json.JSONDecodeError:
            options = {}
        provider_config = CoreProviderConfigWithoutKey(
            providerName=provider_row["provider_name"],
            baseURL=provider_row["base_url"],
            model=provider_row["model"],
            options=options if isinstance(options, dict) else {},
            apiKeyRemoved=True,
        )

    snapshot = CoreSnapshot(
        activeCompanionId=active_row["value"] if active_row else "",
        providerConfigWithoutApiKey=provider_config,
        companions=companions,
        messagesByCompanionId=messages_by_companion_id,
        memories=memories,
        styleSummaries=style_summaries,
    )
    snapshot.snapshotHash = snapshot_hash(snapshot)
    return snapshot


def get_core_status(connection: sqlite3.Connection, schema_version: int) -> CoreStatusResponse:
    latest = connection.execute(
        """
        SELECT snapshot_hash, status
        FROM migration_runs
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    counts = get_core_counts(connection)
    return CoreStatusResponse(
        schemaVersion=schema_version,
        coreReady=True,
        latestMigrationHash=latest["snapshot_hash"] if latest else None,
        latestMigrationStatus=latest["status"] if latest else None,
        counts=counts,
        message="核心数据 SQLite 可用。" if latest else "核心数据 SQLite 可用，尚未记录 localStorage 迁移。",
    )
