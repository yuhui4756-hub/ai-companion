import sqlite3
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def mock_runtime_config() -> dict:
    return {
        "providerName": "mock",
        "baseURL": "http://127.0.0.1:8765/mock",
        "model": "mock-embedding-h2",
        "dimensions": 48,
        "batchSize": 2,
        "timeoutMs": 3000,
        "enabled": True,
        "apiKey": "sk-embeddinglocaltest",
    }


H2_FIXTURES = [
    {
        "title": "晨星会员方案",
        "sourceType": "markdown",
        "content": """
# 晨星会员方案

## 发布档案
编号：CS-MEMBER-2026
上线窗口：2026-08-20 20:00
预算金额：18.2 万元
负责人：顾遥
说明：老会员续费提醒采用“先确认续费意愿，再给 7 天优惠券”。

## 风险边界
规则：不得把未授权手机号导入知识库。
""".strip(),
    },
    {
        "title": "晨星硬件巡检",
        "sourceType": "markdown",
        "content": """
# 晨星硬件巡检

## 发布档案
编号：CS-HARDWARE-2026
上线窗口：2026-09-12 09:30
预算金额：2.7 万元
负责人：卢川
说明：硬件巡检只覆盖会议室投屏、备用路由器和麦克风。
""".strip(),
    },
    {
        "title": "暮雨咖啡活动",
        "sourceType": "markdown",
        "content": """
# 暮雨咖啡活动

## 活动字段
编号：MY-CAFE-2026
折扣码：MUYU-CAFE-88
负责人：苏晴
截止日期：2026-08-31
说明：折扣码只用于暮雨咖啡活动，不可复用到其他资料。
""".strip(),
    },
    {
        "title": "退款升级 SOP",
        "sourceType": "markdown",
        "content": """
# 退款升级 SOP

## 处理规则
触发条件：用户明确提出退款、退钱或取消订单。
升级码：REFUND-ESC-42
处理动作：先安抚情绪，再核对订单号，然后提交人工复核。
证据来源：只使用用户主动提供的订单截图或订单号。

## 不该做
- 不要要求用户在公开聊天里发送银行卡号。
- 不要把退款凭证写入长期记忆。
""".strip(),
    },
    {
        "title": "风格参考摘录",
        "sourceType": "manual_text",
        "content": "风格参考摘录只说明聊天语气：少命令，多确认，多给用户选择感。它没有预算、负责人或上线窗口。",
    },
]


@dataclass(frozen=True)
class RetrievalCase:
    name: str
    query: str
    expected_source: str | None
    required_text: tuple[str, ...] = ()
    forbidden_text: tuple[str, ...] = ()
    should_inject: bool = True
    needs_clarification: bool = False
    retrieval_mode: str = "auto"


H2_CASES = [
    RetrievalCase(
        name="launch window synonym",
        query="晨星会员方案什么时候上线？",
        expected_source="晨星会员方案",
        required_text=("2026-08-20 20:00",),
        forbidden_text=("2026-09-12 09:30", "卢川"),
    ),
    RetrievalCase(
        name="budget colloquial wording",
        query="晨星会员方案要花多少钱？",
        expected_source="晨星会员方案",
        required_text=("18.2 万元",),
        forbidden_text=("2.7 万元", "晨星硬件巡检"),
    ),
    RetrievalCase(
        name="coupon code field",
        query="暮雨咖啡活动的优惠码是什么？",
        expected_source="暮雨咖啡活动",
        required_text=("MUYU-CAFE-88",),
        forbidden_text=("CS-MEMBER-2026", "CS-HARDWARE-2026"),
    ),
    RetrievalCase(
        name="process wording",
        query="退款时第一步怎么处理？",
        expected_source="退款升级 SOP",
        required_text=("先安抚情绪", "REFUND-ESC-42"),
        forbidden_text=("7 天优惠券", "银行卡号"),
    ),
    RetrievalCase(
        name="ambiguous launch field",
        query="上线窗口是什么？",
        expected_source=None,
        should_inject=False,
        needs_clarification=True,
    ),
    RetrievalCase(
        name="unrelated romance question",
        query="我今天心情不好应该怎么和伴侣聊天？",
        expected_source=None,
        should_inject=False,
        needs_clarification=False,
    ),
]


