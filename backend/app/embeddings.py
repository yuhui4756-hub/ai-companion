from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .schemas import (
    EmbeddingConfigRequest,
    EmbeddingConfigResponse,
    EmbeddingHealthCheckResponse,
    EmbeddingRuntimeConfig,
    KnowledgeEmbeddingStatusResponse,
    ReindexKnowledgeEmbeddingsRequest,
    ReindexKnowledgeEmbeddingsResponse,
)

EMBEDDING_CONFIG_ID = "default"
API_KEY_REF = "renderer-localStorage"
DEFAULT_PROVIDER_NAME = "openai_compatible"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 1536
DEFAULT_BATCH_SIZE = 16
DEFAULT_TIMEOUT_MS = 10_000
OLLAMA_PROVIDER_NAME = "ollama"
OLLAMA_DEFAULT_BASE_URL = "http://127.0.0.1:11434/api"
VECTOR_MIN_COSINE = 0.42

SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~+/=-]{8,}|"
    r"(api[_-]?key|access[_-]?token|token|cookie|authorization|secret)(\s*[:=]\s*)[\"']?[^\"'\s,;，；}]+[\"']?",
    re.IGNORECASE,
)

MOCK_SYNONYM_GROUPS: dict[str, tuple[str, ...]] = {
    "budget": ("预算", "金额", "经费", "费用", "成本", "花费", "多少钱", "budget", "cost"),
    "owner": ("负责人", "负责", "联系人", "谁负责", "owner", "person in charge"),
    "deadline": ("截止日期", "截止", "日期", "截止时间", "什么时候", "deadline", "due date"),
    "identifier": ("编号", "代码", "项目编号", "identifier", "id"),
    "service_flow": ("客服", "客户", "沟通", "回复", "工单", "规范", "sop", "support"),
    "confirm_first": ("先确认", "确认问题", "第一步", "下一步", "处理前", "clarify"),
    "emotion_note": ("情绪", "记录", "复盘", "心情", "感受", "安慰", "回应", "难过", "低落", "emotion"),
    "choice_tone": ("选择", "命令", "讲道理", "接住", "先接住", "暂停", "慢一点"),
    "privacy_data": ("隐私", "敏感", "身份证", "银行卡", "api key", "密钥", "cookie", "凭证", "授权"),
    "knowledge_delete": ("删除", "删掉", "不再", "检索", "注入", "prompt", "模型参考"),
    "coupon": ("优惠码", "折扣码", "兑换码", "优惠口令", "口令", "coupon"),
}


class EmbeddingProviderError(Exception):
    pass


@dataclass(frozen=True)
class VectorCandidate:
    source_id: str
    source_title: str
    chunk_id: str
    chunk_index: int
    content: str
    heading_path: str
    chunk_type: str
    cosine: float


@dataclass(frozen=True)
class VectorSearchResult:
    candidates: list[VectorCandidate]
    used: bool
    ready: bool
    reason: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def redact_secret_text(value: str) -> str:
    return SECRET_PATTERN.sub(lambda match: f"{match.group(1) or 'secret'}{match.group(2) or ''}[redacted]", value)[:500]


def normalize_provider_name(value: str) -> str:
    normalized = re.sub(r"\s+", "_", value.strip().lower())
    return normalized or DEFAULT_PROVIDER_NAME


def normalize_base_url(value: str) -> str:
    trimmed = value.strip() or DEFAULT_BASE_URL
    parsed = urllib.parse.urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return DEFAULT_BASE_URL
    sanitized = parsed._replace(query="", fragment="")
    return urllib.parse.urlunparse(sanitized).rstrip("/")


