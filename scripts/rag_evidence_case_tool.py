from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


EVIDENCE_VERSION = "suoyi-rag-evidence-v1"
CASE_VERSION = "suoyi-rag-benchmark-case-v1"
CASE_STATUSES = {"draft", "reviewed", "active", "archived"}
RUNNABLE_STATUSES = {"reviewed", "active"}
RETRIEVAL_MODES = {"auto", "keyword", "hybrid"}
ANSWER_EXPECTATIONS = {"fact", "clarify", "no-answer", "source-identification"}
DEFAULT_EXCERPT_CHARS = 240
DEFAULT_ANSWER_EXCERPT_CHARS = 600
WORKSPACE_DIRS = ("inbox", "drafts", "reviewed", "active", "archived", "bundles", "runs", "reports")
WORKSPACE_CASE_DIRS = ("drafts", "reviewed", "active", "archived")
RUN_SUMMARY_VERSION = "suoyi-rag-run-summary-v1"
WORKSPACE_README = """# 所依 RAG Case 本地工作区

这个目录用于本机沉淀 RAG evidence、benchmark case、运行结果和摘要，默认不进入 Git。

- `inbox/`：放 UI 导出的 `suoyi-rag-evidence-v1` JSON。
- `drafts/`：由 evidence 转出的 draft case，默认 `safeToCommit=false`。
- `reviewed/`：人工补全 expected 后的 case。
- `active/`：当前纳入本地回归的小样本 case。
- `archived/`：暂时不用或过期的 case。
- `bundles/`：导出的 runnable JSONL。
- `runs/`：`rag_answer_benchmark.py --output-json` 的本地运行结果。
- `reports/`：由 `summarize-run` 生成的本地摘要。

私有 evidence/case 可能包含用户问题、回答和短摘录，只能本地处理；不要把真实密钥、Cookie、扫码凭证或未脱敏用户资料提交到仓库。
"""


class CaseToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class ValidationSummary:
    total: int
    statuses: dict[str, int]


