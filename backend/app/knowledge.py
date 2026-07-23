from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .embeddings import VectorCandidate, search_embedding_candidates
from .schemas import (
    DeleteKnowledgeSourceResponse,
    EmbeddingRuntimeConfig,
    KnowledgeHitResponse,
    KnowledgeSourceResponse,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
    SearchKnowledgeResponse,
)

DEFAULT_CHUNK_SIZE = 820
DEFAULT_CHUNK_OVERLAP = 80
CHUNKER_VERSION = "v2-structured"
INJECTION_SCORE_THRESHOLD = 10.0
VECTOR_ONLY_SCORE_BASE = 12.0
VECTOR_SCORE_WEIGHT = 22.0
HYBRID_RRF_K = 60.0
PROMPT_HEADER = "用户导入资料（仅供当前回复参考，不等同于长期记忆或模型事实）："
ENGLISH_STOPWORDS = {
    "a",
    "about",
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
GENERIC_QUERY_PARTS = {
    "预算金额",
    "负责人",
    "截止日期",
    "上线窗口",
    "上线时间",
    "发布时间",
    "发布窗口",
    "审核人",
    "主讲人",
    "保管人",
    "助教",
    "开票时限",
    "时限",
    "多久",
    "发票类型",
    "类型",
    "支持格式",
    "格式",
    "名额",
    "位置",
    "哪里",
    "在哪",
    "预算",
    "金额",
    "经费",
    "费用",
    "成本",
    "花费",
    "多少钱",
    "负责",
    "截止",
    "日期",
    "时间",
    "折扣码",
    "兑换码",
    "优惠码",
    "优惠口令",
    "口令",
    "升级码",
    "编号",
    "代码",
    "项目",
    "计划",
    "方案",
    "规则",
    "流程",
    "清单",
    "规范",
    "红线",
    "活动",
    "资料",
    "文档",
    "内容",
    "信息",
    "答案",
    "是什么",
    "是谁",
    "是多少",
    "有多少",
    "多少",
    "哪位",
    "哪个",
    "哪天",
    "什么时候",
    "请问",
    "告诉我",
    "帮我",
    "一下",
    "里面",
    "提到",
    "的",
    "是",
    "吗",
    "呢",
    "啊",
    "呀",
}
FIELD_SYNONYMS: dict[str, tuple[str, ...]] = {
    "identifier": (
        "编号",
        "代码",
        "项目编号",
        "折扣码",
        "兑换码",
        "优惠码",
        "优惠口令",
        "口令",
        "升级码",
        "id",
        "identifier",
        "code",
        "coupon code",
    ),
    "budget": ("预算", "预算金额", "金额", "经费", "费用", "成本", "花费", "多少钱", "budget", "cost"),
    "owner": ("负责人", "负责", "联系人", "审核人", "主讲人", "保管人", "助教", "owner", "person in charge"),
    "deadline": (
        "截止日期",
        "截止",
        "日期",
        "截止时间",
        "上线窗口",
        "上线时间",
        "发布时间",
        "发布窗口",
        "开票时限",
        "时限",
        "多久",
        "借用窗口",
        "上课时间",
        "deadline",
        "due date",
        "launch date",
    ),
    "condition": ("触发条件", "触发", "条件"),
    "format": ("支持格式", "格式"),
    "location": ("位置", "哪里", "在哪里", "在哪", "放在哪里"),
    "quota": ("名额", "人数"),
    "type": ("发票类型", "类型"),
    "deletion": ("删除规则", "删除", "删掉", "不再检索", "不再注入", "prompt", "模型参考"),
}
EXTRA_FACT_LABELS = (
    "规则",
    "目标",
    "触发条件",
    "处理动作",
    "证据来源",
    "发票类型",
    "开票时限",
    "名额",
    "支持格式",
    "切片原则",
    "删除规则",
    "密钥边界",
    "借用窗口",
    "位置",
    "助教",
    "上课时间",
    "语气原则",
    "节奏",
    "边界",
    "数据库位置",
    "回滚入口",
)
FACT_LABELS = tuple(dict.fromkeys([label for labels in FIELD_SYNONYMS.values() for label in labels] + list(EXTRA_FACT_LABELS)))
FACT_LABEL_PATTERN = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:\*\*)?("
    + "|".join(re.escape(label) for label in sorted(FACT_LABELS, key=len, reverse=True))
    + r"|答案)(?:\*\*)?\s*[:：|]\s*.+",
    re.IGNORECASE,
)
IDENTIFIER_PATTERN = re.compile(
    r"\b[A-Za-z]{1,10}[-_][A-Za-z0-9][A-Za-z0-9_-]{2,}\b|\b[A-Za-z]{2,}\d{2,}[A-Za-z0-9_-]*\b|\b[A-Za-z0-9]{8,}\b"
)
DATE_PATTERN = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")
NUMBER_FACT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:万元|万|元|%|天|日|月)\b")


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
    heading_path: str
    chunk_type: str
    content_hash: str
    token_estimate: int
    metadata: dict[str, Any]
    search_text: str