def sanitize_config_request(payload: EmbeddingConfigRequest | EmbeddingRuntimeConfig) -> EmbeddingConfigRequest:
    return EmbeddingConfigRequest(
        providerName=normalize_provider_name(payload.providerName),
        baseURL=redact_secret_text(normalize_base_url(payload.baseURL)),
        model=redact_secret_text(payload.model.strip() or DEFAULT_MODEL),
        dimensions=payload.dimensions,
        batchSize=payload.batchSize,
        timeoutMs=payload.timeoutMs,
        enabled=payload.enabled,
    )


def default_embedding_config() -> EmbeddingConfigResponse:
    return EmbeddingConfigResponse(
        id=EMBEDDING_CONFIG_ID,
        providerName=DEFAULT_PROVIDER_NAME,
        baseURL=DEFAULT_BASE_URL,
        model=DEFAULT_MODEL,
        dimensions=DEFAULT_DIMENSIONS,
        batchSize=DEFAULT_BATCH_SIZE,
        timeoutMs=DEFAULT_TIMEOUT_MS,
        enabled=False,
        apiKeyRef=API_KEY_REF,
    )


def load_embedding_config(connection: sqlite3.Connection) -> EmbeddingConfigResponse:
    row = connection.execute(
        """
        SELECT id, provider_name, base_url, model, dimensions, batch_size, timeout_ms, enabled,
               api_key_ref, last_checked_at, last_status, last_error
        FROM embedding_provider_configs
        WHERE id = ?
        LIMIT 1
        """,
        (EMBEDDING_CONFIG_ID,),
    ).fetchone()
    if row is None:
        return default_embedding_config()
    return EmbeddingConfigResponse(
        id=row["id"],
        providerName=row["provider_name"],
        baseURL=row["base_url"],
        model=row["model"],
        dimensions=int(row["dimensions"]),
        batchSize=int(row["batch_size"]),
        timeoutMs=int(row["timeout_ms"]),
        enabled=bool(row["enabled"]),
        apiKeyRef=row["api_key_ref"],
        lastCheckedAt=row["last_checked_at"],
        lastStatus=row["last_status"],
        lastError=row["last_error"],
    )


def save_embedding_config(connection: sqlite3.Connection, payload: EmbeddingConfigRequest | EmbeddingRuntimeConfig) -> EmbeddingConfigResponse:
    sanitized = sanitize_config_request(payload)
    existing = load_embedding_config(connection)
    updated_at = now_iso()
    with connection:
        connection.execute(
            """
            INSERT INTO embedding_provider_configs(
                id, provider_name, base_url, model, dimensions, batch_size, timeout_ms, enabled,
                api_key_ref, last_checked_at, last_status, last_error, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                provider_name = excluded.provider_name,
                base_url = excluded.base_url,
                model = excluded.model,
                dimensions = excluded.dimensions,
                batch_size = excluded.batch_size,
                timeout_ms = excluded.timeout_ms,
                enabled = excluded.enabled,
                api_key_ref = excluded.api_key_ref,
                updated_at = excluded.updated_at
            """,
            (
                EMBEDDING_CONFIG_ID,
                sanitized.providerName,
                sanitized.baseURL,
                sanitized.model,
                sanitized.dimensions,
                sanitized.batchSize,
                sanitized.timeoutMs,
                1 if sanitized.enabled else 0,
                API_KEY_REF,
                existing.lastCheckedAt,
                existing.lastStatus,
                existing.lastError,
                updated_at,
                updated_at,
            ),
        )
        mark_stale_embeddings(connection, sanitized)
    return load_embedding_config(connection)


