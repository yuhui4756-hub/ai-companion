from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.test_document_parsing import make_docx_bytes, make_text_pdf


def multiformat_runtime_config() -> dict:
    return {
        "providerName": "mock",
        "baseURL": "http://127.0.0.1:8765/mock",
        "model": "mock-embedding-multiformat",
        "dimensions": 64,
        "batchSize": 4,
        "timeoutMs": 3000,
        "enabled": True,
        "apiKey": "mock-local-key",
    }


def seed_multiformat_sources(client: TestClient) -> dict[str, dict]:
    created: dict[str, dict] = {}

    pdf = client.post(
        "/knowledge/import/file",
        files={
            "file": (
                "星蓝计划.pdf",
                make_text_pdf(
                    [
                        "XLP-2026-041 Budget: 12.8 wan Owner: XuNian",
                        "Deadline: 2026-08-15. This source verifies PDF text-layer import.",
                    ]
                ),
                "application/pdf",
            )
        },
    )
    assert pdf.status_code == 201
    created["星蓝计划"] = pdf.json()

    docx = client.post(
        "/knowledge/import/file",
        files={
            "file": (
                "月澜活动.docx",
                make_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert docx.status_code == 201
    created["月澜活动"] = docx.json()

    markdown = client.post(
        "/knowledge/import/file",
        files={
            "file": (
                "松果客服规范.md",
                """
# 松果客服规范

## 服务字段
编号：SG-SERVICE-17
负责人：周衡
截止日期：2026-07-30
规则：客服回复先确认用户问题，再给出下一步操作。
""".strip().encode("utf-8"),
                "text/markdown",
            )
        },
    )
    assert markdown.status_code == 201
    created["松果客服规范"] = markdown.json()

    text = client.post(
        "/knowledge/import/file",
        files={
            "file": (
                "北桥设备清单.txt",
                "北桥设备清单包含笔记本、麦克风和备用路由器。保管人：陈序。位置：B2 储物柜。".encode("utf-8"),
                "text/plain",
            )
        },
    )
    assert text.status_code == 201
    created["北桥设备清单"] = text.json()

    return created


def test_multiformat_imported_documents_retrieve_precisely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-multiformat.sqlite"))

    with TestClient(app) as client:
        seed_multiformat_sources(client)

        by_pdf_id = client.post("/knowledge/search", json={"query": "XLP-2026-041 是哪份资料？", "topK": 3})
        assert by_pdf_id.status_code == 200
        pdf_data = by_pdf_id.json()
        assert pdf_data["shouldInject"] is True
        assert pdf_data["hits"][0]["sourceTitle"] == "星蓝计划"
        assert "12.8 wan" in pdf_data["promptContext"]

        pdf_budget = client.post("/knowledge/search", json={"query": "星蓝计划 Budget 是多少？", "topK": 3})
        assert pdf_budget.status_code == 200
        budget_data = pdf_budget.json()
        assert budget_data["shouldInject"] is True
        assert {hit["sourceTitle"] for hit in budget_data["hits"]} == {"星蓝计划"}
        assert "12.8 wan" in budget_data["promptContext"]
        assert "3.4 万元" not in budget_data["promptContext"]
        assert "周衡" not in budget_data["promptContext"]

        docx_owner = client.post("/knowledge/search", json={"query": "月澜活动负责人是谁？", "topK": 3})
        assert docx_owner.status_code == 200
        owner_data = docx_owner.json()
        assert owner_data["shouldInject"] is True
        assert {hit["sourceTitle"] for hit in owner_data["hits"]} == {"月澜活动"}
        assert "林澈" in owner_data["promptContext"]
        assert "XuNian" not in owner_data["promptContext"]
        assert "周衡" not in owner_data["promptContext"]


def test_multiformat_generic_and_unrelated_queries_do_not_inject(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-multiformat.sqlite"))

    with TestClient(app) as client:
        seed_multiformat_sources(client)

        generic_budget = client.post("/knowledge/search", json={"query": "预算是多少？", "topK": 3})
        assert generic_budget.status_code == 200
        assert generic_budget.json()["hits"] == []
        assert generic_budget.json()["promptContext"] == ""
        assert generic_budget.json()["shouldInject"] is False
        assert generic_budget.json()["needsClarification"] is True

        generic_owner = client.post("/knowledge/search", json={"query": "负责人是谁？", "topK": 3})
        assert generic_owner.status_code == 200
        assert generic_owner.json()["hits"] == []
        assert generic_owner.json()["promptContext"] == ""

        unrelated = client.post("/knowledge/search", json={"query": "晚饭吃什么比较好？", "topK": 3})
        assert unrelated.status_code == 200
        assert unrelated.json()["hits"] == []
        assert unrelated.json()["promptContext"] == ""


def test_multiformat_duplicate_and_soft_delete_do_not_break_existing_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-multiformat.sqlite"))
    docx_bytes = make_docx_bytes()

    with TestClient(app) as client:
        created = seed_multiformat_sources(client)
        duplicate = client.post(
            "/knowledge/import/file",
            files={
                "file": (
                    "月澜活动.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert duplicate.status_code == 409

        before_delete = client.post("/knowledge/search", json={"query": "月澜活动负责人是谁？", "topK": 3})
        assert before_delete.status_code == 200
        assert before_delete.json()["shouldInject"] is True

        deleted = client.delete(f"/knowledge/sources/{created['月澜活动']['id']}")
        assert deleted.status_code == 200

        after_delete = client.post("/knowledge/search", json={"query": "月澜活动负责人是谁？", "topK": 3})
        assert after_delete.status_code == 200
        assert after_delete.json()["hits"] == []
        assert after_delete.json()["promptContext"] == ""
        assert after_delete.json()["shouldInject"] is False


def test_multiformat_hybrid_mock_embeddings_respect_file_import_and_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-multiformat.sqlite"))
    runtime = multiformat_runtime_config()

    with TestClient(app) as client:
        created = seed_multiformat_sources(client)
        reindex = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert reindex.status_code == 200
        assert reindex.json()["failed"] == 0
        assert reindex.json()["indexed"] >= 4

        hybrid = client.post(
            "/knowledge/search",
            json={
                "query": "moon-event YL-2026-009 的预算金额",
                "topK": 3,
                "retrievalMode": "hybrid",
                "embeddingRuntimeConfig": runtime,
            },
        )
        assert hybrid.status_code == 200
        hybrid_data = hybrid.json()
        assert hybrid_data["shouldInject"] is True
        assert hybrid_data["embeddingUsed"] is True
        assert hybrid_data["hits"][0]["sourceTitle"] == "月澜活动"
        assert "3.4 万元" in hybrid_data["promptContext"]

        deleted = client.delete(f"/knowledge/sources/{created['月澜活动']['id']}")
        assert deleted.status_code == 200
        after_delete = client.post(
            "/knowledge/search",
            json={
                "query": "moon-event YL-2026-009 的预算金额",
                "topK": 3,
                "retrievalMode": "hybrid",
                "embeddingRuntimeConfig": runtime,
            },
        )
        assert after_delete.status_code == 200
        assert after_delete.json()["hits"] == []
        assert after_delete.json()["promptContext"] == ""
