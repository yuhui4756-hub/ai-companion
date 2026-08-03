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
    build_run_summary,
    draft_case_from_evidence,
    load_cases_from_path,
    load_evidence_files,
    validate_cases,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
EVIDENCE_ROOT = FIXTURE_ROOT / "rag_evidence"
CASE_ROOT = FIXTURE_ROOT / "rag_evidence_cases"
SYNTHETIC_CASES = CASE_ROOT / "synthetic_cases.jsonl"
RUN_ROOT = FIXTURE_ROOT / "rag_case_runs"
SYNTHETIC_RUN = RUN_ROOT / "synthetic_run.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_case_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/rag_evidence_case_tool.py", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


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
    validate_result = run_case_tool(
        "validate",
        "--input",
        str(SYNTHETIC_CASES),
        "--require-runnable",
    )
    assert validate_result.returncode == 0, validate_result.stderr
    assert "validated 3 case(s)" in validate_result.stdout

    output_path = tmp_path / "merged.jsonl"
    jsonl_result = run_case_tool(
        "to-jsonl",
        "--input",
        str(SYNTHETIC_CASES),
        "--output",
        str(output_path),
    )
    assert jsonl_result.returncode == 0, jsonl_result.stderr
    assert output_path.exists()
    assert len(output_path.read_text(encoding="utf-8").strip().splitlines()) == 3


def test_workspace_ingest_review_list_and_private_export_gate(tmp_path: Path) -> None:
    workspace = tmp_path / ".suoyi-rag-cases"

    init_result = run_case_tool("workspace-init", "--root", str(workspace))
    assert init_result.returncode == 0, init_result.stderr
    for dirname in ("inbox", "drafts", "reviewed", "active", "archived", "bundles", "runs", "reports"):
        assert (workspace / dirname).is_dir()
    assert (workspace / "README.md").exists()

    ingest_result = run_case_tool(
        "workspace-ingest",
        "--root",
        str(workspace),
        "--input",
        str(EVIDENCE_ROOT),
        "--corpus-id",
        "public-multiformat",
        "--source-policy",
        "public-summary",
        "--format",
        "public-multiformat",
        "--fixture-ref",
        "backend/tests/test_rag_multiformat_public_docs_benchmark.py",
    )
    assert ingest_result.returncode == 0, ingest_result.stderr
    draft_files = sorted((workspace / "drafts").glob("*.json"))
    assert len(draft_files) == 3

    list_result = run_case_tool("list", "--input", str(workspace), "--format", "json")
    assert list_result.returncode == 0, list_result.stderr
    summary = json.loads(list_result.stdout)
    assert summary["total"] == 3
    assert summary["statuses"] == {"draft": 3}
    assert summary["runnable"] == 0
    assert summary["safeToCommit"] == 0
    assert summary["containsUserPrivateText"] == 3

    react_draft = next(
        path
        for path in draft_files
        if load_cases_from_path(path)[0]["expected"]["expectedSourceTitle"] == "React useEffect 多格式摘要"
    )
    reviewed_path = workspace / "reviewed" / react_draft.name
    review_result = run_case_tool(
        "review",
        "--input",
        str(react_draft),
        "--output",
        str(reviewed_path),
        "--status",
        "reviewed",
        "--expected-source-title",
        "React useEffect 多格式摘要",
        "--required-fact",
        "先用旧值运行 cleanup",
        "--required-fact",
        "再用新值运行 setup",
        "--forbidden-fact",
        "VITE_",
        "--answer-expectation",
        "fact",
        "--retrieval-mode",
        "auto",
        "--reviewed-by",
        "pytest",
        "--safe-to-commit",
        "false",
        "--contains-user-private-text",
        "true",
    )
    assert review_result.returncode == 0, review_result.stderr
    reviewed_case = load_cases_from_path(reviewed_path)[0]
    validate_cases([reviewed_case], require_runnable=True)
    assert reviewed_case["privacy"]["safeToCommit"] is False
    assert reviewed_case["privacy"]["containsUserPrivateText"] is True

    bundle_path = workspace / "bundles" / "private.jsonl"
    blocked_export = run_case_tool(
        "to-jsonl",
        "--input",
        str(workspace / "reviewed"),
        "--output",
        str(bundle_path),
    )
    assert blocked_export.returncode == 2
    assert not bundle_path.exists()

    local_export = run_case_tool(
        "to-jsonl",
        "--input",
        str(workspace / "reviewed"),
        "--output",
        str(bundle_path),
        "--allow-private-local",
    )
    assert local_export.returncode == 0, local_export.stderr
    assert len(bundle_path.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_summarize_run_outputs_metrics_and_boundary(tmp_path: Path) -> None:
    summary = build_run_summary(SYNTHETIC_RUN, SYNTHETIC_CASES)

    assert summary["version"] == "suoyi-rag-run-summary-v1"
    assert summary["caseCount"] == 3
    assert summary["corpus"] == "public-multiformat"
    assert summary["retrievalGate"]["passRate"] == 100.0
    assert summary["answerCorrectness"]["passRate"] == 33.3
    assert summary["byExpectation"]["fact"]["total"] == 2
    assert summary["byExpectation"]["clarify"]["total"] == 1
    assert summary["failureCategories"]["missing required answer text"] == 1
    assert "not an online accuracy claim" in summary["boundaryNote"]

    output_json = tmp_path / "summary.json"
    output_md = tmp_path / "summary.md"
    cli_result = run_case_tool(
        "summarize-run",
        "--input",
        str(SYNTHETIC_RUN),
        "--case-file",
        str(SYNTHETIC_CASES),
        "--output-json",
        str(output_json),
        "--output-md",
        str(output_md),
    )
    assert cli_result.returncode == 0, cli_result.stderr
    written = json.loads(output_json.read_text(encoding="utf-8"))
    assert written["answerCorrectness"]["passed"] == 1
    assert "retrieval_gate_pass_rate: 3/3 (100.0%)" in output_md.read_text(encoding="utf-8")