def update_config_status(connection: sqlite3.Connection, *, status: str, error: str = "") -> None:
    current = load_embedding_config(connection)
    now = now_iso()
    with connection:
        connection.execute(
            """
            INSERT INTO embedding_provider_configs(
                id, provider_name, base_url, model, dimensions, batch_size, timeout_ms, enabled,
                api_key_ref, last_checked_at, last_status, last_error, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_checked_at = excluded.last_checked_at,
                last_status = excluded.last_status,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (
                EMBEDDING_CONFIG_ID,
                current.providerName,
                current.baseURL,
                current.model,
                current.dimensions,
                current.batchSize,
                current.timeoutMs,
                1 if current.enabled else 0,
                API_KEY_REF,
                now,
                status,
                redact_secret_text(error),
                now,
                now,
            ),
        )


def has_runtime_key(runtime_config: EmbeddingRuntimeConfig) -> bool:
    if is_ollama_provider(runtime_config):
        return True
    return bool((runtime_config.apiKey or "").strip())


def runtime_to_config(runtime_config: EmbeddingRuntimeConfig) -> EmbeddingConfigRequest:
    return sanitize_config_request(runtime_config)


def embedding_endpoint(base_url: str) -> str:
    normalized = normalize_base_url(base_url)
    return normalized if normalized.endswith("/embeddings") else f"{normalized}/embeddings"


def is_ollama_provider(config: EmbeddingRuntimeConfig | EmbeddingConfigRequest) -> bool:
    return normalize_provider_name(config.providerName) == OLLAMA_PROVIDER_NAME


def is_local_ollama_base_url(base_url: str) -> bool:
    parsed = urllib.parse.urlparse(normalize_base_url(base_url))
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def ollama_embed_endpoint(base_url: str) -> str:
    normalized = normalize_base_url(base_url or OLLAMA_DEFAULT_BASE_URL)
    if not is_local_ollama_base_url(normalized):
        raise EmbeddingProviderError("embedding-provider-local-url-required")
    if normalized.endswith("/api/embed"):
        return normalized
    if normalized.endswith("/api"):
        return f"{normalized}/embed"
    return f"{normalized}/api/embed"


def vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def cosine_similarity(left: list[float], right: list[float], left_norm: float | None = None, right_norm: float | None = None) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_value = left_norm if left_norm is not None else vector_norm(left)
    right_value = right_norm if right_norm is not None else vector_norm(right)
    if left_value <= 0 or right_value <= 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_value * right_value)


def cjk_terms(text: str) -> list[str]:
    terms: list[str] = []
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if len(sequence) <= 18:
            terms.append(sequence)
        for size in (2, 3):
            if len(sequence) < size:
                continue
            for index in range(min(len(sequence), 80) - size + 1):
                terms.append(sequence[index : index + size])
    return list(dict.fromkeys(terms))


def mock_features(text: str) -> list[tuple[str, float]]:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)
    features: list[tuple[str, float]] = []
    for canonical, labels in MOCK_SYNONYM_GROUPS.items():
        if any(label.lower() in lowered or label.lower() in compact for label in labels):
            features.append((f"concept:{canonical}", 3.0))
    for value in re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,30}", lowered):
        features.append((f"word:{value}", 1.2))
    for value in re.findall(r"\b[A-Za-z]{1,10}[-_][A-Za-z0-9][A-Za-z0-9_-]{2,}\b", text):
        features.append((f"id:{value.lower()}", 5.0))
    for value in cjk_terms(text):
        features.append((f"cjk:{value}", 1.0))
    return features


def mock_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0 for _ in range(dimensions)]
    for feature, weight in mock_features(text):
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1 if digest[4] % 2 == 0 else -1
        vector[index] += weight * sign
    return vector


def create_mock_embeddings(texts: list[str], dimensions: int) -> list[list[float]]:
    return [mock_embedding(text, dimensions) for text in texts]


def create_openai_compatible_embeddings(texts: list[str], runtime_config: EmbeddingRuntimeConfig) -> list[list[float]]:
    api_key = (runtime_config.apiKey or "").strip()
    if not api_key:
        raise EmbeddingProviderError("embedding-api-key-missing")

    payload: dict[str, Any] = {
        "model": runtime_config.model,
        "input": texts,
    }
    if runtime_config.dimensions > 0:
        payload["dimensions"] = runtime_config.dimensions

    request = urllib.request.Request(
        embedding_endpoint(runtime_config.baseURL),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=runtime_config.timeoutMs / 1000) as response:
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as error:
        raise EmbeddingProviderError(f"embedding-provider-http-{error.code}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise EmbeddingProviderError("embedding-provider-network-error") from error
    except Exception as error:
        raise EmbeddingProviderError("embedding-provider-request-failed") from error

    try:
        data = json.loads(raw.decode("utf-8"))
        rows = data.get("data")
        if not isinstance(rows, list) or len(rows) != len(texts):
            raise ValueError("embedding-count-mismatch")
        vectors: list[list[float]] = []
        for item in rows:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(embedding, list) or not embedding:
                raise ValueError("embedding-empty")
            vectors.append([float(value) for value in embedding])
        return vectors
    except Exception as error:
        raise EmbeddingProviderError("embedding-provider-invalid-response") from error


def create_ollama_embeddings(texts: list[str], runtime_config: EmbeddingRuntimeConfig) -> list[list[float]]:
    payload: dict[str, Any] = {
        "model": runtime_config.model,
        "input": texts,
    }
    request = urllib.request.Request(
        ollama_embed_endpoint(runtime_config.baseURL),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=runtime_config.timeoutMs / 1000) as response:
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as error:
        raise EmbeddingProviderError(f"embedding-provider-http-{error.code}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise EmbeddingProviderError("embedding-provider-network-error") from error
    except Exception as error:
        raise EmbeddingProviderError("embedding-provider-request-failed") from error

    try:
        data = json.loads(raw.decode("utf-8"))
        rows = data.get("embeddings")
        if not isinstance(rows, list) and len(texts) == 1 and isinstance(data.get("embedding"), list):
            rows = [data["embedding"]]
        if not isinstance(rows, list) or len(rows) != len(texts):
            raise ValueError("embedding-count-mismatch")
        vectors: list[list[float]] = []
        for embedding in rows:
            if not isinstance(embedding, list) or not embedding:
                raise ValueError("embedding-empty")
            vectors.append([float(value) for value in embedding])
        return vectors
    except Exception as error:
        raise EmbeddingProviderError("embedding-provider-invalid-response") from error


def create_embeddings(texts: list[str], runtime_config: EmbeddingRuntimeConfig) -> list[list[float]]:
    provider_name = normalize_provider_name(runtime_config.providerName)
    if provider_name == "mock":
        time.sleep(0)
        return create_mock_embeddings(texts, runtime_config.dimensions)
    if provider_name == OLLAMA_PROVIDER_NAME:
        return create_ollama_embeddings(texts, runtime_config)
    return create_openai_compatible_embeddings(texts, runtime_config)


def embedding_input_from_row(row: sqlite3.Row) -> str:
    return "\n".join(
        part
        for part in [
            row["source_title"],
            row["heading_path"] or "",
            row["content"],
        ]
        if part
    )


def embedding_id_for(row: sqlite3.Row, config: EmbeddingConfigRequest) -> str:
    seed = "|".join(
        [
            row["chunk_id"],
            EMBEDDING_CONFIG_ID,
            config.model,
            str(config.dimensions),
            row["content_hash"],
            row["chunker_version"],
        ]
    )
    return f"knowledge-embedding-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:32]}"


def mark_stale_embeddings(connection: sqlite3.Connection, config: EmbeddingConfigRequest) -> int:
    updated_at = now_iso()
    cursor = connection.execute(
        """
        UPDATE knowledge_embeddings
        SET status = 'stale',
            error = '',
            updated_at = ?
        WHERE provider_id = ?
          AND status IN ('pending', 'indexing', 'ready', 'failed')
          AND (
            model != ?
            OR dimensions != ?
            OR NOT EXISTS (
                SELECT 1
                FROM knowledge_chunks c
                WHERE c.id = knowledge_embeddings.chunk_id
                  AND c.content_hash = knowledge_embeddings.content_hash
                  AND c.chunker_version = knowledge_embeddings.chunker_version
            )
          )
        """,
        (updated_at, EMBEDDING_CONFIG_ID, config.model, config.dimensions),
    )
    return cursor.rowcount if cursor.rowcount >= 0 else 0


def fetch_active_chunk_rows(
    connection: sqlite3.Connection,
    *,
    source_id: str | None = None,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    params: list[Any] = []
    source_filter = ""
    if source_id:
        source_filter = "AND c.source_id = ?"
        params.append(source_id)
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT ?"
        params.append(limit)
    return connection.execute(
        f"""
        SELECT c.id AS chunk_id, c.source_id, s.title AS source_title, c.chunk_index, c.content,
               c.heading_path, c.chunk_type, c.content_hash, c.chunker_version
        FROM knowledge_chunks c
        JOIN knowledge_sources s ON s.id = c.source_id
        WHERE s.status = 'active' AND c.status = 'active'
          {source_filter}
        ORDER BY s.updated_at DESC, c.chunk_index ASC
        {limit_clause}
        """,
        params,
    ).fetchall()


def existing_ready_embedding(connection: sqlite3.Connection, row: sqlite3.Row, config: EmbeddingConfigRequest) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id
        FROM knowledge_embeddings
        WHERE chunk_id = ?
          AND provider_id = ?
          AND model = ?
          AND dimensions = ?
          AND content_hash = ?
          AND chunker_version = ?
          AND status = 'ready'
        LIMIT 1
        """,
        (
            row["chunk_id"],
            EMBEDDING_CONFIG_ID,
            config.model,
            config.dimensions,
            row["content_hash"],
            row["chunker_version"],
        ),
    ).fetchone()