@dataclass(frozen=True)
class StructuredBlock:
    content: str
    heading_path: list[str]
    chunk_type: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ActiveSource:
    id: str
    title: str
    compact_title: str
    title_core: str


@dataclass(frozen=True)
class QueryAnalysis:
    query: str
    normalized_query: str
    compact_query: str
    distinctive_terms: list[str]
    identifiers: list[str]
    numeric_facts: list[str]
    field_terms: list[str]
    mentioned_source_ids: set[str]
    has_distinctive_signal: bool
    reason: str


@dataclass(frozen=True)
class SearchCandidate:
    hit: KnowledgeHitResponse
    chunk_id: str
    source_id: str
    score: float


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def compact_text(value: str) -> str:
    return re.sub(r"[\s,.;:!?，。；：！？、()[\]{}\"'“”‘’<>《》/\\|`~·\-_*#]+", "", value.lower())


def has_cjk(value: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value))


def strip_markdown_inline(value: str) -> str:
    return re.sub(r"[*_`~]+", "", value).strip()


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


def short_content_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def strip_generic_parts(value: str) -> str:
    remaining = compact_text(value)
    for part in sorted(GENERIC_QUERY_PARTS, key=len, reverse=True):
        remaining = remaining.replace(part, "")
    return remaining


def extract_identifier_tokens(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0).lower() for match in IDENTIFIER_PATTERN.finditer(text)))


def extract_numeric_fact_tokens(text: str) -> list[str]:
    values = [match.group(0).replace(" ", "") for match in DATE_PATTERN.finditer(text)]
    values.extend(match.group(0).replace(" ", "") for match in NUMBER_FACT_PATTERN.finditer(text))
    return list(dict.fromkeys(value.lower() for value in values))


def extract_english_terms(text: str) -> list[str]:
    terms = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,30}", text.lower()):
        if word in ENGLISH_STOPWORDS or word in {"id", "what", "who", "when", "where", "which"}:
            continue
        terms.append(word)
    return list(dict.fromkeys(terms))


def extract_cjk_terms(text: str, *, include_full: bool = True) -> list[str]:
    terms: list[str] = []
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        if include_full and len(sequence) <= 18:
            terms.append(sequence)
        max_window_start = min(len(sequence), 80)
        for size in (2, 3):
            if len(sequence) < size:
                continue
            for index in range(max_window_start - size + 1):
                token = sequence[index : index + size]
                if token not in GENERIC_QUERY_PARTS:
                    terms.append(token)
    return list(dict.fromkeys(term for term in terms if is_useful_keyword(term)))[:96]


def create_keyword_list(text: str) -> list[str]:
    normalized = normalize_text(text)
    words = [
        word.strip()
        for word in re.split(r"""[\s,.;:!?，。；：！？、()[\]{}"'“”‘’<>《》/\\|-]+""", normalized)
        if len(word.strip()) <= 32 and is_useful_keyword(word)
    ]
    return list(dict.fromkeys([*words, *extract_identifier_tokens(text), *extract_numeric_fact_tokens(text), *extract_cjk_terms(text)]))[:80]


def build_search_text(source_title: str, heading_path: str, content: str, keywords: list[str]) -> str:
    searchable = "\n".join([source_title, heading_path, content, " ".join(keywords)])
    tokens = [
        *extract_identifier_tokens(searchable),
        *extract_numeric_fact_tokens(searchable),
        *extract_english_terms(searchable),
        *extract_cjk_terms(searchable),
    ]
    return " ".join(dict.fromkeys([source_title, heading_path, content, *keywords, *tokens]))


def heading_path_to_text(path: list[str]) -> str:
    return " / ".join(part.strip() for part in path if part.strip())


def is_heading_line(line: str) -> re.Match[str] | None:
    return re.match(r"^(#{1,6})\s+(.+?)\s*$", line)


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return "|" in stripped and len([part for part in stripped.strip("|").split("|") if part.strip()]) >= 2


