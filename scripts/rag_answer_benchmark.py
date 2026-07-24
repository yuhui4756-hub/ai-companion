from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_CHAT_MODEL = "deepseek-r1:1.5b"
DEFAULT_EMBEDDING_MODEL = "bge-m3"
DEFAULT_EMBEDDING_DIMENSIONS = 1024

INSUFFICIENT_MARKERS = (
    "资料不足",
    "没有足够",
    "无法确定",
    "不能确定",
    "没有找到",
    "未找到",
    "不清楚",
    "请指定",
    "需要指定",
    "哪份资料",
)


@dataclass(frozen=True)
class AnswerResult:
    suite: str
    name: str
    expectation: str
    source: str
    retrieval_passed: bool
    answer_passed: bool
    failure: str = ""
    answer: str = ""
    elapsed_seconds: float = 0.0


def pass_rate(passed: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{passed / total * 100:.1f}%"


def expectation_for(case: Any) -> str:
    if case.should_inject:
        return "inject"
    if case.needs_clarification:
        return "clarify"
    return "no-answer"


def normalize_for_match(value: str) -> str:
    normalized = value.lower()
    normalized = re.sub(
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        lambda match: f"{match.group(1)}{int(match.group(2)):02d}{int(match.group(3)):02d}",
        normalized,
    )
    normalized = re.sub(
        r"(\d{4})年(\d{1,2})月(\d{1,2})日?",
        lambda match: f"{match.group(1)}{int(match.group(2)):02d}{int(match.group(3)):02d}",
        normalized,
    )
    return re.sub(r"\s+", "", normalized)


def strip_reasoning(raw_answer: str) -> str:
    without_closed_thoughts = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.IGNORECASE | re.DOTALL)
    if "<think>" in without_closed_thoughts.lower():
        parts = re.split(r"</?think>", without_closed_thoughts, flags=re.IGNORECASE)
        return (parts[-1] if parts else without_closed_thoughts).strip()
    return without_closed_thoughts.strip()


def answer_has_insufficient_marker(answer: str) -> bool:
    compact = normalize_for_match(answer)
    return any(normalize_for_match(marker) in compact for marker in INSUFFICIENT_MARKERS)


def grade_answer(case: Any, answer: str) -> str | None:
    compact_answer = normalize_for_match(answer)
    if case.expected_source is None:
        if answer_has_insufficient_marker(answer):
            return None
        return "answer did not clearly say the knowledge base is insufficient or needs clarification"

    missing = [text for text in case.required_text if normalize_for_match(text) not in compact_answer]
    if missing and is_source_identification_answer(case, answer, missing):
        missing = []
    if missing:
        return f"missing required answer text {missing!r}"
    leaked = [text for text in case.forbidden_text if normalize_for_match(text) in compact_answer]
    if leaked:
        return f"answer leaked forbidden text {leaked!r}"
    return None


def is_source_identification_answer(case: Any, answer: str, missing: list[str]) -> bool:
    if not case.expected_source:
        return False
    compact_query = normalize_for_match(case.query)
    source_question = any(marker in compact_query for marker in ("是哪份资料", "对应哪份资料", "哪份资料", "哪份清单", "哪份规范", "哪份说明"))
    missing_from_query = all(normalize_for_match(text) in compact_query for text in missing)
    return source_question and missing_from_query and normalize_for_match(case.expected_source) in normalize_for_match(answer)


def grouped_rows(results: list[AnswerResult], key: str) -> list[tuple[str, int, int]]:
    totals: Counter[str] = Counter()
    passed: Counter[str] = Counter()
    for result in results:
        label = getattr(result, key)
        totals[label] += 1
        if result.answer_passed:
            passed[label] += 1
    return [(label, totals[label], passed[label]) for label in sorted(totals)]