def set_embedding_status(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    config: EmbeddingConfigRequest,
    *,
    status: str,
    vector: list[float] | None = None,
    error: str = "",
) -> None:
    now = now_iso()
    embedding_id = embedding_id_for(row, config)
    vector_json = stable_json([round(value, 8) for value in vector]) if vector is not None else None
    norm = vector_norm(vector) if vector is not None else 0.0
    connection.execute(
        """
        INSERT INTO knowledge_embeddings(
            id, chunk_id, source_id, content_hash, chunker_version, provider_id, provider_name,
            model, dimensions, vector_json, vector_norm, status, error, created_at, updated_at, last_indexed_at
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chunk_id, provider_id, model, dimensions, content_hash, chunker_version) DO UPDATE SET
            provider_name = excluded.provider_name,
            vector_json = excluded.vector_json,
            vector_norm = excluded.vector_norm,
            status = excluded.status,
            error = excluded.error,
            updated_at = excluded.updated_at,
            last_indexed_at = excluded.last_indexed_at
        """,
        (
            embedding_id,
            row["chunk_id"],
            row["source_id"],
            row["content_hash"],
            row["chunker_version"],
            EMBEDDING_CONFIG_ID,
            config.providerName,
            config.model,
            config.dimensions,
            vector_json,
            norm,
            status,
            redact_secret_text(error),
            now,
            now,
            now if status == "ready" else None,
        ),
    )