def is_markdown_table_separator(line: str) -> bool:
    cells = [part.strip() for part in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def is_list_line(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)", line))


def is_question_line(line: str) -> bool:
    return bool(re.match(r"^\s*(?:q|question|问|问题)\s*[:：]", line.strip(), re.IGNORECASE))


def is_answer_line(line: str) -> bool:
    return bool(re.match(r"^\s*(?:a|answer|答|答案)\s*[:：]", line.strip(), re.IGNORECASE))


def is_fact_line(line: str) -> bool:
    return bool(FACT_LABEL_PATTERN.match(line.strip()))


def count_fact_labels(text: str) -> int:
    compact = text.lower()
    count = 0
    for label in FACT_LABELS:
        if compact_text(label) and compact_text(label) in compact_text(compact):
            count += 1
    return count


def make_block(content: str, heading_path: list[str], chunk_type: str, metadata: dict[str, Any] | None = None) -> StructuredBlock | None:
    stripped = content.strip()
    if not stripped:
        return None
    actual_type = chunk_type
    if chunk_type in {"paragraph", "list"} and count_fact_labels(stripped) >= 2:
        actual_type = "fact_block"
    return StructuredBlock(
        content=stripped,
        heading_path=list(heading_path),
        chunk_type=actual_type,
        metadata=metadata or {},
    )


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


def split_lines_to_sized_blocks(lines: list[str], chunk_size: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in lines:
        next_text = f"{current}\n{line}" if current else line
        if current and len(next_text) > chunk_size:
            chunks.append(current)
            current = line
        else:
            current = next_text
    if current:
        chunks.append(current)
    return chunks


def split_block(block: StructuredBlock, chunk_size: int, overlap: int) -> list[StructuredBlock]:
    if len(block.content) <= chunk_size:
        return [block]

    if block.chunk_type in {"list", "table_block", "fact_block"}:
        line_chunks = split_lines_to_sized_blocks(block.content.splitlines(), chunk_size)
        return [
            StructuredBlock(
                content=chunk,
                heading_path=block.heading_path,
                chunk_type=block.chunk_type,
                metadata={**block.metadata, "splitFromLargeBlock": True},
            )
            for chunk in line_chunks
        ]

    return [
        StructuredBlock(
            content=chunk,
            heading_path=block.heading_path,
            chunk_type=block.chunk_type,
            metadata={**block.metadata, "splitFromLargeBlock": True},
        )
        for chunk in split_long_text(block.content, chunk_size, overlap)
    ]


def parse_structured_blocks(text: str) -> list[StructuredBlock]:
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[StructuredBlock] = []
    heading_path: list[str] = []
    paragraph_buffer: list[str] = []
    fact_buffer: list[str] = []
    list_buffer: list[str] = []

    def add_block(block: StructuredBlock | None) -> None:
        if block is not None:
            blocks.append(block)

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if paragraph_buffer:
            add_block(make_block("\n".join(paragraph_buffer), heading_path, "paragraph", {"lineCount": len(paragraph_buffer)}))
            paragraph_buffer = []

    def flush_fact() -> None:
        nonlocal fact_buffer
        if fact_buffer:
            add_block(make_block("\n".join(fact_buffer), heading_path, "fact_block", {"lineCount": len(fact_buffer)}))
            fact_buffer = []

    def flush_list() -> None:
        nonlocal list_buffer
        if list_buffer:
            chunk_type = "fact_block" if sum(1 for line in list_buffer if is_fact_line(line)) >= 2 else "list"
            add_block(make_block("\n".join(list_buffer), heading_path, chunk_type, {"lineCount": len(list_buffer)}))
            list_buffer = []

    def flush_all() -> None:
        flush_paragraph()
        flush_fact()
        flush_list()

    index = 0
    while index < len(lines):
        raw_line = lines[index].rstrip()
        stripped = raw_line.strip()

        if not stripped:
            flush_all()
            index += 1
            continue

        heading = is_heading_line(stripped)
        if heading:
            flush_all()
            level = len(heading.group(1))
            title = strip_markdown_inline(heading.group(2))
            heading_path = [*heading_path[: max(0, level - 1)], title]
            index += 1
            continue

        if is_table_line(stripped):
            flush_all()
            table_lines = [raw_line]
            index += 1
            while index < len(lines) and is_table_line(lines[index]):
                table_lines.append(lines[index].rstrip())
                index += 1
            if len(table_lines) >= 3 and is_markdown_table_separator(table_lines[1]):
                header = table_lines[0]
                data_rows = [line for line in table_lines[2:] if not is_markdown_table_separator(line)]
                for row_index, data_row in enumerate(data_rows):
                    add_block(
                        make_block(
                            "\n".join([header, data_row]),
                            heading_path,
                            "table_row",
                            {"rowCount": 1, "rowIndex": row_index},
                        )
                    )
            else:
                chunk_type = "table_row" if len(table_lines) <= 2 else "table_block"
                add_block(make_block("\n".join(table_lines), heading_path, chunk_type, {"rowCount": len(table_lines)}))
            continue

        if is_question_line(stripped):
            flush_all()
            qa_lines = [raw_line]
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and is_answer_line(lines[next_index]):
                qa_lines.append(lines[next_index].rstrip())
                add_block(make_block("\n".join(qa_lines), heading_path, "qa", {"lineCount": len(qa_lines)}))
                index = next_index + 1
                continue

        if is_fact_line(stripped):
            flush_paragraph()
            flush_list()
            fact_buffer.append(raw_line)
            index += 1
            continue

        if is_list_line(stripped):
            flush_paragraph()
            flush_fact()
            list_buffer.append(raw_line)
            index += 1
            continue

        flush_fact()
        flush_list()
        paragraph_buffer.append(raw_line)
        index += 1

    flush_all()
    return blocks


def make_chunk_draft(source_title: str, block: StructuredBlock) -> KnowledgeChunkDraft:
    heading_path = heading_path_to_text(block.heading_path)
    keywords = create_keyword_list("\n".join([source_title, heading_path, block.content]))
    metadata = {
        **block.metadata,
        "sourceTitle": source_title,
        "headingPath": block.heading_path,
        "charCount": len(block.content),
    }
    return KnowledgeChunkDraft(
        content=block.content,
        keywords=keywords,
        heading_path=heading_path,
        chunk_type=block.chunk_type,
        content_hash=short_content_hash("\n".join([source_title, heading_path, block.content])),
        token_estimate=len(block.content),
        metadata=metadata,
        search_text=build_search_text(source_title, heading_path, block.content, keywords),
    )


def chunk_text(
    text: str,
    *,
    source_title: str = "",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[KnowledgeChunkDraft]:
    blocks = parse_structured_blocks(text)
    if not blocks:
        fallback = make_block(text, [], "paragraph", {"fallback": True})
        blocks = [fallback] if fallback else []

    chunk_blocks: list[StructuredBlock] = []
    for block in blocks:
        chunk_blocks.extend(split_block(block, chunk_size, overlap))

    return [make_chunk_draft(source_title, block) for block in chunk_blocks]


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


def fts_ready(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT value FROM app_meta WHERE key = 'fts5Available'
        """
    ).fetchone()
    if row is None or row["value"] != "true":
        return False
    table = connection.execute(
        """
        SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_chunks_fts'
        """
    ).fetchone()
    return table is not None


def knowledge_search_mode(connection: sqlite3.Connection) -> str:
    return "fts5" if fts_ready(connection) else "keyword"


def backfill_chunk_metadata(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT c.id, c.content, c.keywords_json, c.heading_path, c.chunk_type, c.content_hash,
               c.chunker_version, c.token_estimate, c.metadata_json, c.search_text, s.title AS source_title
        FROM knowledge_chunks c
        JOIN knowledge_sources s ON s.id = c.source_id
        WHERE c.content_hash = ''
           OR c.search_text = ''
           OR c.token_estimate = 0
           OR c.metadata_json = '{}'
        """
    ).fetchall()
    if not rows:
        return

    with connection:
        for row in rows:
            try:
                keywords = json.loads(row["keywords_json"])
            except json.JSONDecodeError:
                keywords = []
            keyword_list = keywords if isinstance(keywords, list) else []
            heading_path = row["heading_path"] or ""
            metadata = {"sourceTitle": row["source_title"], "headingPath": heading_path.split(" / ") if heading_path else []}
            connection.execute(
                """
                UPDATE knowledge_chunks
                SET content_hash = CASE WHEN content_hash = '' THEN ? ELSE content_hash END,
                    token_estimate = CASE WHEN token_estimate = 0 THEN ? ELSE token_estimate END,
                    metadata_json = CASE WHEN metadata_json = '{}' THEN ? ELSE metadata_json END,
                    search_text = CASE WHEN search_text = '' THEN ? ELSE search_text END
                WHERE id = ?
                """,
                (
                    short_content_hash("\n".join([row["source_title"], heading_path, row["content"]])),
                    len(row["content"]),
                    json.dumps(metadata, ensure_ascii=False),
                    build_search_text(row["source_title"], heading_path, row["content"], keyword_list),
                    row["id"],
                ),
            )


def sync_fts_index(connection: sqlite3.Connection) -> bool:
    backfill_chunk_metadata(connection)
    if not fts_ready(connection):
        return False
    try:
        with connection:
            connection.execute("DELETE FROM knowledge_chunks_fts")
            rows = connection.execute(
                """
                SELECT c.id, c.source_id, s.title AS source_title, c.heading_path, c.content, c.search_text
                FROM knowledge_chunks c
                JOIN knowledge_sources s ON s.id = c.source_id
                WHERE s.status = 'active' AND c.status = 'active'
                """
            ).fetchall()
            connection.executemany(
                """
                INSERT INTO knowledge_chunks_fts(chunk_id, source_id, source_title, heading_path, content, search_text)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                [
                    (row["id"], row["source_id"], row["source_title"], row["heading_path"], row["content"], row["search_text"])
                    for row in rows
                ],
            )
        return True
    except sqlite3.Error:
        connection.execute(
            """
            INSERT INTO app_meta(key, value, updated_at)
            VALUES('fts5Available', 'false', datetime('now'))
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """
        )
        connection.commit()
        return False


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
    chunks = chunk_text(content, source_title=source_title)

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
                    id, source_id, chunk_index, content, keywords_json, embedding_json, status, created_at,
                    heading_path, chunk_type, content_hash, chunker_version, token_estimate, metadata_json, search_text
                )
                VALUES(?, ?, ?, ?, ?, NULL, 'active', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"knowledge-chunk-{uuid.uuid4()}",
                    source_id,
                    index,
                    chunk.content,
                    json.dumps(chunk.keywords, ensure_ascii=False),
                    created_at,
                    chunk.heading_path,
                    chunk.chunk_type,
                    chunk.content_hash,
                    CHUNKER_VERSION,
                    chunk.token_estimate,
                    json.dumps(chunk.metadata, ensure_ascii=False),
                    chunk.search_text,
                ),
            )
    sync_fts_index(connection)
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
        if fts_ready(connection):
            connection.execute("DELETE FROM knowledge_chunks_fts WHERE source_id = ?", (source_id,))

    return DeleteKnowledgeSourceResponse(
        id=source_id,
        status=KnowledgeSourceStatus.deleted,
        deletedChunkCount=cursor.rowcount if cursor.rowcount >= 0 else 0,
    )


def get_active_sources(connection: sqlite3.Connection) -> list[ActiveSource]:
    rows = connection.execute(
        """
        SELECT id, title FROM knowledge_sources WHERE status = 'active'
        """
    ).fetchall()
    return [
        ActiveSource(
            id=row["id"],
            title=row["title"],
            compact_title=compact_text(row["title"]),
            title_core=strip_generic_parts(row["title"]),
        )
        for row in rows
    ]


def extract_field_terms(query: str) -> list[str]:
    compact = compact_text(query)
    fields: list[str] = []
    for canonical, labels in FIELD_SYNONYMS.items():
        if any(compact_text(label) and compact_text(label) in compact for label in labels):
            fields.append(canonical)
    if "谁" in compact and "owner" not in fields:
        fields.append("owner")
    if ("什么时候" in compact or "哪天" in compact) and "deadline" not in fields:
        fields.append("deadline")
    return list(dict.fromkeys(fields))


def source_mentions_from_query(query: str, active_sources: list[ActiveSource]) -> set[str]:
    compact_query = compact_text(query)
    remaining = strip_generic_parts(query)
    mentioned: set[str] = set()
    for source in active_sources:
        if len(source.compact_title) >= 2 and source.compact_title in compact_query:
            mentioned.add(source.id)
            continue
        if len(source.title_core) >= 2 and source.title_core in remaining:
            mentioned.add(source.id)
    return mentioned


def analyze_query(query: str, active_sources: list[ActiveSource]) -> QueryAnalysis:
    normalized_query = normalize_text(query)
    compact_query = compact_text(query)
    identifiers = extract_identifier_tokens(query)
    numeric_facts = extract_numeric_fact_tokens(query)
    field_terms = extract_field_terms(query)
    mentioned_source_ids = source_mentions_from_query(query, active_sources)
    remaining = strip_generic_parts(query)
    distinctive_terms: list[str] = []
    if remaining:
        distinctive_terms.extend(extract_english_terms(remaining))
        distinctive_terms.extend(extract_cjk_terms(remaining))
        if has_cjk(remaining) and len(remaining) >= 2:
            distinctive_terms.insert(0, remaining[:18])

    for source in active_sources:
        if source.id in mentioned_source_ids:
            distinctive_terms.extend(term for term in (source.title_core, source.compact_title) if len(term) >= 2)

    distinctive_terms.extend(identifiers)
    distinctive_terms.extend(numeric_facts)
    distinctive_terms = list(dict.fromkeys(term.lower() for term in distinctive_terms if is_useful_keyword(term) or term in identifiers or term in numeric_facts))[:64]
    has_signal = bool(distinctive_terms or identifiers or numeric_facts or mentioned_source_ids)
    reason = "" if has_signal else "query-needs-specific-source-or-entity"
    return QueryAnalysis(
        query=query,
        normalized_query=normalized_query,
        compact_query=compact_query,
        distinctive_terms=distinctive_terms,
        identifiers=identifiers,
        numeric_facts=numeric_facts,
        field_terms=field_terms,
        mentioned_source_ids=mentioned_source_ids,
        has_distinctive_signal=has_signal,
        reason=reason,
    )


def quote_fts_term(term: str) -> str:
    return f'"{term.replace(chr(34), chr(34) + chr(34))}"'


def build_fts_query(analysis: QueryAnalysis) -> str:
    terms = [*analysis.identifiers, *analysis.numeric_facts, *analysis.distinctive_terms]
    useful_terms = [term for term in dict.fromkeys(terms) if len(term) >= 2]
    return " OR ".join(quote_fts_term(term) for term in useful_terms[:32])


def fetch_keyword_rows(connection: sqlite3.Connection, analysis: QueryAnalysis) -> list[sqlite3.Row]:
    params: list[Any] = []
    source_filter = ""
    if analysis.mentioned_source_ids:
        placeholders = ", ".join("?" for _ in analysis.mentioned_source_ids)
        source_filter = f"AND c.source_id IN ({placeholders})"
        params.extend(sorted(analysis.mentioned_source_ids))
    return connection.execute(
        f"""
        SELECT c.source_id, s.title AS source_title, c.id AS chunk_id, c.chunk_index, c.content, c.keywords_json,
               c.heading_path, c.chunk_type, c.content_hash, c.chunker_version, c.token_estimate, c.metadata_json,
               c.search_text, NULL AS bm25
        FROM knowledge_chunks c
        JOIN knowledge_sources s ON s.id = c.source_id
        WHERE s.status = 'active' AND c.status = 'active'
        {source_filter}
        """,
        params,
    ).fetchall()


def fetch_fts_rows(connection: sqlite3.Connection, analysis: QueryAnalysis) -> tuple[list[sqlite3.Row], bool]:
    fts_query = build_fts_query(analysis)
    if not fts_query:
        return [], False

    params: list[Any] = [fts_query]
    source_filter = ""
    if analysis.mentioned_source_ids:
        placeholders = ", ".join("?" for _ in analysis.mentioned_source_ids)
        source_filter = f"AND c.source_id IN ({placeholders})"
        params.extend(sorted(analysis.mentioned_source_ids))

    try:
        rows = connection.execute(
            f"""
            SELECT c.source_id, s.title AS source_title, c.id AS chunk_id, c.chunk_index, c.content, c.keywords_json,
                   c.heading_path, c.chunk_type, c.content_hash, c.chunker_version, c.token_estimate, c.metadata_json,
                   c.search_text, bm25(knowledge_chunks_fts) AS bm25
            FROM knowledge_chunks_fts
            JOIN knowledge_chunks c ON c.id = knowledge_chunks_fts.chunk_id
            JOIN knowledge_sources s ON s.id = c.source_id
            WHERE knowledge_chunks_fts MATCH ?
              AND s.status = 'active'
              AND c.status = 'active'
              {source_filter}
            ORDER BY bm25(knowledge_chunks_fts)
            LIMIT 50
            """,
            params,
        ).fetchall()
        return rows, True
    except sqlite3.Error:
        return [], False


def content_has_field(content: str, field_terms: list[str]) -> bool:
    compact = compact_text(content)
    for field in field_terms:
        for label in FIELD_SYNONYMS.get(field, ()):
            if compact_text(label) and compact_text(label) in compact:
                return True
    return False


def row_text_parts(row: sqlite3.Row) -> tuple[str, str, str]:
    title = normalize_text(row["source_title"])
    heading = normalize_text(row["heading_path"] or "")
    content = normalize_text(row["content"])
    return title, heading, content


def score_row(row: sqlite3.Row, analysis: QueryAnalysis, *, from_fts: bool) -> tuple[float, dict[str, float]]:
    title, heading, content = row_text_parts(row)
    compact_title = compact_text(row["source_title"])
    compact_heading = compact_text(row["heading_path"] or "")
    compact_content = compact_text(row["content"])

    scores = {
        "source": 0.0,
        "identifier": 0.0,
        "titleTerm": 0.0,
        "headingTerm": 0.0,
        "contentTerm": 0.0,
        "field": 0.0,
        "phrase": 0.0,
        "fts": 0.0,
    }
    if row["source_id"] in analysis.mentioned_source_ids:
        scores["source"] += 15

    for token in analysis.identifiers:
        if token and (token in content.lower() or token in title or token in heading):
            scores["identifier"] += 35
    for token in analysis.numeric_facts:
        compact_token = compact_text(token)
        if compact_token and compact_token in compact_content:
            scores["identifier"] += 22

    for term in analysis.distinctive_terms:
        compact_term = compact_text(term)
        if not compact_term:
            continue
        if compact_term in compact_title:
            scores["titleTerm"] += 12
        elif compact_term in compact_heading:
            scores["headingTerm"] += 9
        elif compact_term in compact_content:
            scores["contentTerm"] += 7 if has_cjk(compact_term) and len(compact_term) <= 3 else 5

    if analysis.field_terms and content_has_field(row["content"], analysis.field_terms):
        scores["field"] += 5 * len(analysis.field_terms)

    if len(analysis.compact_query) >= 4 and analysis.compact_query in compact_content:
        scores["phrase"] += 8

    if from_fts:
        scores["fts"] += 2

    total = sum(scores.values())
    if analysis.field_terms and analysis.mentioned_source_ids and not content_has_field(row["content"], analysis.field_terms):
        total -= 12
    return max(0.0, total), scores


def build_candidates(rows: list[sqlite3.Row], analysis: QueryAnalysis, *, from_fts: bool) -> list[SearchCandidate]:
    candidates: list[SearchCandidate] = []
    seen_hashes: set[str] = set()
    for row in rows:
        if analysis.field_terms and analysis.mentioned_source_ids and not content_has_field(row["content"], analysis.field_terms):
            continue
        score, scores = score_row(row, analysis, from_fts=from_fts)
        if score <= 0:
            continue
        content_hash = row["content_hash"] or row["chunk_id"]
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        candidates.append(
            SearchCandidate(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                score=score,
                hit=KnowledgeHitResponse(
                    sourceId=row["source_id"],
                    sourceTitle=row["source_title"],
                    chunkIndex=int(row["chunk_index"]),
                    content=row["content"],
                    score=round(score, 3),
                    headingPath=row["heading_path"] or "",
                    chunkType=row["chunk_type"] or "paragraph",
                    scores={key: round(value, 3) for key, value in scores.items() if value > 0},
                ),
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.hit.sourceTitle, candidate.hit.chunkIndex))
    return candidates


def vector_candidate_to_search_candidate(candidate: VectorCandidate, analysis: QueryAnalysis) -> SearchCandidate | None:
    if analysis.field_terms and analysis.mentioned_source_ids and not content_has_field(candidate.content, analysis.field_terms):
        return None

    score = VECTOR_ONLY_SCORE_BASE + candidate.cosine * VECTOR_SCORE_WEIGHT
    scores = {"vector": round(candidate.cosine, 3)}
    if candidate.source_id in analysis.mentioned_source_ids:
        score += 8
        scores["source"] = 8.0
    if analysis.field_terms and content_has_field(candidate.content, analysis.field_terms):
        field_score = 4 * len(analysis.field_terms)
        score += field_score
        scores["field"] = float(field_score)

    return SearchCandidate(
        chunk_id=candidate.chunk_id,
        source_id=candidate.source_id,
        score=score,
        hit=KnowledgeHitResponse(
            sourceId=candidate.source_id,
            sourceTitle=candidate.source_title,
            chunkIndex=candidate.chunk_index,
            content=candidate.content,
            score=round(score, 3),
            headingPath=candidate.heading_path,
            chunkType=candidate.chunk_type,
            scores=scores,
        ),
    )


def with_candidate_score(candidate: SearchCandidate, score: float, scores: dict[str, float]) -> SearchCandidate:
    hit = candidate.hit.model_copy(
        update={
            "score": round(score, 3),
            "scores": {key: round(value, 3) for key, value in scores.items() if value > 0},
        }
    )
    return SearchCandidate(
        hit=hit,
        chunk_id=candidate.chunk_id,
        source_id=candidate.source_id,
        score=score,
    )


def fuse_candidates(
    lexical_candidates: list[SearchCandidate],
    vector_candidates: list[SearchCandidate],
) -> list[SearchCandidate]:
    combined: dict[str, SearchCandidate] = {}
    scores_by_chunk: dict[str, dict[str, float]] = {}
    rank_bonus_by_chunk: dict[str, float] = {}

    for index, candidate in enumerate(lexical_candidates, start=1):
        combined[candidate.chunk_id] = candidate
        scores_by_chunk[candidate.chunk_id] = dict(candidate.hit.scores)
        rank_bonus_by_chunk[candidate.chunk_id] = rank_bonus_by_chunk.get(candidate.chunk_id, 0.0) + 1 / (HYBRID_RRF_K + index)

    for index, candidate in enumerate(vector_candidates, start=1):
        current = combined.get(candidate.chunk_id)
        rank_bonus_by_chunk[candidate.chunk_id] = rank_bonus_by_chunk.get(candidate.chunk_id, 0.0) + 1.35 / (HYBRID_RRF_K + index)
        if current is None:
            combined[candidate.chunk_id] = candidate
            scores_by_chunk[candidate.chunk_id] = dict(candidate.hit.scores)
            continue

        merged_scores = {**scores_by_chunk[candidate.chunk_id], **candidate.hit.scores}
        vector_boost = candidate.hit.scores.get("vector", 0) * VECTOR_SCORE_WEIGHT
        score = max(current.score, candidate.score) + vector_boost * 0.35
        combined[candidate.chunk_id] = with_candidate_score(current, score, merged_scores)
        scores_by_chunk[candidate.chunk_id] = merged_scores

    fused: list[SearchCandidate] = []
    for chunk_id, candidate in combined.items():
        rrf_score = rank_bonus_by_chunk.get(chunk_id, 0.0)
        total = candidate.score + rrf_score * 100
        scores = {**scores_by_chunk.get(chunk_id, {}), "rrf": rrf_score}
        fused.append(with_candidate_score(candidate, total, scores))

    fused.sort(key=lambda candidate: (-candidate.score, candidate.hit.sourceTitle, candidate.hit.chunkIndex))
    return fused


def select_prompt_hits(candidates: list[SearchCandidate], analysis: QueryAnalysis, top_k: int) -> tuple[list[KnowledgeHitResponse], bool, bool, str]:
    reliable = [candidate for candidate in candidates if candidate.score >= INJECTION_SCORE_THRESHOLD]
    if not reliable:
        return [], False, False, "no-reliable-hit"

    source_scores: dict[str, float] = {}
    for candidate in reliable:
        source_scores[candidate.source_id] = max(source_scores.get(candidate.source_id, 0.0), candidate.score)

    preferred_source_id: str | None = None
    if analysis.field_terms and not analysis.mentioned_source_ids and reliable and has_disambiguating_chunk_signal(reliable[0]):
        preferred_source_id = reliable[0].source_id

    if analysis.field_terms and not analysis.mentioned_source_ids and len(source_scores) > 1:
        sorted_scores = sorted(source_scores.values(), reverse=True)
        top_candidate = reliable[0]
        if (
            len(sorted_scores) >= 2
            and sorted_scores[1] >= sorted_scores[0] * 0.72
            and not has_disambiguating_chunk_signal(top_candidate)
        ):
            return [], False, True, "ambiguous-field-query"

    selected: list[KnowledgeHitResponse] = []
    selected_sources: set[str] = set()
    for candidate in reliable:
        if preferred_source_id is not None and candidate.source_id != preferred_source_id:
            continue
        if candidate.source_id in selected_sources and not has_strong_chunk_signal(candidate):
            continue
        if candidate.source_id not in selected_sources and len(selected_sources) >= 2:
            continue
        selected.append(candidate.hit)
        selected_sources.add(candidate.source_id)
        if len(selected) >= top_k:
            break

    return selected, bool(selected), False, ""


def has_strong_chunk_signal(candidate: SearchCandidate) -> bool:
    scores = candidate.hit.scores
    return (
        scores.get("identifier", 0) >= 20
        or scores.get("field", 0) > 0
        or scores.get("phrase", 0) > 0
        or scores.get("vector", 0) >= 0.55
        or scores.get("contentTerm", 0) >= 10
    )


def has_disambiguating_chunk_signal(candidate: SearchCandidate) -> bool:
    scores = candidate.hit.scores
    return (
        scores.get("identifier", 0) >= 20
        or scores.get("contentTerm", 0) >= 10
        or scores.get("titleTerm", 0) >= 12
        or scores.get("phrase", 0) > 0
        or scores.get("vector", 0) >= 0.55
    )


def search_knowledge(
    connection: sqlite3.Connection,
    *,
    query: str,
    top_k: int = 3,
    prompt_budget: int = 1200,
    retrieval_mode: str = "auto",
    embedding_runtime_config: EmbeddingRuntimeConfig | None = None,
) -> SearchKnowledgeResponse:
    active_sources = get_active_sources(connection)
    analysis = analyze_query(query, active_sources)
    fts_available = sync_fts_index(connection)
    mode = "fts5" if fts_available else "keyword"

    if not analysis.has_distinctive_signal:
        return SearchKnowledgeResponse(
            hits=[],
            promptContext="",
            mode=mode,
            shouldInject=False,
            needsClarification=True,
            reason=analysis.reason,
            ftsReady=fts_available,
            embeddingUsed=False,
            embeddingReady=False,
            embeddingReason="query-needs-specific-source-or-entity",
        )

    rows: list[sqlite3.Row]
    from_fts = False
    if fts_available:
        rows, from_fts = fetch_fts_rows(connection, analysis)
    else:
        rows = []

    if not rows:
        rows = fetch_keyword_rows(connection, analysis)
        from_fts = False
        if fts_available:
            mode = "keyword-fallback"

    candidates = build_candidates(rows, analysis, from_fts=from_fts)
    embedding_used = False
    embedding_ready = False
    embedding_reason = ""
    if retrieval_mode in {"auto", "hybrid"}:
        vector_result = search_embedding_candidates(
            connection,
            query=query,
            runtime_config=embedding_runtime_config,
            source_ids=analysis.mentioned_source_ids,
            limit=50,
        )
        embedding_used = vector_result.used
        embedding_ready = vector_result.ready
        embedding_reason = vector_result.reason
        vector_candidates = [
            candidate
            for candidate in (
                vector_candidate_to_search_candidate(vector_candidate, analysis)
                for vector_candidate in vector_result.candidates
            )
            if candidate is not None
        ]
        if vector_candidates:
            candidates = fuse_candidates(candidates, vector_candidates)
            mode = "hybrid"
        elif vector_result.used:
            mode = "hybrid-fallback"

    selected_hits, should_inject, needs_clarification, reason = select_prompt_hits(candidates, analysis, top_k)
    return SearchKnowledgeResponse(
        hits=selected_hits,
        promptContext=format_hits_for_prompt(selected_hits, prompt_budget) if should_inject else "",
        mode=mode,
        shouldInject=should_inject,
        needsClarification=needs_clarification,
        reason=reason,
        ftsReady=fts_available,
        embeddingUsed=embedding_used,
        embeddingReady=embedding_ready,
        embeddingReason=embedding_reason,
    )


def format_hits_for_prompt(hits: list[KnowledgeHitResponse], prompt_budget: int) -> str:
    if not hits:
        return ""

    lines = [PROMPT_HEADER]
    used = len(PROMPT_HEADER)
    for hit in hits:
        heading = f"（{hit.headingPath}）" if hit.headingPath else ""
        line = f"- 来源《{hit.sourceTitle}》{heading}片段 {hit.chunkIndex + 1}：{hit.content}"
        if used + len(line) > prompt_budget:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines) if len(lines) > 1 else ""


def get_db_counts(connection: sqlite3.Connection) -> tuple[int, int, int, int, bool, str]:
    source_count = connection.execute("SELECT COUNT(*) AS count FROM knowledge_sources").fetchone()["count"]
    active_source_count = connection.execute(
        "SELECT COUNT(*) AS count FROM knowledge_sources WHERE status = 'active'"
    ).fetchone()["count"]
    chunk_count = connection.execute("SELECT COUNT(*) AS count FROM knowledge_chunks").fetchone()["count"]
    active_chunk_count = connection.execute(
        "SELECT COUNT(*) AS count FROM knowledge_chunks WHERE status = 'active'"
    ).fetchone()["count"]
    ready = sync_fts_index(connection)
    return int(source_count), int(active_source_count), int(chunk_count), int(active_chunk_count), ready, "fts5" if ready else "keyword"
