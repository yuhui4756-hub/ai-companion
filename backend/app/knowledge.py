from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .schemas import (
    DeleteKnowledgeSourceResponse,
    KnowledgeHitResponse,
    KnowledgeSourceResponse,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
    SearchKnowledgeResponse,
)

DEFAULT_CHUNK_SIZE = 700
DEFAULT_CHUNK_OVERLAP = 80
PROMPT_HEADER = "用户导入资料（仅供当前回复参考，不等同于长期记忆或模型事实）："
ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
}


class DuplicateKnowledgeSourceError(Exception):
    def __init__(self, source_id: str, title: str) -> None:
        self.source_id = source_id
        self.title = title
        super().__init__(f"同内容资料已存在：{title}")


class KnowledgeSourceNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class KnowledgeChunkDraft:
    content: str
    keywords: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def is_useful_keyword(value: str) -> bool:
    keyword = value.strip().lower()
    if not keyword:
        return False
    if has_cjk(keyword):
        return len(keyword) >= 2
    if keyword in ENGLISH_STOPWORDS:
        return False
    if keyword.isdigit():
        return len(keyword) >= 4
    return len(keyword) >= 3


def content_checksum(value: str) -> str:
    normalized = value.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def create_keyword_list(text: str) -> list[str]:
    normalized = normalize_text(text)
    words = [
        word.strip()
        for word in re.split(r"""[\s,.;:!?，。；：！？、()[\]{}"'“”‘’<>《》/\\|-]+""", normalized)
        if len(word.strip()) <= 24 and is_useful_keyword(word)
    ]
    compact_cjk = re.sub(r"[^\u4e00-\u9fff]", "", normalized)
    cjk_pairs = [compact_cjk[index : index + 2] for index in range(max(0, min(len(compact_cjk) - 1, 32)))]
    return list(dict.fromkeys([*words, *cjk_pairs]))[:48]


def split_paragraphs(text: str) -> list[str]:
    return [
        part.strip()
        for part in re.split(r"\n{2,}|(?<=[。！？!?])\s+", text.replace("\r\n", "\n"))
        if part.strip()
    ]


def split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[KnowledgeChunkDraft]:
    paragraphs = split_paragraphs(text)
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_long_text(paragraph, chunk_size, overlap))
            continue

        next_text = f"{current}\n\n{paragraph}" if current else paragraph
        if len(next_text) > chunk_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = next_text

    if current:
        chunks.append(current)

    return [KnowledgeChunkDraft(content=chunk, keywords=create_keyword_list(chunk)) for chunk in chunks]


def _source_from_row(row: sqlite3.Row) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=row["id"],
        title=row["title"],
        sourceType=KnowledgeSourceType(row["source_type"]),
        status=KnowledgeSourceStatus(row["status"]),
        chunkCount=int(row["chunk_count"]),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def create_source(
    connection: sqlite3.Connection,
    *,
    title: str,
    source_type: KnowledgeSourceType,
    content: str,
) -> KnowledgeSourceResponse:
    checksum = content_checksum(content)
    duplicate = connection.execute(
        """
        SELECT id, title
        FROM knowledge_sources
        WHERE checksum = ? AND status = 'active'
        LIMIT 1
        """,
        (checksum,),
    ).fetchone()
    if duplicate:
        raise DuplicateKnowledgeSourceError(source_id=duplicate["id"], title=duplicate["title"])

    source_id = f"knowledge-source-{uuid.uuid4()}"
    created_at = now_iso()
    source_title = title.strip() or "未命名资料"
    chunks = chunk_text(content)

    with connection:
        connection.execute(
            """
            INSERT INTO knowledge_sources(id, title, source_type, status, checksum, created_at, updated_at)
            VALUES(?, ?, ?, 'active', ?, ?, ?)
            """,
            (source_id, source_title, source_type.value, checksum, created_at, created_at),
        )
        for index, chunk in enumerate(chunks):
            connection.execute(
                """
                INSERT INTO knowledge_chunks(
                    id, source_id, chunk_index, content, keywords_json, embedding_json, status, created_at
                )
                VALUES(?, ?, ?, ?, ?, NULL, 'active', ?)
                """,
                (
                    f"knowledge-chunk-{uuid.uuid4()}",
                    source_id,
                    index,
                    chunk.content,
                    json.dumps(chunk.keywords, ensure_ascii=False),
                    created_at,
                ),
            )

    return get_source(connection, source_id)


def get_source(connection: sqlite3.Connection, source_id: str) -> KnowledgeSourceResponse:
    row = connection.execute(
        """
        SELECT s.*, COUNT(c.id) AS chunk_count
        FROM knowledge_sources s
        LEFT JOIN knowledge_chunks c ON c.source_id = s.id
        WHERE s.id = ?
        GROUP BY s.id
        """,
        (source_id,),
    ).fetchone()
    if row is None:
        raise KnowledgeSourceNotFoundError(source_id)
    return _source_from_row(row)