SENSITIVE_VALUE_PATTERNS = (
    ("openai_key", re.compile(r"sk-[A-Za-z0-9_-]{8,}", re.IGNORECASE)),
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
    ("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]+", re.IGNORECASE)),
    ("gh_token_assignment", re.compile(r"\bGH_TOKEN\b\s*[:=]", re.IGNORECASE)),
    ("api_key_assignment", re.compile(r"\bapi[_-]?key\b\s*[:=]\s*[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
    ("access_token_assignment", re.compile(r"\baccess[_-]?token\b\s*[:=]\s*[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
    ("cookie_header", re.compile(r"\bCookie\s*:\s*\S+", re.IGNORECASE)),
)
SENSITIVE_FIELD_NAMES = {"apikey", "api_key", "token", "accesstoken", "authorization", "cookie", "secret", "ghtoken"}


def json_path(parent: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}" if parent else key


def normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", key.lower())


def scan_sensitive_values(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = json_path(path, str(key))
            if normalized_key(str(key)) in SENSITIVE_FIELD_NAMES and isinstance(child, str) and child.strip():
                raise CaseToolError(f"sensitive field value detected at {child_path}")
            scan_sensitive_values(child, child_path)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            scan_sensitive_values(child, json_path(path, index))
        return
    if isinstance(value, str):
        for label, pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                raise CaseToolError(f"sensitive value pattern detected at {path}: {label}")


def read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CaseToolError(f"invalid JSON in {path}: line {error.lineno} column {error.colno}") from error


def read_jsonl_file(path: Path) -> list[Any]:
    records: list[Any] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            records.append(json.loads(stripped))
        except json.JSONDecodeError as error:
            raise CaseToolError(f"invalid JSONL in {path}: line {line_number} column {error.colno}") from error
    return records


def immediate_input_files(paths: Iterable[Path], *, suffixes: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            raise CaseToolError(f"input path does not exist: {path}")
        if path.is_dir():
            files.extend(
                child
                for child in sorted(path.iterdir())
                if child.is_file() and child.suffix.lower() in suffixes
            )
        elif path.is_file():
            if path.suffix.lower() not in suffixes:
                raise CaseToolError(f"unsupported input suffix for {path}; expected {', '.join(suffixes)}")
            files.append(path)
        else:
            raise CaseToolError(f"input path is not a file or directory: {path}")
    if not files:
        raise CaseToolError("no input files found")
    return files


def load_cases_from_path(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        cases: list[dict[str, Any]] = []
        for child in immediate_input_files([path], suffixes=(".json", ".jsonl")):
            cases.extend(load_cases_from_path(child))
        return cases
    if path.suffix.lower() == ".jsonl":
        raw_records = read_jsonl_file(path)
    elif path.suffix.lower() == ".json":
        raw = read_json_file(path)
        raw_records = raw if isinstance(raw, list) else [raw]
    else:
        raise CaseToolError(f"unsupported case file suffix: {path}")

    cases: list[dict[str, Any]] = []
    for index, record in enumerate(raw_records):
        if not isinstance(record, dict):
            raise CaseToolError(f"case record at {path}[{index}] must be an object")
        cases.append(record)
    return cases


def load_evidence_files(paths: Iterable[Path]) -> list[tuple[Path, dict[str, Any]]]:
    files = immediate_input_files(paths, suffixes=(".json",))
    documents: list[tuple[Path, dict[str, Any]]] = []
    for path in files:
        raw = read_json_file(path)
        if not isinstance(raw, dict):
            raise CaseToolError(f"evidence file must contain a JSON object: {path}")
        scan_sensitive_values(raw)
        if raw.get("version") != EVIDENCE_VERSION:
            raise CaseToolError(f"unsupported evidence version in {path}: {raw.get('version')!r}")
        documents.append((path, raw))
    return documents


def truncate_text(value: Any, limit: int = DEFAULT_EXCERPT_CHARS) -> str:
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def safe_metadata(value: Any, *, string_limit: int = 160) -> Any:
    if isinstance(value, dict):
        return {str(key): safe_metadata(child, string_limit=string_limit) for key, child in value.items()}
    if isinstance(value, list):
        return [safe_metadata(child, string_limit=string_limit) for child in value[:20]]
    if isinstance(value, str):
        return truncate_text(value, string_limit)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return truncate_text(str(value), string_limit)


def text_content(value: Any) -> str:
    if isinstance(value, dict):
        content = value.get("content")
        return content if isinstance(content, str) else ""
    return value if isinstance(value, str) else ""


def coerce_bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def normalize_retrieval_mode(mode: Any, *, embedding_used: bool = False) -> str:
    text = str(mode or "").lower()
    if embedding_used or "hybrid" in text or "vector" in text:
        return "hybrid"
    if "keyword" in text:
        return "keyword"
    return "auto"


def answer_expectation_for(query: str, *, should_inject: bool, needs_clarification: bool) -> str:
    if should_inject:
        compact_query = re.sub(r"\s+", "", query)
        if any(marker in compact_query for marker in ("哪份资料", "哪份文档", "哪份规范", "哪份说明", "对应哪份")):
            return "source-identification"
        return "fact"
    return "clarify" if needs_clarification else "no-answer"


def slug_from_text(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", value.lower())
    slug = "-".join(tokens[:6])
    return slug[:48].strip("-") or "case"


def stable_case_id(evidence: dict[str, Any], query: str, top_source_title: str | None) -> str:
    exported_at = evidence.get("exportedAt") if isinstance(evidence.get("exportedAt"), str) else ""
    date_token = re.sub(r"[^0-9]", "", exported_at[:10]) or "undated"
    basis = {
        "exportedAt": exported_at,
        "query": query,
        "source": top_source_title or "",
        "answerId": (evidence.get("answer") or {}).get("id") if isinstance(evidence.get("answer"), dict) else "",
    }
    digest = hashlib.sha256(json.dumps(basis, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"evidence-{date_token}-{slug_from_text(query or top_source_title or '')}-{digest}"


def compact_hit(hit: dict[str, Any]) -> dict[str, Any]:
    content = hit.get("content", hit.get("contentExcerpt", hit.get("excerpt", "")))
    compact: dict[str, Any] = {
        "sourceId": hit.get("sourceId"),
        "sourceTitle": hit.get("sourceTitle"),
        "chunkIndex": hit.get("chunkIndex"),
        "score": hit.get("score"),
        "scores": safe_metadata(hit.get("scores") or {}),
        "headingPath": hit.get("headingPath"),
        "chunkType": hit.get("chunkType"),
        "metadata": safe_metadata(hit.get("metadata") or {}),
        "contentExcerpt": truncate_text(content),
    }
    return {key: value for key, value in compact.items() if value not in (None, "", {}, [])}


def draft_case_from_evidence(
    evidence: dict[str, Any],
    *,
    corpus_id: str,
    source_policy: str,
    corpus_format: str,
    fixture_ref: str,
    collected_from: str,
) -> dict[str, Any]:
    scan_sensitive_values(evidence)
    if evidence.get("version") != EVIDENCE_VERSION:
        raise CaseToolError(f"unsupported evidence version: {evidence.get('version')!r}")

    question = text_content(evidence.get("question"))
    answer = text_content(evidence.get("answer"))
    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    trace = evidence.get("trace") if isinstance(evidence.get("trace"), dict) else {}
    raw_hits = trace.get("hits") if isinstance(trace.get("hits"), list) else []
    hits = [compact_hit(hit) for hit in raw_hits if isinstance(hit, dict)]
    top_hit = hits[0] if hits else {}
    top_source_title = top_hit.get("sourceTitle") if isinstance(top_hit.get("sourceTitle"), str) else None
    should_inject = coerce_bool(summary.get("shouldInject", trace.get("shouldInject")), default=bool(hits))
    needs_clarification = coerce_bool(summary.get("needsClarification", trace.get("needsClarification")), default=False)
    embedding_used = coerce_bool(summary.get("embeddingUsed", trace.get("embeddingUsed")), default=False)
    retrieval_mode = normalize_retrieval_mode(summary.get("mode", trace.get("mode")), embedding_used=embedding_used)

    return {
        "version": CASE_VERSION,
        "id": stable_case_id(evidence, question, top_source_title),
        "status": "draft",
        "origin": {
            "type": "rag-evidence-json",
            "evidenceVersion": EVIDENCE_VERSION,
            "exportedAt": evidence.get("exportedAt"),
            "collectedFrom": collected_from,
            "redactionStatus": "unreviewed",
        },
        "privacy": {
            "containsUserPrivateText": True,
            "safeToCommit": False,
            "apiKeyIncluded": False,
            "fullKnowledgeChunkIncluded": False,
            "redactions": [],
        },
        "corpus": {
            "id": corpus_id,
            "sourcePolicy": source_policy,
            "format": corpus_format,
            "fixtureRef": fixture_ref,
        },
        "query": question,
        "expected": {
            "shouldInject": should_inject,
            "needsClarification": needs_clarification,
            "expectedSourceTitle": top_source_title if should_inject else None,
            "requiredFacts": [],
            "forbiddenFacts": [],
            "requiredSourceTitles": [top_source_title] if should_inject and top_source_title else [],
            "forbiddenSourceTitles": [],
            "retrievalMode": retrieval_mode,
            "answerExpectation": answer_expectation_for(
                question,
                should_inject=should_inject,
                needs_clarification=needs_clarification,
            ),
        },
        "evidence": {
            "answerExcerpt": truncate_text(answer, DEFAULT_ANSWER_EXCERPT_CHARS),
            "traceSummary": {
                "mode": summary.get("mode", trace.get("mode")),
                "shouldInject": should_inject,
                "needsClarification": needs_clarification,
                "embeddingUsed": embedding_used,
                "embeddingReady": summary.get("embeddingReady", trace.get("embeddingReady")),
                "reason": truncate_text(summary.get("reason", trace.get("reason")), 180),
                "hitCount": len(hits),
                "topSourceTitle": top_source_title,
            },
            "hits": hits[:5],
        },
        "review": {
            "reviewedBy": "",
            "reviewedAt": "",
            "notes": "",
        },
    }


def expect_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaseToolError(f"{path} must be an object")
    return value


def expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise CaseToolError(f"{path} must be a list")
    return value


def expect_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise CaseToolError(f"{path} must be a boolean")
    return value


def expect_string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CaseToolError(f"{path} must be a string")
    if not allow_empty and not value.strip():
        raise CaseToolError(f"{path} must not be empty")
    return value


def validate_case(case: dict[str, Any], *, require_runnable: bool = False) -> None:
    scan_sensitive_values(case)
    if case.get("version") != CASE_VERSION:
        raise CaseToolError(f"unsupported case version for {case.get('id', '<unknown>')}: {case.get('version')!r}")
    case_id = expect_string(case.get("id"), "id")
    status = expect_string(case.get("status"), f"{case_id}.status")
    if status not in CASE_STATUSES:
        raise CaseToolError(f"{case_id}.status must be one of {sorted(CASE_STATUSES)}")
    if require_runnable and status not in RUNNABLE_STATUSES:
        raise CaseToolError(f"{case_id} is {status!r}; only reviewed/active cases are runnable")

    origin = expect_object(case.get("origin"), f"{case_id}.origin")
    if origin.get("type") != "rag-evidence-json":
        raise CaseToolError(f"{case_id}.origin.type must be rag-evidence-json")
    if origin.get("evidenceVersion") != EVIDENCE_VERSION:
        raise CaseToolError(f"{case_id}.origin.evidenceVersion must be {EVIDENCE_VERSION}")

    privacy = expect_object(case.get("privacy"), f"{case_id}.privacy")
    if expect_bool(privacy.get("apiKeyIncluded"), f"{case_id}.privacy.apiKeyIncluded"):
        raise CaseToolError(f"{case_id} must not include API keys")
    if expect_bool(privacy.get("fullKnowledgeChunkIncluded"), f"{case_id}.privacy.fullKnowledgeChunkIncluded"):
        raise CaseToolError(f"{case_id} must not include full knowledge chunks")
    expect_bool(privacy.get("containsUserPrivateText"), f"{case_id}.privacy.containsUserPrivateText")
    expect_bool(privacy.get("safeToCommit"), f"{case_id}.privacy.safeToCommit")
    expect_list(privacy.get("redactions"), f"{case_id}.privacy.redactions")

    corpus = expect_object(case.get("corpus"), f"{case_id}.corpus")
    expect_string(corpus.get("id"), f"{case_id}.corpus.id")
    if corpus.get("sourcePolicy") not in {"synthetic", "public-summary", "user-private-local"}:
        raise CaseToolError(f"{case_id}.corpus.sourcePolicy is invalid")

    expect_string(case.get("query"), f"{case_id}.query")
    expected = expect_object(case.get("expected"), f"{case_id}.expected")
    should_inject = expect_bool(expected.get("shouldInject"), f"{case_id}.expected.shouldInject")
    needs_clarification = expect_bool(expected.get("needsClarification"), f"{case_id}.expected.needsClarification")
    retrieval_mode = expect_string(expected.get("retrievalMode"), f"{case_id}.expected.retrievalMode")
    if retrieval_mode not in RETRIEVAL_MODES:
        raise CaseToolError(f"{case_id}.expected.retrievalMode must be one of {sorted(RETRIEVAL_MODES)}")
    answer_expectation = expect_string(expected.get("answerExpectation"), f"{case_id}.expected.answerExpectation")
    if answer_expectation not in ANSWER_EXPECTATIONS:
        raise CaseToolError(f"{case_id}.expected.answerExpectation must be one of {sorted(ANSWER_EXPECTATIONS)}")
    required_facts = expect_list(expected.get("requiredFacts"), f"{case_id}.expected.requiredFacts")
    forbidden_facts = expect_list(expected.get("forbiddenFacts"), f"{case_id}.expected.forbiddenFacts")
    required_sources = expect_list(expected.get("requiredSourceTitles"), f"{case_id}.expected.requiredSourceTitles")
    expect_list(expected.get("forbiddenSourceTitles"), f"{case_id}.expected.forbiddenSourceTitles")
    for index, text in enumerate([*required_facts, *forbidden_facts, *required_sources]):
        expect_string(text, f"{case_id}.expected.listItem[{index}]")

    if status in RUNNABLE_STATUSES or require_runnable:
        expected_source = expected.get("expectedSourceTitle")
        has_expected_source = isinstance(expected_source, str) and bool(expected_source.strip())
        has_required_sources = any(isinstance(source, str) and source.strip() for source in required_sources)
        if should_inject:
            if not has_expected_source and not has_required_sources:
                raise CaseToolError(f"{case_id} needs expectedSourceTitle or requiredSourceTitles before it can run")
            if answer_expectation in {"fact", "source-identification"} and not required_facts:
                raise CaseToolError(f"{case_id} needs requiredFacts before it can run")
        else:
            if answer_expectation not in {"clarify", "no-answer"}:
                raise CaseToolError(f"{case_id} non-inject case must expect clarify or no-answer")
            if needs_clarification and answer_expectation != "clarify":
                raise CaseToolError(f"{case_id} needsClarification=true must use answerExpectation=clarify")

    evidence = expect_object(case.get("evidence"), f"{case_id}.evidence")
    expect_string(evidence.get("answerExcerpt"), f"{case_id}.evidence.answerExcerpt", allow_empty=True)
    expect_list(evidence.get("hits"), f"{case_id}.evidence.hits")
    expect_object(case.get("review"), f"{case_id}.review")


def validate_cases(cases: list[dict[str, Any]], *, require_runnable: bool = False) -> ValidationSummary:
    statuses: Counter[str] = Counter()
    seen_ids: set[str] = set()
    for case in cases:
        validate_case(case, require_runnable=require_runnable)
        case_id = str(case["id"])
        if case_id in seen_ids:
            raise CaseToolError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)
        statuses[str(case["status"])] += 1
    return ValidationSummary(total=len(cases), statuses=dict(statuses))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value!r}")


def case_missing_fields(case: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    privacy = case.get("privacy") if isinstance(case.get("privacy"), dict) else {}
    status = case.get("status")
    should_inject = expected.get("shouldInject")
    needs_clarification = expected.get("needsClarification")
    answer_expectation = expected.get("answerExpectation")
    retrieval_mode = expected.get("retrievalMode")
    expected_source = expected.get("expectedSourceTitle")
    required_sources = expected.get("requiredSourceTitles") if isinstance(expected.get("requiredSourceTitles"), list) else []
    required_facts = expected.get("requiredFacts") if isinstance(expected.get("requiredFacts"), list) else []

    if status not in CASE_STATUSES:
        missing.append("status")
    if not isinstance(case.get("query"), str) or not case["query"].strip():
        missing.append("query")
    if not isinstance(should_inject, bool):
        missing.append("expected.shouldInject")
    if not isinstance(needs_clarification, bool):
        missing.append("expected.needsClarification")
    if retrieval_mode not in RETRIEVAL_MODES:
        missing.append("expected.retrievalMode")
    if answer_expectation not in ANSWER_EXPECTATIONS:
        missing.append("expected.answerExpectation")
    if should_inject is True:
        has_source = isinstance(expected_source, str) and bool(expected_source.strip())
        has_required_source = any(isinstance(source, str) and source.strip() for source in required_sources)
        if not has_source and not has_required_source:
            missing.append("expected.expectedSourceTitle")
        if answer_expectation in {"fact", "source-identification"} and not any(
            isinstance(fact, str) and fact.strip() for fact in required_facts
        ):
            missing.append("expected.requiredFacts")
    if not isinstance(privacy.get("safeToCommit"), bool):
        missing.append("privacy.safeToCommit")
    if not isinstance(privacy.get("containsUserPrivateText"), bool):
        missing.append("privacy.containsUserPrivateText")
    return missing


def case_is_runnable(case: dict[str, Any]) -> bool:
    try:
        validate_case(case, require_runnable=True)
    except CaseToolError:
        return False
    return case.get("status") in RUNNABLE_STATUSES


def workspace_case_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in WORKSPACE_CASE_DIRS:
        directory = root / dirname
        if directory.exists() and directory.is_dir():
            files.extend(
                child
                for child in sorted(directory.iterdir())
                if child.is_file() and child.suffix.lower() in {".json", ".jsonl"}
            )
    return files


def collect_case_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            raise CaseToolError(f"input path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() not in {".json", ".jsonl"}:
                raise CaseToolError(f"unsupported case file suffix: {path}")
            files.append(path)
            continue
        if any((path / dirname).is_dir() for dirname in WORKSPACE_CASE_DIRS):
            files.extend(workspace_case_files(path))
        else:
            files.extend(
                child
                for child in sorted(path.iterdir())
                if child.is_file() and child.suffix.lower() in {".json", ".jsonl"}
            )
    if not files:
        raise CaseToolError("no case files found")
    return files


def load_case_records_from_inputs(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in collect_case_files(paths):
        records.extend(load_cases_from_path(path))
    return records


def ensure_safe_to_export(cases: list[dict[str, Any]], *, allow_private_local: bool) -> None:
    for case in cases:
        privacy = case.get("privacy") if isinstance(case.get("privacy"), dict) else {}
        if allow_private_local:
            continue
        if privacy.get("safeToCommit") is not True or privacy.get("containsUserPrivateText") is True:
            raise CaseToolError(
                f"{case.get('id', '<unknown>')} is not safe for default export; use --allow-private-local only for ignored local workspaces"
            )


def write_case_records(cases: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".jsonl":
        output.write_text(
            "\n".join(json.dumps(case, ensure_ascii=False, sort_keys=True) for case in cases) + "\n",
            encoding="utf-8",
        )
        return
    payload: Any = cases[0] if len(cases) == 1 else cases
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_single_case(path: Path) -> dict[str, Any]:
    cases = load_cases_from_path(path)
    if len(cases) != 1:
        raise CaseToolError(f"review expects exactly one case in {path}, got {len(cases)}")
    return cases[0]


def set_repeated_list(target: dict[str, Any], key: str, values: list[str] | None) -> None:
    if values is not None:
        target[key] = [value for value in values if value.strip()]


def category_for_failure(failure: str) -> str:
    lowered = failure.lower()
    if not failure:
        return "passed"
    if lowered.startswith("retrieval failed"):
        return "retrieval failed"
    if lowered.startswith("missing required answer text"):
        return "missing required answer text"
    if lowered.startswith("answer leaked forbidden text"):
        return "answer leaked forbidden text"
    if "did not clearly say" in lowered or "insufficient" in lowered or "clarification" in lowered:
        return "answer policy mismatch"
    if any(marker in lowered for marker in ("empty", "timeout", "network", "http", "missing-api-key", "response", "runtime")):
        return "model/runtime error"
    return "other"


def percentage(passed: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(passed / total * 100, 1)


def count_group(results: list[dict[str, Any]], key: str, pass_key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for result in results:
        label = str(result.get(key) or "unknown")
        group = groups.setdefault(label, {"total": 0, "passed": 0, "failed": 0, "passRate": 0.0})
        group["total"] += 1
        if result.get(pass_key) is True:
            group["passed"] += 1
        else:
            group["failed"] += 1
    for group in groups.values():
        group["passRate"] = percentage(int(group["passed"]), int(group["total"]))
    return dict(sorted(groups.items()))


def case_expectation_map(case_file: Path | None) -> tuple[dict[str, str], str | None]:
    if case_file is None:
        return {}, None
    cases = load_cases_from_path(case_file)
    validate_cases(cases, require_runnable=True)
    mapping: dict[str, str] = {}
    corpus_ids: set[str] = set()
    for case in cases:
        mapping[str(case["id"])] = str(case["expected"].get("answerExpectation") or "unknown")
        corpus_ids.add(str(case["corpus"]["id"]))
    corpus_id = next(iter(corpus_ids)) if len(corpus_ids) == 1 else None
    return mapping, corpus_id


def normalize_run_records(raw: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)], {}
    if isinstance(raw, dict):
        results = raw.get("results") if isinstance(raw.get("results"), list) else []
        metadata = {key: value for key, value in raw.items() if key != "results"}
        return [item for item in results if isinstance(item, dict)], metadata
    raise CaseToolError("run input must be a JSON array or an object with results[]")


def build_run_summary(run_path: Path, case_file: Path | None) -> dict[str, Any]:
    raw = read_json_file(run_path)
    scan_sensitive_values(raw)
    results, run_metadata = normalize_run_records(raw)
    expectation_by_case, corpus_from_cases = case_expectation_map(case_file)
    total = len(results)
    retrieval_passed = sum(1 for result in results if result.get("retrieval_passed") is True)
    answer_passed = sum(1 for result in results if result.get("answer_passed") is True)
    enriched_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for result in results:
        case_name = str(result.get("name") or "")
        expectation = expectation_by_case.get(case_name) or str(result.get("expectation") or "unknown")
        failure = str(result.get("failure") or "")
        category = category_for_failure(failure)
        enriched = {**result, "answerExpectation": expectation, "failureCategory": category}
        enriched_results.append(enriched)
        if failure:
            failures.append(
                {
                    "name": case_name,
                    "suite": result.get("suite"),
                    "source": result.get("source"),
                    "answerExpectation": expectation,
                    "failure": truncate_text(failure, 260),
                    "failureCategory": category,
                    "answerExcerpt": truncate_text(result.get("answer"), 180),
                }
            )

    failure_categories: Counter[str] = Counter(item["failureCategory"] for item in failures)
    corpus = run_metadata.get("corpus") or corpus_from_cases
    boundary_note = (
        "This summary describes only the explicit local case file, selected corpus, model/runtime, and run date. "
        "It is not an online accuracy claim and must not be presented as production user accuracy."
    )
    return {
        "version": RUN_SUMMARY_VERSION,
        "createdAt": utc_now_iso(),
        "inputRun": str(run_path),
        "caseFile": str(case_file) if case_file is not None else None,
        "corpus": corpus,
        "caseCount": total,
        "retrievalGate": {
            "passed": retrieval_passed,
            "failed": total - retrieval_passed,
            "total": total,
            "passRate": percentage(retrieval_passed, total),
        },
        "answerCorrectness": {
            "passed": answer_passed,
            "failed": total - answer_passed,
            "total": total,
            "passRate": percentage(answer_passed, total),
        },
        "byExpectation": count_group(enriched_results, "answerExpectation", "answer_passed"),
        "bySourceOrNegativeType": count_group(enriched_results, "source", "answer_passed"),
        "failureCategories": dict(sorted(failure_categories.items())),
        "failures": failures,
        "boundaryNote": boundary_note,
    }


def render_run_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# 所依 RAG Case Run Summary",
        "",
        f"- createdAt: {summary['createdAt']}",
        f"- corpus: {summary.get('corpus') or 'unknown'}",
        f"- case_file: {summary.get('caseFile') or 'not provided'}",
        f"- case_count: {summary['caseCount']}",
        f"- retrieval_gate_pass_rate: {summary['retrievalGate']['passed']}/{summary['retrievalGate']['total']} ({summary['retrievalGate']['passRate']}%)",
        f"- answer_correctness_pass_rate: {summary['answerCorrectness']['passed']}/{summary['answerCorrectness']['total']} ({summary['answerCorrectness']['passRate']}%)",
        "",
        "## By Expectation",
        "",
        "| expectation | total | passed | failed | pass_rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, group in summary["byExpectation"].items():
        lines.append(f"| {label} | {group['total']} | {group['passed']} | {group['failed']} | {group['passRate']}% |")
    lines.extend(
        [
            "",
            "## By Source Or Negative Type",
            "",
            "| source_or_type | total | passed | failed | pass_rate |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, group in summary["bySourceOrNegativeType"].items():
        lines.append(f"| {label} | {group['total']} | {group['passed']} | {group['failed']} | {group['passRate']}% |")
    lines.extend(["", "## Failure Categories", ""])
    if summary["failureCategories"]:
        for label, count in summary["failureCategories"].items():
            lines.append(f"- {label}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Boundary", "", summary["boundaryNote"], ""])
    return "\n".join(lines)


def command_draft(args: argparse.Namespace) -> int:
    evidence_documents = load_evidence_files([Path(value) for value in args.input])
    cases = [
        draft_case_from_evidence(
            evidence,
            corpus_id=args.corpus_id,
            source_policy=args.source_policy,
            corpus_format=args.format,
            fixture_ref=args.fixture_ref,
            collected_from=args.collected_from,
        )
        for _, evidence in evidence_documents
    ]
    validate_cases(cases)
    write_case_records(cases, Path(args.output))
    print(f"drafted {len(cases)} case(s) -> {args.output}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    cases = load_case_records_from_inputs([Path(value) for value in args.input])
    summary = validate_cases(cases, require_runnable=args.require_runnable)
    print(f"validated {summary.total} case(s); statuses={json.dumps(summary.statuses, ensure_ascii=False, sort_keys=True)}")
    return 0


def command_to_jsonl(args: argparse.Namespace) -> int:
    cases = load_case_records_from_inputs([Path(value) for value in args.input])
    validate_cases(cases, require_runnable=True)
    runnable_cases = [case for case in cases if case["status"] in RUNNABLE_STATUSES]
    if len(runnable_cases) != len(cases):
        raise CaseToolError("to-jsonl only accepts reviewed/active cases")
    ensure_safe_to_export(runnable_cases, allow_private_local=args.allow_private_local)
    runnable_cases.sort(key=lambda item: item["id"])
    write_case_records(runnable_cases, Path(args.output))
    print(f"wrote {len(runnable_cases)} reviewed/active case(s) -> {args.output}")
    return 0


def command_workspace_init(args: argparse.Namespace) -> int:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    for dirname in WORKSPACE_DIRS:
        (root / dirname).mkdir(exist_ok=True)
    readme_path = root / "README.md"
    if args.overwrite_readme or not readme_path.exists():
        readme_path.write_text(WORKSPACE_README, encoding="utf-8")
    print(f"initialized workspace -> {root}")
    return 0


def command_workspace_ingest(args: argparse.Namespace) -> int:
    root = Path(args.root)
    drafts_dir = root / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    evidence_documents = load_evidence_files([Path(value) for value in args.input])
    written: list[Path] = []
    skipped: list[Path] = []
    for source_path, evidence in evidence_documents:
        case = draft_case_from_evidence(
            evidence,
            corpus_id=args.corpus_id,
            source_policy=args.source_policy,
            corpus_format=args.format,
            fixture_ref=args.fixture_ref,
            collected_from=args.collected_from,
        )
        output_path = drafts_dir / f"{case['id']}.json"
        if output_path.exists() and not args.overwrite:
            skipped.append(output_path)
            continue
        write_case_records([case], output_path)
        written.append(output_path)
        print(f"drafted {source_path} -> {output_path}")
    print(f"workspace ingest complete: written={len(written)} skipped={len(skipped)}")
    return 0


def summarize_case_records(cases: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    runnable = 0
    safe_to_commit = 0
    private = 0
    missing_by_case: dict[str, list[str]] = {}
    validation_errors: dict[str, str] = {}
    for case in cases:
        case_id = str(case.get("id") or "<missing-id>")
        status_counts[str(case.get("status") or "<missing>")] += 1
        privacy = case.get("privacy") if isinstance(case.get("privacy"), dict) else {}
        if privacy.get("safeToCommit") is True:
            safe_to_commit += 1
        if privacy.get("containsUserPrivateText") is True:
            private += 1
        missing = case_missing_fields(case)
        if missing:
            missing_by_case[case_id] = missing
        try:
            validate_case(case, require_runnable=False)
        except CaseToolError as error:
            validation_errors[case_id] = str(error)
        if case_is_runnable(case):
            runnable += 1
    return {
        "total": len(cases),
        "statuses": dict(sorted(status_counts.items())),
        "runnable": runnable,
        "safeToCommit": safe_to_commit,
        "containsUserPrivateText": private,
        "missingFields": dict(sorted(missing_by_case.items())),
        "validationErrors": dict(sorted(validation_errors.items())),
    }


def print_case_summary_table(summary: dict[str, Any]) -> None:
    print("| metric | value |")
    print("| --- | ---: |")
    print(f"| total | {summary['total']} |")
    print(f"| runnable | {summary['runnable']} |")
    print(f"| safeToCommit | {summary['safeToCommit']} |")
    print(f"| containsUserPrivateText | {summary['containsUserPrivateText']} |")
    for status, count in summary["statuses"].items():
        print(f"| status:{status} | {count} |")
    if summary["missingFields"]:
        print("\n## Missing Fields")
        for case_id, fields in summary["missingFields"].items():
            print(f"- {case_id}: {', '.join(fields)}")
    if summary["validationErrors"]:
        print("\n## Validation Errors")
        for case_id, error in summary["validationErrors"].items():
            print(f"- {case_id}: {error}")


def command_list(args: argparse.Namespace) -> int:
    cases = load_case_records_from_inputs([Path(value) for value in args.input])
    for case in cases:
        scan_sensitive_values(case)
    summary = summarize_case_records(cases)
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_case_summary_table(summary)
    return 0


def command_review(args: argparse.Namespace) -> int:
    case = load_single_case(Path(args.input))
    scan_sensitive_values(case)
    expected = expect_object(case.get("expected"), f"{case.get('id', '<unknown>')}.expected")
    privacy = expect_object(case.get("privacy"), f"{case.get('id', '<unknown>')}.privacy")
    review = expect_object(case.get("review"), f"{case.get('id', '<unknown>')}.review")

    if args.status:
        case["status"] = args.status
    if args.expected_source_title is not None:
        expected["expectedSourceTitle"] = args.expected_source_title or None
        if args.expected_source_title and not args.required_source_title:
            expected["requiredSourceTitles"] = [args.expected_source_title]
    if args.should_inject is not None:
        expected["shouldInject"] = args.should_inject
    if args.needs_clarification is not None:
        expected["needsClarification"] = args.needs_clarification
    if args.retrieval_mode:
        expected["retrievalMode"] = args.retrieval_mode
    if args.answer_expectation:
        expected["answerExpectation"] = args.answer_expectation
    set_repeated_list(expected, "requiredFacts", args.required_fact)
    set_repeated_list(expected, "forbiddenFacts", args.forbidden_fact)
    set_repeated_list(expected, "requiredSourceTitles", args.required_source_title)
    set_repeated_list(expected, "forbiddenSourceTitles", args.forbidden_source_title)
    if expected.get("shouldInject") is False:
        expected["expectedSourceTitle"] = None
        expected["requiredSourceTitles"] = []

    if args.safe_to_commit is not None:
        privacy["safeToCommit"] = args.safe_to_commit
    if args.contains_user_private_text is not None:
        privacy["containsUserPrivateText"] = args.contains_user_private_text
    privacy["apiKeyIncluded"] = False
    privacy["fullKnowledgeChunkIncluded"] = False
    privacy.setdefault("redactions", [])

    if args.reviewed_by is not None:
        review["reviewedBy"] = args.reviewed_by
    if args.notes is not None:
        review["notes"] = args.notes
    if case.get("status") in RUNNABLE_STATUSES:
        review["reviewedAt"] = args.reviewed_at or utc_now_iso()
        origin = expect_object(case.get("origin"), f"{case.get('id', '<unknown>')}.origin")
        origin["redactionStatus"] = args.redaction_status or "reviewed"

    validate_case(case)
    output_path = Path(args.output)
    if output_path.exists() and output_path.resolve() != Path(args.input).resolve() and not args.overwrite:
        raise CaseToolError(f"output exists; pass --overwrite to replace: {output_path}")
    write_case_records([case], output_path)
    print(f"reviewed {case['id']} -> {output_path}")
    return 0


def command_summarize_run(args: argparse.Namespace) -> int:
    case_file = Path(args.case_file) if args.case_file else None
    summary = build_run_summary(Path(args.input), case_file)
    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"summary_json: {output_json}")
    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_run_summary_markdown(summary), encoding="utf-8")
        print(f"summary_md: {output_md}")
    if not args.output_json and not args.output_md:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert suoyi RAG evidence JSON into benchmark case drafts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    workspace_init_parser = subparsers.add_parser("workspace-init", help="Create a local ignored RAG case workspace.")
    workspace_init_parser.add_argument("--root", default=".suoyi-rag-cases")
    workspace_init_parser.add_argument("--overwrite-readme", action="store_true")
    workspace_init_parser.set_defaults(func=command_workspace_init)

    workspace_ingest_parser = subparsers.add_parser("workspace-ingest", help="Convert evidence JSON files into workspace drafts.")
    workspace_ingest_parser.add_argument("--root", default=".suoyi-rag-cases")
    workspace_ingest_parser.add_argument("--input", action="append", required=True, help="Evidence JSON file or directory.")
    workspace_ingest_parser.add_argument("--corpus-id", default="local-private")
    workspace_ingest_parser.add_argument("--source-policy", choices=("synthetic", "public-summary", "user-private-local"), default="user-private-local")
    workspace_ingest_parser.add_argument("--format", default="evidence-json")
    workspace_ingest_parser.add_argument("--fixture-ref", default="")
    workspace_ingest_parser.add_argument("--collected-from", default="workspace-inbox")
    workspace_ingest_parser.add_argument("--overwrite", action="store_true")
    workspace_ingest_parser.set_defaults(func=command_workspace_ingest)

    list_parser = subparsers.add_parser("list", help="List case status and missing-field counts.")
    list_parser.add_argument("--input", action="append", required=True, help="Workspace root, case directory, JSON, or JSONL.")
    list_parser.add_argument("--format", choices=("table", "json"), default="table")
    list_parser.set_defaults(func=command_list)

    review_parser = subparsers.add_parser("review", help="Non-interactively update a draft/reviewed case.")
    review_parser.add_argument("--input", required=True, help="Input case JSON containing exactly one case.")
    review_parser.add_argument("--output", required=True, help="Output case JSON path.")
    review_parser.add_argument("--status", choices=sorted(CASE_STATUSES))
    review_parser.add_argument("--expected-source-title")
    review_parser.add_argument("--required-source-title", action="append")
    review_parser.add_argument("--forbidden-source-title", action="append")
    review_parser.add_argument("--required-fact", action="append")
    review_parser.add_argument("--forbidden-fact", action="append")
    review_parser.add_argument("--answer-expectation", choices=sorted(ANSWER_EXPECTATIONS))
    review_parser.add_argument("--retrieval-mode", choices=sorted(RETRIEVAL_MODES))
    review_parser.add_argument("--should-inject", type=parse_bool)
    review_parser.add_argument("--needs-clarification", type=parse_bool)
    review_parser.add_argument("--safe-to-commit", type=parse_bool)
    review_parser.add_argument("--contains-user-private-text", type=parse_bool)
    review_parser.add_argument("--reviewed-by")
    review_parser.add_argument("--reviewed-at")
    review_parser.add_argument("--redaction-status")
    review_parser.add_argument("--notes")
    review_parser.add_argument("--overwrite", action="store_true")
    review_parser.set_defaults(func=command_review)

    draft_parser = subparsers.add_parser("draft", help="Convert evidence JSON exports into draft benchmark cases.")
    draft_parser.add_argument("--input", action="append", required=True, help="Evidence JSON file or directory of JSON files.")
    draft_parser.add_argument("--output", required=True, help="Output .json or .jsonl path.")
    draft_parser.add_argument("--corpus-id", default="local-private")
    draft_parser.add_argument("--source-policy", choices=("synthetic", "public-summary", "user-private-local"), default="user-private-local")
    draft_parser.add_argument("--format", default="evidence-json")
    draft_parser.add_argument("--fixture-ref", default="")
    draft_parser.add_argument("--collected-from", default="ui-evidence-export")
    draft_parser.set_defaults(func=command_draft)

    validate_parser = subparsers.add_parser("validate", help="Validate benchmark case JSON/JSONL files.")
    validate_parser.add_argument("--input", action="append", required=True, help="Case JSON/JSONL file or directory.")
    validate_parser.add_argument(
        "--require-runnable",
        action="store_true",
        help="Require reviewed/active status and complete expected fields.",
    )
    validate_parser.set_defaults(func=command_validate)

    jsonl_parser = subparsers.add_parser("to-jsonl", help="Merge reviewed/active case JSON files into JSONL.")
    jsonl_parser.add_argument("--input", action="append", required=True, help="Case JSON/JSONL file or directory.")
    jsonl_parser.add_argument("--output", required=True, help="Output JSONL path.")
    jsonl_parser.add_argument(
        "--allow-private-local",
        action="store_true",
        help="Allow safeToCommit=false/private reviewed cases in an ignored local bundle.",
    )
    jsonl_parser.set_defaults(func=command_to_jsonl)

    summary_parser = subparsers.add_parser("summarize-run", help="Summarize rag_answer_benchmark --output-json results.")
    summary_parser.add_argument("--input", required=True, help="Run JSON from rag_answer_benchmark.py --output-json.")
    summary_parser.add_argument("--case-file", default="", help="Optional reviewed/active case JSONL used by the run.")
    summary_parser.add_argument("--output-json", default="")
    summary_parser.add_argument("--output-md", default="")
    summary_parser.set_defaults(func=command_summarize_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CaseToolError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
