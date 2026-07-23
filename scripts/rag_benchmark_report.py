from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import warnings
from contextlib import contextmanager
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PILOT_BEFORE_PASSED = 37
PILOT_BEFORE_TOTAL = 48
PILOT_AFTER_PASSED = 48
PILOT_AFTER_TOTAL = 48


@dataclass(frozen=True)
class BenchmarkResult:
    suite: str
    name: str
    source: str
    expectation: str
    passed: bool
    failure: str = ""


def pass_rate(passed: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{passed / total * 100:.1f}%"


def expectation_for(case) -> str:
    if case.should_inject:
        return "inject"
    if case.needs_clarification:
        return "clarify"
    return "no-answer"


def result_for_case(client, case, suite: str, *, runtime: dict | None = None) -> BenchmarkResult:
    from backend.tests.test_rag_realistic_benchmark import evaluate_case

    failure = evaluate_case(client, case, runtime=runtime)
    return BenchmarkResult(
        suite=suite,
        name=case.name,
        source=case.expected_source or expectation_for(case),
        expectation=expectation_for(case),
        passed=failure is None,
        failure=failure or "",
    )


def print_summary_table(title: str, rows: list[tuple[str, int, int]]) -> None:
    print(f"\n## {title}")
    print("| group | total | passed | failed | pass_rate |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for label, total, passed in rows:
        print(f"| {label} | {total} | {passed} | {total - passed} | {pass_rate(passed, total)} |")


def grouped_rows(results: list[BenchmarkResult], key: str) -> list[tuple[str, int, int]]:
    totals: Counter[str] = Counter()
    passed: Counter[str] = Counter()
    for result in results:
        label = getattr(result, key)
        totals[label] += 1
        if result.passed:
            passed[label] += 1
    return [(label, totals[label], passed[label]) for label in sorted(totals)]


@contextmanager
def benchmark_temp_dir():
    path = Path(tempfile.mkdtemp(prefix="suoyi-rag-benchmark-"))
    try:
        yield path
    finally:
        for attempt in range(8):
            try:
                shutil.rmtree(path)
                break
            except PermissionError:
                if attempt == 7:
                    shutil.rmtree(path, ignore_errors=True)
                    break
                time.sleep(0.25)


def run_benchmark() -> list[BenchmarkResult]:
    previous_db_path = os.environ.get("SUOYI_BACKEND_DB_PATH")
    with benchmark_temp_dir() as temp_dir:
        os.environ["SUOYI_BACKEND_DB_PATH"] = str(temp_dir / "rag-benchmark.sqlite")

        warnings.filterwarnings(
            "ignore",
            message="Using `httpx` with `starlette.testclient` is deprecated.*",
        )

        from fastapi.testclient import TestClient

        from backend.tests.test_rag_realistic_benchmark import (
            HYBRID_CASES,
            LEXICAL_CASES,
            REALISTIC_DOCUMENTS,
            app,
            realistic_runtime_config,
            seed_realistic_documents,
        )

        results: list[BenchmarkResult] = []
        runtime = realistic_runtime_config()

        try:
            with TestClient(app) as client:
                seed_realistic_documents(client)
                results.extend(result_for_case(client, case, "lexical/fts") for case in LEXICAL_CASES)

                reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
                if reindex.status_code != 200 or reindex.json().get("failed") != 0:
                    failure = f"hybrid reindex failed: HTTP {reindex.status_code} {reindex.text[:200]}"
                    results.extend(
                        BenchmarkResult(
                            suite="hybrid/mock-embedding",
                            name=case.name,
                            source=case.expected_source or expectation_for(case),
                            expectation=expectation_for(case),
                            passed=False,
                            failure=failure,
                        )
                        for case in HYBRID_CASES
                    )
                else:
                    results.extend(
                        result_for_case(client, case, "hybrid/mock-embedding", runtime=runtime)
                        for case in HYBRID_CASES
                    )
        finally:
            if previous_db_path is None:
                os.environ.pop("SUOYI_BACKEND_DB_PATH", None)
            else:
                os.environ["SUOYI_BACKEND_DB_PATH"] = previous_db_path

        print("# 所依 RAG Benchmark Report")
        print("")
        print("本报告验证的是知识库检索与 prompt 注入是否命中预期资料，不等同于真实大模型最终回答准确率。")
        print(f"- corpus_documents: {len(REALISTIC_DOCUMENTS)}")
        print(
            f"- pilot_before_optimization: {PILOT_BEFORE_PASSED}/{PILOT_BEFORE_TOTAL} "
            f"({pass_rate(PILOT_BEFORE_PASSED, PILOT_BEFORE_TOTAL)})"
        )
        print(
            f"- pilot_after_optimization: {PILOT_AFTER_PASSED}/{PILOT_AFTER_TOTAL} "
            f"({pass_rate(PILOT_AFTER_PASSED, PILOT_AFTER_TOTAL)})"
        )

        total = len(results)
        passed = sum(1 for result in results if result.passed)
        print_summary_table("Current Expanded Benchmark", [("overall", total, passed)])
        print_summary_table("By Suite", grouped_rows(results, "suite"))
        print_summary_table("By Expectation", grouped_rows(results, "expectation"))
        print_summary_table("By Source Or Negative Type", grouped_rows(results, "source"))

        failures = [result for result in results if not result.passed]
        print("\n## Failures")
        if not failures:
            print("None")
        else:
            for result in failures:
                print(f"- {result.suite} / {result.name}: {result.failure}")

        return results


def main() -> int:
    results = run_benchmark()
    return 1 if any(not result.passed for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