def get_embedding_status(connection: sqlite3.Connection) -> KnowledgeEmbeddingStatusResponse:
    config = load_embedding_config(connection)
    request_config = EmbeddingConfigRequest(
        providerName=config.providerName,
        baseURL=config.baseURL,
        model=config.model,
        dimensions=config.dimensions,
        batchSize=config.batchSize,
        timeoutMs=config.timeoutMs,
        enabled=config.enabled,
    )
    mark_stale_embeddings(connection, request_config)
    connection.commit()

    active_count = int(
        connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM knowledge_chunks c
            JOIN knowledge_sources s ON s.id = c.source_id
            WHERE s.status = 'active' AND c.status = 'active'
            """
        ).fetchone()["count"]
    )

    def count_status(status: str) -> int:
        return int(
            connection.execute(
                """
                SELECT COUNT(DISTINCT e.chunk_id) AS count
                FROM knowledge_embeddings e
                JOIN knowledge_chunks c ON c.id = e.chunk_id
                JOIN knowledge_sources s ON s.id = c.source_id
                WHERE s.status = 'active'
                  AND c.status = 'active'
                  AND e.provider_id = ?
                  AND e.model = ?
                  AND e.dimensions = ?
                  AND e.content_hash = c.content_hash
                  AND e.chunker_version = c.chunker_version
                  AND e.status = ?
                """,
                (EMBEDDING_CONFIG_ID, config.model, config.dimensions, status),
            ).fetchone()["count"]
        )

    ready_count = count_status("ready")
    failed_count = count_status("failed")
    indexing_count = count_status("indexing")
    stale_count = int(
        connection.execute(
            """
            SELECT COUNT(DISTINCT e.chunk_id) AS count
            FROM knowledge_embeddings e
            JOIN knowledge_chunks c ON c.id = e.chunk_id
            JOIN knowledge_sources s ON s.id = c.source_id
            WHERE s.status = 'active'
              AND c.status = 'active'
              AND e.provider_id = ?
              AND (
                e.status = 'stale'
                OR e.model != ?
                OR e.dimensions != ?
                OR e.content_hash != c.content_hash
                OR e.chunker_version != c.chunker_version
              )
              AND NOT EXISTS (
                SELECT 1
                FROM knowledge_embeddings current
                WHERE current.chunk_id = c.id
                  AND current.provider_id = ?
                  AND current.model = ?
                  AND current.dimensions = ?
                  AND current.content_hash = c.content_hash
                  AND current.chunker_version = c.chunker_version
                  AND current.status = 'ready'
              )
            """,
            (EMBEDDING_CONFIG_ID, config.model, config.dimensions, EMBEDDING_CONFIG_ID, config.model, config.dimensions),
        ).fetchone()["count"]
    )
    pending_count = max(active_count - ready_count - failed_count - indexing_count, 0)
    last_indexed = connection.execute(
        """
        SELECT MAX(last_indexed_at) AS value
        FROM knowledge_embeddings
        WHERE provider_id = ? AND model = ? AND dimensions = ? AND status = 'ready'
        """,
        (EMBEDDING_CONFIG_ID, config.model, config.dimensions),
    ).fetchone()["value"]
    latest_error = connection.execute(
        """
        SELECT error
        FROM knowledge_embeddings
        WHERE provider_id = ? AND model = ? AND dimensions = ? AND status = 'failed' AND error IS NOT NULL AND error != ''
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (EMBEDDING_CONFIG_ID, config.model, config.dimensions),
    ).fetchone()
    vector_ready = bool(config.enabled and ready_count > 0)
    if not config.enabled:
        message = "向量检索未开启，本地 BM25/关键词检索仍可用。"
    elif vector_ready and pending_count == 0 and failed_count == 0 and stale_count == 0:
        message = "向量索引已就绪。"
    elif ready_count > 0:
        message = "向量索引部分就绪，可继续重建未完成或过期切片。"
    else:
        message = "向量检索已开启，但还没有可用索引。"

    return KnowledgeEmbeddingStatusResponse(
        providerId=EMBEDDING_CONFIG_ID,
        providerName=config.providerName,
        model=config.model,
        dimensions=config.dimensions,
        enabled=config.enabled,
        activeChunkCount=active_count,
        readyCount=ready_count,
        pendingCount=pending_count,
        indexingCount=indexing_count,
        failedCount=failed_count,
        staleCount=stale_count,
        vectorReady=vector_ready,
        lastIndexedAt=last_indexed,
        lastError=latest_error["error"] if latest_error else config.lastError,
        lexicalReady=True,
        message=message,
    )


