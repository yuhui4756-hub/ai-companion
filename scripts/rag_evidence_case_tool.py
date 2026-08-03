from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
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
    cases: list[dict[str, Any]] = []
    for input_path in [Path(value) for value in args.input]:
        cases.extend(load_cases_from_path(input_path))
    summary = validate_cases(cases, require_runnable=args.require_runnable)
    print(f"validated {summary.total} case(s); statuses={json.dumps(summary.statuses, ensure_ascii=False, sort_keys=True)}")
    return 0


def command_to_jsonl(args: argparse.Namespace) -> int:
    cases: list[dict[str, Any]] = []
    for input_path in [Path(value) for value in args.input]:
        cases.extend(load_cases_from_path(input_path))
    validate_cases(cases, require_runnable=True)
    runnable_cases = [case for case in cases if case["status"] in RUNNABLE_STATUSES]
    if len(runnable_cases) != len(cases):
        raise CaseToolError("to-jsonl only accepts reviewed/active cases")
    runnable_cases.sort(key=lambda item: item["id"])
    write_case_records(runnable_cases, Path(args.output))
    print(f"wrote {len(runnable_cases)} reviewed/active case(s) -> {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert suoyi RAG evidence JSON into benchmark case drafts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

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
    jsonl_parser.set_defaults(func=command_to_jsonl)
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