def list_sources(connection: sqlite3.Connection) -> list[KnowledgeSourceResponse]:
    rows = connection.execute(
        """
        SELECT s.*, COUNT(c.id) AS chunk_count
        FROM knowledge_sources s
        LEFT JOIN knowledge_chunks c ON c.source_id = s.id
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        """
    ).fetchall()
    return [_source_from_row(row) for row in rows]


def soft_delete_source(connection: sqlite3.Connection, source_id: str) -> DeleteKnowledgeSourceResponse:
    row = connection.execute("SELECT id FROM knowledge_sources WHERE id = ?", (source_id,)).fetchone()
    if row is None:
        raise KnowledgeSourceNotFoundError(source_id)

    updated_at = now_iso()
    with connection:
        connection.execute(
            "UPDATE knowledge_sources SET status = 'deleted', updated_at = ? WHERE id = ?",
            (updated_at, source_id),
        )
        cursor = connection.execute(
            "UPDATE knowledge_chunks SET status = 'deleted' WHERE source_id = ? AND status != 'deleted'",
            (source_id,),
        )

    return DeleteKnowledgeSourceResponse(
        id=source_id,
        status=KnowledgeSourceStatus.deleted,
        deletedChunkCount=cursor.rowcount if cursor.rowcount >= 0 else 0,
    )


def _score_chunk(content: str, keywords: list[str], query: str) -> float:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return 0

    normalized_content = normalize_text(content)
    score = 0.0
    for raw_keyword in keywords:
        if not isinstance(raw_keyword, str):
            continue
        keyword = raw_keyword.strip().lower()
        if not is_useful_keyword(keyword):
            continue
        if keyword and keyword in normalized_query:
            score += 3
        if has_cjk(keyword) and len(keyword) >= 2 and keyword[:2] in normalized_query and keyword in normalized_content:
            score += 1
    if len(normalized_query) >= 4 and normalized_query in normalized_content:
        score += 8
    return score


def search_knowledge(
    connection: sqlite3.Connection,
    *,
    query: str,
    top_k: int = 3,
    prompt_budget: int = 1200,
) -> SearchKnowledgeResponse:
    rows = connection.execute(
        """
        SELECT c.source_id, s.title AS source_title, c.chunk_index, c.content, c.keywords_json
        FROM knowledge_chunks c
        JOIN knowledge_sources s ON s.id = c.source_id
        WHERE s.status = 'active' AND c.status = 'active'
        """
    ).fetchall()

    hits: list[KnowledgeHitResponse] = []
    for row in rows:
        try:
            keywords = json.loads(row["keywords_json"])
        except json.JSONDecodeError:
            keywords = []
        score = _score_chunk(row["content"], keywords if isinstance(keywords, list) else [], query)
        if score <= 0:
            continue
        hits.append(
            KnowledgeHitResponse(
                sourceId=row["source_id"],
                sourceTitle=row["source_title"],
                chunkIndex=row["chunk_index"],
                content=row["content"],
                score=score,
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.sourceTitle, hit.chunkIndex))
    selected_hits = hits[:top_k]
    return SearchKnowledgeResponse(
        hits=selected_hits,
        promptContext=format_hits_for_prompt(selected_hits, prompt_budget),
    )


def format_hits_for_prompt(hits: list[KnowledgeHitResponse], prompt_budget: int) -> str:
    if not hits:
        return ""

    lines = [PROMPT_HEADER]
    used = len(PROMPT_HEADER)
    for hit in hits:
        line = f"- 来源《{hit.sourceTitle}》片段 {hit.chunkIndex + 1}：{hit.content}"
        if used + len(line) > prompt_budget:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines) if len(lines) > 1 else ""


def get_db_counts(connection: sqlite3.Connection) -> tuple[int, int, int, int]:
    source_count = connection.execute("SELECT COUNT(*) AS count FROM knowledge_sources").fetchone()["count"]
    active_source_count = connection.execute(
        "SELECT COUNT(*) AS count FROM knowledge_sources WHERE status = 'active'"
    ).fetchone()["count"]
    chunk_count = connection.execute("SELECT COUNT(*) AS count FROM knowledge_chunks").fetchone()["count"]
    active_chunk_count = connection.execute(
        "SELECT COUNT(*) AS count FROM knowledge_chunks WHERE status = 'active'"
    ).fetchone()["count"]
    return int(source_count), int(active_source_count), int(chunk_count), int(active_chunk_count)