def check_embedding_health(connection: sqlite3.Connection, runtime_config: EmbeddingRuntimeConfig) -> EmbeddingHealthCheckResponse:
    sanitized_config = runtime_to_config(runtime_config)
    save_embedding_config(connection, sanitized_config)
    checked_at = now_iso()
    if not runtime_config.enabled:
        update_config_status(connection, status="disabled")
        return EmbeddingHealthCheckResponse(
            ok=False,
            status="disabled",
            message="向量检索未开启，未发起 embedding 检查。",
            checkedAt=checked_at,
        )
    if not has_runtime_key(runtime_config):
        update_config_status(connection, status="missing-key", error="embedding-api-key-missing")
        return EmbeddingHealthCheckResponse(
            ok=False,
            status="missing-key",
            message="缺少 embedding API Key，未发起外部请求。",
            checkedAt=checked_at,
        )
    try:
        vector = create_embeddings(["suoyi embedding health check"], runtime_config)[0]
        update_config_status(connection, status="ok")
        return EmbeddingHealthCheckResponse(
            ok=True,
            status="ok",
            message="embedding provider 已通过兼容性检查。",
            dimensions=len(vector),
            checkedAt=checked_at,
        )
    except EmbeddingProviderError as error:
        redacted = redact_secret_text(str(error))
        update_config_status(connection, status="error", error=redacted)
        return EmbeddingHealthCheckResponse(
            ok=False,
            status="error",
            message=redacted,
            checkedAt=checked_at,
        )


