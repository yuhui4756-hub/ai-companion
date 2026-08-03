from __future__ import annotations

from pathlib import Path
from typing import Iterable

from backend.tests.test_rag_realistic_benchmark import BenchmarkCase
from scripts.rag_evidence_case_tool import RUNNABLE_STATUSES, CaseToolError, load_cases_from_path, validate_case


def load_benchmark_cases(
    path: str | Path,
    *,
    corpus_id: str | None = None,
    allowed_statuses: Iterable[str] = RUNNABLE_STATUSES,
) -> list[BenchmarkCase]:
    allowed = set(allowed_statuses)
    records = load_cases_from_path(Path(path))
    cases: list[BenchmarkCase] = []
    for record in records:
        validate_case(record, require_runnable=True)
        status = str(record["status"])
        if status not in allowed:
            raise CaseToolError(f"{record['id']} is {status!r}; expected one of {sorted(allowed)}")
        record_corpus_id = str(record["corpus"]["id"])
        if corpus_id is not None and record_corpus_id != corpus_id:
            raise CaseToolError(f"{record['id']} belongs to corpus {record_corpus_id!r}, not {corpus_id!r}")
        expected = record["expected"]
        expected_source = expected.get("expectedSourceTitle")
        required_sources = expected.get("requiredSourceTitles") or []
        if not (isinstance(expected_source, str) and expected_source.strip()):
            expected_source = next((str(source) for source in required_sources if str(source).strip()), None)
        if not expected.get("shouldInject"):
            expected_source = None
        needs_clarification = expected.get("needsClarification")
        cases.append(
            BenchmarkCase(
                name=str(record["id"]),
                query=str(record["query"]),
                expected_source=expected_source,
                required_text=tuple(str(item) for item in expected.get("requiredFacts") or []),
                forbidden_text=tuple(str(item) for item in expected.get("forbiddenFacts") or []),
                should_inject=bool(expected.get("shouldInject")),
                needs_clarification=needs_clarification if isinstance(needs_clarification, bool) else None,
                retrieval_mode=str(expected.get("retrievalMode") or "auto"),
            )
        )
    return cases