def print_summary_table(title: str, rows: list[tuple[str, int, int]]) -> None:
    print(f"\n## {title}")
    print("| group | total | passed | failed | pass_rate |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for label, total, passed in rows:
        print(f"| {label} | {total} | {passed} | {total - passed} | {pass_rate(passed, total)} |")


@contextmanager
def benchmark_temp_dir():
    path = Path(tempfile.mkdtemp(prefix="suoyi-rag-answer-benchmark-"))
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


def ollama_json(base_url: str, path: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"ollama-http-{error.code}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("ollama-network-error") from error


def call_ollama_chat(
    *,
    base_url: str,
    model: str,
    query: str,
    prompt_context: str,
    timeout_seconds: int,
    num_predict: int,
) -> str:
    system_prompt = (
        "你是所依知识库端到端评测助手。只能根据用户导入资料回答。"
        "如果没有用户导入资料，或资料没有答案，或问题没有指定清楚资料来源，就回答“资料不足，需要补充或指定资料”。"
        "不要编造，不要使用资料外常识。回答尽量简短，保留原始编号、日期、金额、人名、位置和代码。"
    )
    user_prompt = "\n\n".join(
        [
            f"用户问题：{query}",
            f"用户导入资料：\n{prompt_context}" if prompt_context else "用户导入资料：无",
            "请直接给出答案。",
        ]
    )
    data = ollama_json(
        base_url,
        "/api/chat",
        {
            "model": model,
            "stream": False,
            "think": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": 0,
                "top_p": 0.9,
                "num_predict": num_predict,
            },
        },
        timeout_seconds,
    )
    message = data.get("message")
    content = message.get("content") if isinstance(message, dict) else ""
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("ollama-empty-chat-response")
    return strip_reasoning(content)


def select_cases(all_cases: list[tuple[str, Any]], limit: int | None) -> list[tuple[str, Any]]:
    if limit is None or limit >= len(all_cases):
        return all_cases

    selected: list[tuple[str, Any]] = []
    buckets: dict[str, list[tuple[str, Any]]] = {"hybrid": [], "clarify": [], "no-answer": [], "inject": []}
    for suite, case in all_cases:
        if suite.startswith("hybrid"):
            buckets["hybrid"].append((suite, case))
        elif case.needs_clarification:
            buckets["clarify"].append((suite, case))
        elif not case.should_inject:
            buckets["no-answer"].append((suite, case))
        else:
            buckets["inject"].append((suite, case))

    preferred_order = ["hybrid", "clarify", "no-answer", "inject"]
    while len(selected) < limit and any(buckets.values()):
        for bucket_name in preferred_order:
            if len(selected) >= limit:
                break
            if buckets[bucket_name]:
                selected.append(buckets[bucket_name].pop(0))
    return selected


def run_answer_benchmark(args: argparse.Namespace) -> list[AnswerResult]:
    previous_db_path = os.environ.get("SUOYI_BACKEND_DB_PATH")
    with benchmark_temp_dir() as temp_dir:
        os.environ["SUOYI_BACKEND_DB_PATH"] = str(temp_dir / "rag-answer-benchmark.sqlite")

        from fastapi.testclient import TestClient

        from backend.tests.test_rag_realistic_benchmark import (
            BENCHMARK_DOCUMENTS,
            HYBRID_CASES,
            LEXICAL_CASES,
            app,
            evaluate_case,
            seed_realistic_documents,
        )

        embedding_runtime = {
            "providerName": "ollama",
            "baseURL": f"{args.ollama_base_url.rstrip('/')}/api",
            "model": args.embedding_model,
            "dimensions": args.embedding_dimensions,
            "batchSize": args.embedding_batch_size,
            "timeoutMs": args.embedding_timeout_seconds * 1000,
            "enabled": True,
            "apiKey": "",
        }
        all_cases = [("lexical/fts+ollama-auto", case) for case in LEXICAL_CASES]
        all_cases.extend(("hybrid/ollama-bge-m3", case) for case in HYBRID_CASES)
        selected_cases = select_cases(all_cases, args.limit)

        results: list[AnswerResult] = []
        try:
            with TestClient(app) as client:
                seed_realistic_documents(client)
                health = client.post("/embedding/health/check", json={"runtimeConfig": embedding_runtime})
                reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": embedding_runtime})
                print("# 所依 RAG Answer Benchmark")
                print("")
                print("本报告验证的是“检索片段注入后，本地聊天模型能否答出关键事实”，不等同于线上真实用户准确率。")
                print(f"- corpus_documents: {len(BENCHMARK_DOCUMENTS)}")
                print(f"- selected_cases: {len(selected_cases)}/{len(all_cases)}")
                print(f"- chat_model: {args.chat_model}")
                print(f"- embedding_model: {args.embedding_model}")
                print(f"- embedding_health: HTTP {health.status_code} {health.json()}")
                print(f"- embedding_reindex: HTTP {reindex.status_code} {reindex.json()}")
                if health.status_code != 200 or not health.json().get("ok"):
                    raise RuntimeError("embedding health check failed")
                if reindex.status_code != 200 or reindex.json().get("failed"):
                    raise RuntimeError("embedding reindex failed")

                for index, (suite, case) in enumerate(selected_cases, start=1):
                    started = time.time()
                    expectation = expectation_for(case)
                    retrieval_failure = evaluate_case(client, case, runtime=embedding_runtime)
                    search = client.post(
                        "/knowledge/search",
                        json={
                            "query": case.query,
                            "topK": 3,
                            "retrievalMode": case.retrieval_mode,
                            "embeddingRuntimeConfig": embedding_runtime,
                        },
                    )
                    search_data = search.json() if search.status_code == 200 else {}
                    answer = ""
                    failure = ""
                    if retrieval_failure:
                        failure = f"retrieval failed: {retrieval_failure}"
                    else:
                        try:
                            answer = call_ollama_chat(
                                base_url=args.ollama_base_url,
                                model=args.chat_model,
                                query=case.query,
                                prompt_context=search_data.get("promptContext", ""),
                                timeout_seconds=args.chat_timeout_seconds,
                                num_predict=args.num_predict,
                            )
                            failure = grade_answer(case, answer) or ""
                        except RuntimeError as error:
                            failure = str(error)

                    result = AnswerResult(
                        suite=suite,
                        name=case.name,
                        expectation=expectation,
                        source=case.expected_source or expectation,
                        retrieval_passed=retrieval_failure is None,
                        answer_passed=failure == "",
                        failure=failure,
                        answer=answer,
                        elapsed_seconds=time.time() - started,
                    )
                    results.append(result)
                    status = "PASS" if result.answer_passed else "FAIL"
                    print(f"[{index}/{len(selected_cases)}] {status} {suite} / {case.name} ({result.elapsed_seconds:.1f}s)", flush=True)
        finally:
            if previous_db_path is None:
                os.environ.pop("SUOYI_BACKEND_DB_PATH", None)
            else:
                os.environ["SUOYI_BACKEND_DB_PATH"] = previous_db_path

        total = len(results)
        passed = sum(1 for result in results if result.answer_passed)
        retrieval_passed = sum(1 for result in results if result.retrieval_passed)
        print_summary_table("Answer Correctness", [("overall", total, passed)])
        print_summary_table("Retrieval Gate", [("overall", total, retrieval_passed)])
        print_summary_table("By Suite", grouped_rows(results, "suite"))
        print_summary_table("By Expectation", grouped_rows(results, "expectation"))
        print_summary_table("By Source Or Negative Type", grouped_rows(results, "source"))

        failures = [result for result in results if not result.answer_passed]
        print("\n## Failures")
        if not failures:
            print("None")
        else:
            for result in failures[: args.max_failures]:
                answer_preview = result.answer.replace("\n", " ")[:240]
                print(f"- {result.suite} / {result.name}: {result.failure}; answer={answer_preview!r}")
            if len(failures) > args.max_failures:
                print(f"- ... {len(failures) - args.max_failures} more failures omitted")

        if args.output_json:
            output_path = Path(args.output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\n- output_json: {output_path}")

        return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local end-to-end RAG answer benchmark through Ollama chat.")
    parser.add_argument("--ollama-base-url", default=DEFAULT_OLLAMA_BASE_URL)
    parser.add_argument("--chat-model", default=DEFAULT_CHAT_MODEL)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--embedding-dimensions", type=int, default=DEFAULT_EMBEDDING_DIMENSIONS)
    parser.add_argument("--embedding-batch-size", type=int, default=4)
    parser.add_argument("--embedding-timeout-seconds", type=int, default=30)
    parser.add_argument("--chat-timeout-seconds", type=int, default=90)
    parser.add_argument("--num-predict", type=int, default=160)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-failures", type=int, default=20)
    parser.add_argument("--output-json", default="")
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Exit with code 0 even when some answer cases fail; useful for exploratory model baselines.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = run_answer_benchmark(args)
    if args.allow_failures:
        return 0
    return 1 if any(not result.answer_passed for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