def reindex_embeddings(
    connection: sqlite3.Connection,
    payload: ReindexKnowledgeEmbeddingsRequest,
) -> ReindexKnowledgeEmbeddingsResponse:
    runtime = payload.embeddingRuntimeConfig
    config = runtime_to_config(runtime)
    save_embedding_config(connection, config)
    stale = mark_stale_embeddings(connection, config)
    rows = fetch_active_chunk_rows(connection, source_id=payload.sourceId)
    if not config.enabled:
        connection.commit()
        status = get_embedding_status(connection)
        return ReindexKnowledgeEmbeddingsResponse(
            ok=False,
            status="disabled",
            indexed=0,
            skipped=0,
            failed=0,
            stale=stale,
            pending=status.pendingCount,
            ready=status.readyCount,
            message="向量检索未开启，未发送资料切片。",
        )
    if not has_runtime_key(runtime):
        connection.commit()
        status = get_embedding_status(connection)
        return ReindexKnowledgeEmbeddingsResponse(
            ok=False,
            status="missing-key",
            indexed=0,
            skipped=0,
            failed=0,
            stale=stale,
            pending=status.pendingCount,
            ready=status.readyCount,
            message="缺少 embedding API Key，未发送资料切片。",
        )

    indexed = 0
    skipped = 0
    failed = 0
    batch: list[sqlite3.Row] = []

    def flush_batch() -> None:
        nonlocal indexed, failed, batch
        if not batch:
            return
        texts = [embedding_input_from_row(row) for row in batch]
        try:
            vectors = create_embeddings(texts, runtime)
            if len(vectors) != len(batch):
                raise EmbeddingProviderError("embedding-count-mismatch")
            with connection:
                for row, vector in zip(batch, vectors):
                    if len(vector) != config.dimensions:
                        set_embedding_status(
                            connection,
                            row,
                            config,
                            status="failed",
                            error=f"embedding-dimensions-mismatch:{len(vector)}",
                        )
                        failed += 1
                        continue
                    set_embedding_status(connection, row, config, status="ready", vector=vector)
                    indexed += 1
        except EmbeddingProviderError as error:
            redacted = redact_secret_text(str(error))
            with connection:
                for row in batch:
                    set_embedding_status(connection, row, config, status="failed", error=redacted)
                    failed += 1
        finally:
            batch = []

    with connection:
        for row in rows:
            if not payload.force and existing_ready_embedding(connection, row, config):
                skipped += 1
                continue
            set_embedding_status(connection, row, config, status="indexing")
            batch.append(row)
            if len(batch) >= config.batchSize:
                flush_batch()
        flush_batch()
    status = get_embedding_status(connection)
    return ReindexKnowledgeEmbeddingsResponse(
        ok=failed == 0,
        status="ok" if failed == 0 else "partial-failed",
        indexed=indexed,
        skipped=skipped,
        failed=failed,
        stale=stale,
        pending=status.pendingCount,
        ready=status.readyCount,
        message="向量索引已更新。" if failed == 0 else "部分切片索引失败，已保留本地 BM25/关键词 fallback。",
    )


