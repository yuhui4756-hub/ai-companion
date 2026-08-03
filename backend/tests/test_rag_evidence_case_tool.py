from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.tests.rag_case_loader import load_benchmark_cases
from scripts.rag_answer_benchmark import select_cases
from scripts.rag_evidence_case_tool import (
    CaseToolError,
    draft_case_from_evidence,
    load_cases_from_path,
    load_evidence_files,
    validate_cases,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
EVIDENCE_ROOT = FIXTURE_ROOT / "rag_evidence"
CASE_ROOT = FIXTURE_ROOT / "rag_evidence_cases"
SYNTHETIC_CASES = CASE_ROOT / "synthetic_cases.jsonl"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_draft_case_from_evidence_defaults_to_private_unreviewed() -> None:
    evidence = read_json(EVIDENCE_ROOT / "synthetic_evidence_react_cleanup.json")

    case = draft_case_from_evidence(
        evidence,
        corpus_id="public-multiformat",
        source_policy="public-summary",
        corpus_format="public-multiformat",
        fixture_ref="backend/tests/test_rag_multiformat_public_docs_benchmark.py",
        collected_from="pytest-fixture",
    )

    validate_cases([case])
    assert case["version"] == "suoyi-rag-benchmark-case-v1"
    assert case["status"] == "draft"
    assert case["privacy"]["safeToCommit"] is False
    assert case["privacy"]["containsUserPrivateText"] is True
    assert case["expected"]["expectedSourceTitle"] == "React useEffect 多格式摘要"
    assert case["expected"]["requiredFacts"] == []
    assert case["expected"]["retrievalMode"] == "auto"
    assert case["evidence"]["hits"][0]["metadata"]["sourceFormat"] == "markdown"
    assert len(case["evidence"]["hits"][0]["contentExcerpt"]) <= 243


def test_hybrid_evidence_maps_to_hybrid_retrieval_mode() -> None:
    evidence = read_json(EVIDENCE_ROOT / "synthetic_evidence_fetch_hybrid.json")

    case = draft_case_from_evidence(
        evidence,
        corpus_id="public-multiformat",
        source_policy="public-summary",
        corpus_format="public-multiformat",
        fixture_ref="backend/tests/test_rag_multiformat_public_docs_benchmark.py",
        collected_from="pytest-fixture",
    )

    assert case["expected"]["retrievalMode"] == "hybrid"
    assert case["evidence"]["traceSummary"]["embeddingUsed"] is True


def test_secret_like_evidence_is_rejected_without_echoing_value(tmp_path: Path) -> None:
    evidence = read_json(EVIDENCE_ROOT / "synthetic_evidence_generic_clarify.json")
    fake_secret = "sk-" + "test-secret-value"
    evidence["answer"]["content"] = f"debug key {fake_secret}"
    evidence_path = tmp_path / "bad-evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(CaseToolError) as error:
        load_evidence_files([evidence_path])

    message = str(error.value)
    assert "sensitive" in message
    assert fake_secret not in message


def test_validate_synthetic_reviewed_cases_and_load_benchmark_cases() -> None:
    cases = load_cases_from_path(SYNTHETIC_CASES)

    summary = validate_cases(cases, require_runnable=True)
    loaded = load_benchmark_cases(SYNTHETIC_CASES, corpus_id="public-multiformat")
    selected = select_cases(
        [("public-multiformat/case-file", case) for case in loaded],
        limit=1,
        case_names="evidence-20260803-react-cleanup-001",
    )

    assert summary.total == 3
    assert summary.statuses["active"] == 2
    assert summary.statuses["reviewed"] == 1
    assert [case.name for case in loaded] == [
        "evidence-20260803-react-cleanup-001",
        "evidence-20260803-generic-base-url-001",
        "evidence-20260803-fetch-http-001",
    ]
    assert loaded[0].expected_source == "React useEffect 多格式摘要"
    assert loaded[1].should_inject is False
    assert loaded[1].needs_clarification is True
    assert loaded[2].retrieval_mode == "hybrid"
    assert selected[0][1].name == "evidence-20260803-react-cleanup-001"


def test_loader_rejects_draft_cases_by_default(tmp_path: Path) -> None:
    evidence = read_json(EVIDENCE_ROOT / "synthetic_evidence_react_cleanup.json")
    case = draft_case_from_evidence(
        evidence,
        corpus_id="public-multiformat",
        source_policy="public-summary",
        corpus_format="public-multiformat",
        fixture_ref="backend/tests/test_rag_multiformat_public_docs_benchmark.py",
        collected_from="pytest-fixture",
    )
    case_path = tmp_path / "draft-case.json"
    case_path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(CaseToolError):
        load_benchmark_cases(case_path, corpus_id="public-multiformat")


def test_cli_validate_and_to_jsonl(tmp_path: Path) -> None:
    validate_result = subprocess.run(
        [
            sys.executable,
            "scripts/rag_evidence_case_tool.py",
            "validate",
            "--input",
            str(SYNTHETIC_CASES),
            "--require-runnable",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )
    assert validate_result.returncode == 0, validate_result.stderr
    assert "validated 3 case(s)" in validate_result.stdout

    output_path = tmp_path / "merged.jsonl"
    jsonl_result = subprocess.run(
        [
            sys.executable,
            "scripts/rag_evidence_case_tool.py",
            "to-jsonl",
            "--input",
            str(SYNTHETIC_CASES),
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )
    assert jsonl_result.returncode == 0, jsonl_result.stderr
    assert output_path.exists()
    assert len(output_path.read_text(encoding="utf-8").strip().splitlines()) == 3