def seed_h2_sources(client: TestClient) -> dict[str, dict]:
    created: dict[str, dict] = {}
    for payload in H2_FIXTURES:
        response = client.post("/knowledge/sources", json=payload)
        assert response.status_code == 201
        created[payload["title"]] = response.json()
    return created


def assert_retrieval_case(client: TestClient, case: RetrievalCase, *, runtime: dict | None = None) -> None:
    payload: dict = {"query": case.query, "topK": 3, "retrievalMode": case.retrieval_mode}
    if runtime is not None:
        payload["embeddingRuntimeConfig"] = runtime

    response = client.post("/knowledge/search", json=payload)
    assert response.status_code == 200, case.name
    data = response.json()
    prompt_context = data["promptContext"]

    assert data["shouldInject"] is case.should_inject, case.name
    assert data["needsClarification"] is case.needs_clarification, case.name
    if case.expected_source is None:
        assert data["hits"] == [], case.name
        assert prompt_context == "", case.name
        return

    assert data["hits"], case.name
    assert data["hits"][0]["sourceTitle"] == case.expected_source, case.name
    assert case.expected_source in prompt_context, case.name
    for text in case.required_text:
        assert text in prompt_context, f"{case.name}: missing {text}"
    for text in case.forbidden_text:
        assert text not in prompt_context, f"{case.name}: leaked {text}"


def test_h2_retrieval_cases_measure_precision_and_ambiguity(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-h2.sqlite"))

    with TestClient(app) as client:
        seed_h2_sources(client)

        for case in H2_CASES:
            assert_retrieval_case(client, case)


def test_h2_structured_fact_block_keeps_related_fields_together(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "rag-h2.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))

    with TestClient(app) as client:
        seed_h2_sources(client)
        search = client.post("/knowledge/search", json={"query": "晨星会员方案什么时候上线？", "topK": 3})
        assert search.status_code == 200
        assert search.json()["shouldInject"] is True

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT c.heading_path, c.chunk_type, c.content
            FROM knowledge_chunks c
            JOIN knowledge_sources s ON s.id = c.source_id
            WHERE s.title = '晨星会员方案'
            ORDER BY c.chunk_index
            """
        ).fetchall()

    fact_block = next(
        row
        for row in rows
        if row["heading_path"] == "晨星会员方案 / 发布档案" and row["chunk_type"] == "fact_block"
    )
    assert "编号：CS-MEMBER-2026" in fact_block["content"]
    assert "上线窗口：2026-08-20 20:00" in fact_block["content"]
    assert "预算金额：18.2 万元" in fact_block["content"]
    assert "负责人：顾遥" in fact_block["content"]


def test_h2_hybrid_mock_embedding_covers_paraphrased_process_query(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-h2.sqlite"))
    runtime = mock_runtime_config()

    with TestClient(app) as client:
        seed_h2_sources(client)
        reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert reindex.status_code == 200
        assert reindex.json()["indexed"] >= 4

        case = RetrievalCase(
            name="hybrid paraphrased refund flow",
            query="用户要退钱时售后开头要先做什么？",
            expected_source="退款升级 SOP",
            required_text=("先安抚情绪", "核对订单号"),
            forbidden_text=("7 天优惠券",),
            retrieval_mode="hybrid",
        )
        assert_retrieval_case(client, case, runtime=runtime)

        data = client.post(
            "/knowledge/search",
            json={"query": case.query, "topK": 3, "retrievalMode": "hybrid", "embeddingRuntimeConfig": runtime},
        ).json()
        assert data["embeddingReady"] is True
        assert data["mode"] in {"hybrid", "hybrid-fallback"}