def fetch_ready_vector_rows(
    connection: sqlite3.Connection,
    config: EmbeddingConfigRequest,
    source_ids: set[str] | None,
    limit: int,
) -> list[sqlite3.Row]:
    params: list[Any] = [EMBEDDING_CONFIG_ID, config.model, config.dimensions]
    source_filter = ""
    if source_ids:
        placeholders = ", ".join("?" for _ in source_ids)
        source_filter = f"AND c.source_id IN ({placeholders})"
        params.extend(sorted(source_ids))
    params.append(limit)
    return connection.execute(
        f"""
        SELECT e.vector_json, e.vector_norm, c.id AS chunk_id, c.source_id, s.title AS source_title,
               c.chunk_index, c.content, c.heading_path, c.chunk_type, c.content_hash, c.chunker_version
        FROM knowledge_embeddings e
        JOIN knowledge_chunks c ON c.id = e.chunk_id
        JOIN knowledge_sources s ON s.id = c.source_id
        WHERE e.provider_id = ?
          AND e.model = ?
          AND e.dimensions = ?
          AND e.status = 'ready'
          AND e.content_hash = c.content_hash
          AND e.chunker_version = c.chunker_version
          AND s.status = 'active'
          AND c.status = 'active'
          {source_filter}
        ORDER BY e.last_indexed_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def search_embedding_candidates(
    connection: sqlite3.Connection,
    *,
    query: str,
    runtime_config: EmbeddingRuntimeConfig | None,
    source_ids: set[str],
    limit: int = 50,
) -> VectorSearchResult:
    if runtime_config is None:
        return VectorSearchResult(candidates=[], used=False, ready=False, reason="embedding-runtime-missing")
    config = runtime_to_config(runtime_config)
    if not config.enabled:
        return VectorSearchResult(candidates=[], used=False, ready=False, reason="embedding-disabled")
    if not has_runtime_key(runtime_config):
        return VectorSearchResult(candidates=[], used=False, ready=False, reason="embedding-key-missing")

    rows = fetch_ready_vector_rows(connection, config, source_ids or None, limit)
    if not rows:
        return VectorSearchResult(candidates=[], used=False, ready=False, reason="embedding-no-ready-vectors")

    try:
        query_vector = create_embeddings([query], runtime_config)[0]
    except EmbeddingProviderError as error:
        return VectorSearchResult(candidates=[], used=False, ready=True, reason=redact_secret_text(str(error)))
    query_norm = vector_norm(query_vector)
    candidates: list[VectorCandidate] = []
    for row in rows:
        try:
            vector = json.loads(row["vector_json"] or "[]")
            stored_vector = [float(value) for value in vector]
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        cosine = cosine_similarity(query_vector, stored_vector, query_norm, float(row["vector_norm"] or 0))
        if cosine < VECTOR_MIN_COSINE:
            continue
        candidates.append(
            VectorCandidate(
                source_id=row["source_id"],
                source_title=row["source_title"],
                chunk_id=row["chunk_id"],
                chunk_index=int(row["chunk_index"]),
                content=row["content"],
                heading_path=row["heading_path"] or "",
                chunk_type=row["chunk_type"] or "paragraph",
                cosine=cosine,
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.cosine, candidate.source_title, candidate.chunk_index))
    return VectorSearchResult(candidates=candidates[:limit], used=True, ready=True, reason="")
