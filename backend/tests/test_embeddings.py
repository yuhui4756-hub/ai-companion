import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

import backend.app.embeddings as embeddings
from backend.app.main import app


def fake_embedding_key() -> str:
    return "sk-" + "embeddinglocaltest"


def mock_runtime_config(*, enabled: bool = True, dimensions: int = 32, model: str = "mock-embedding") -> dict:
    return {
        "providerName": "mock",
        "baseURL": "http://127.0.0.1:8765/mock",
        "model": model,
        "dimensions": dimensions,
        "batchSize": 2,
        "timeoutMs": 3000,
        "enabled": enabled,
        "apiKey": fake_embedding_key(),
    }


def seed_embedding_sources(client: TestClient) -> dict[str, dict]:
    payloads = [
        {
            "title": "星蓝计划",
            "sourceType": "manual_text",
            "content": "\n".join(
                [
                    "编号：XLP-2026-041",
                    "预算金额：12.8 万元",
                    "负责人：许念",
                    "说明：星蓝计划用于验证明确编号和本地检索。",
                ]
            ),
        },
        {
            "title": "松果客服规范",
            "sourceType": "manual_text",
            "content": "规则：客服回复要先确认用户问题，再给出下一步操作。升级前先记录工单背景。",
        },
    ]
    created: dict[str, dict] = {}
    for payload in payloads:
        response = client.post("/knowledge/sources", json=payload)
        assert response.status_code == 201
        created[payload["title"]] = response.json()
    return created


def test_embedding_config_is_disabled_by_default_and_never_returns_key(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "embedding.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))

    with TestClient(app) as client:
        seed_embedding_sources(client)

        config = client.get("/embedding/config")
        assert config.status_code == 200
        data = config.json()
        assert data["enabled"] is False
        assert data["apiKeyRef"] == "renderer-localStorage"
        assert "apiKey" not in data

        search = client.post("/knowledge/search", json={"query": "星蓝计划是什么", "retrievalMode": "auto"})
        assert search.status_code == 200
        search_data = search.json()
        assert search_data["embeddingUsed"] is False
        assert search_data["embeddingReady"] is False
        assert search_data["shouldInject"] is True


def test_embedding_config_persists_only_non_secret_fields(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "embedding.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))
    fake_key = fake_embedding_key()

    with TestClient(app) as client:
        response = client.put(
            "/embedding/config",
            json={
                "providerName": "mock",
                "baseURL": "https://example.test/v1?api_key=should-not-store",
                "model": "mock-embedding",
                "dimensions": 32,
                "batchSize": 4,
                "timeoutMs": 3000,
                "enabled": True,
                "apiKey": fake_key,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["baseURL"] == "https://example.test/v1"
        assert "apiKey" not in data

    with sqlite3.connect(db_path) as connection:
        database_text = "\n".join(
            " ".join(str(value) for value in row)
            for table in ["embedding_provider_configs", "knowledge_embeddings"]
            for row in connection.execute(f"SELECT * FROM {table}").fetchall()
        )
    assert fake_key not in database_text
    assert "should-not-store" not in database_text


def test_mock_embedding_health_reindex_is_idempotent_and_hybrid_finds_semantic_match(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "embedding.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))
    runtime = mock_runtime_config()

    with TestClient(app) as client:
        seed_embedding_sources(client)

        health = client.post("/embedding/health/check", json={"runtimeConfig": runtime})
        assert health.status_code == 200
        assert health.json()["ok"] is True
        assert health.json()["dimensions"] == runtime["dimensions"]

        first = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert first.status_code == 200
        first_data = first.json()
        assert first_data["indexed"] >= 2
        assert first_data["failed"] == 0

        second = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert second.status_code == 200
        second_data = second.json()
        assert second_data["indexed"] == 0
        assert second_data["skipped"] >= first_data["indexed"]

        status = client.get("/knowledge/embeddings/status")
        assert status.status_code == 200
        status_data = status.json()
        assert status_data["enabled"] is True
        assert status_data["vectorReady"] is True
        assert status_data["readyCount"] >= 2

        semantic = client.post(
            "/knowledge/search",
            json={
                "query": "客户沟通 SOP 第一步怎么做？",
                "retrievalMode": "hybrid",
                "embeddingRuntimeConfig": runtime,
                "topK": 2,
            },
        )
        assert semantic.status_code == 200
        semantic_data = semantic.json()
        assert semantic_data["embeddingUsed"] is True
        assert semantic_data["embeddingReady"] is True
        assert semantic_data["shouldInject"] is True
        assert semantic_data["hits"][0]["sourceTitle"] == "松果客服规范"
        assert "用户导入资料" in semantic_data["promptContext"]


def test_generic_query_does_not_call_embedding_even_when_vectors_are_ready(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "embedding.sqlite"))
    runtime = mock_runtime_config()

    with TestClient(app) as client:
        seed_embedding_sources(client)
        assert client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime}).status_code == 200

        generic = client.post(
            "/knowledge/search",
            json={
                "query": "负责人是谁？",
                "retrievalMode": "hybrid",
                "embeddingRuntimeConfig": runtime,
            },
        )
        assert generic.status_code == 200
        data = generic.json()
        assert data["hits"] == []
        assert data["promptContext"] == ""
        assert data["shouldInject"] is False
        assert data["needsClarification"] is True
        assert data["embeddingUsed"] is False
        assert data["embeddingReason"] == "query-needs-specific-source-or-entity"


def test_deleted_source_embeddings_are_not_recalled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "embedding.sqlite"))
    runtime = mock_runtime_config()

    with TestClient(app) as client:
        created = seed_embedding_sources(client)
        assert client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime}).status_code == 200
        deleted = client.delete(f"/knowledge/sources/{created['松果客服规范']['id']}")
        assert deleted.status_code == 200

        search = client.post(
            "/knowledge/search",
            json={
                "query": "客户沟通 SOP 第一步怎么做？",
                "retrievalMode": "hybrid",
                "embeddingRuntimeConfig": runtime,
            },
        )
        assert search.status_code == 200
        data = search.json()
        assert data["promptContext"] == ""
        assert all(hit["sourceTitle"] != "松果客服规范" for hit in data["hits"])


def test_model_dimension_change_marks_old_vectors_stale_and_rebuilds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "embedding.sqlite"))
    runtime = mock_runtime_config(dimensions=32, model="mock-embedding-a")
    changed_runtime = mock_runtime_config(dimensions=48, model="mock-embedding-b")

    with TestClient(app) as client:
        seed_embedding_sources(client)
        first = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime})
        assert first.status_code == 200
        assert first.json()["indexed"] >= 2

        saved = client.put("/embedding/config", json={key: value for key, value in changed_runtime.items() if key != "apiKey"})
        assert saved.status_code == 200
        status_after_change = client.get("/knowledge/embeddings/status").json()
        assert status_after_change["staleCount"] >= 1
        assert status_after_change["readyCount"] == 0

        rebuilt = client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": changed_runtime})
        assert rebuilt.status_code == 200
        assert rebuilt.json()["indexed"] >= 2
        status_after_rebuild = client.get("/knowledge/embeddings/status").json()
        assert status_after_rebuild["readyCount"] >= 2
        assert status_after_rebuild["staleCount"] == 0


def test_embedding_provider_failure_falls_back_to_local_search_with_redacted_reason(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "embedding.sqlite"))
    runtime = mock_runtime_config()

    with TestClient(app) as client:
        seed_embedding_sources(client)
        assert client.post("/knowledge/embeddings/reindex", json={"embeddingRuntimeConfig": runtime}).status_code == 200

        def fail_embeddings(_texts, _runtime_config):
            raise embeddings.EmbeddingProviderError("Bearer should-not-leak-token")

        monkeypatch.setattr(embeddings, "create_embeddings", fail_embeddings)
        search = client.post(
            "/knowledge/search",
            json={
                "query": "XLP-2026-041 对应哪份资料？",
                "retrievalMode": "hybrid",
                "embeddingRuntimeConfig": runtime,
            },
        )
        assert search.status_code == 200
        data = search.json()
        assert data["embeddingUsed"] is False
        assert data["embeddingReady"] is True
        assert "should-not-leak-token" not in json.dumps(data, ensure_ascii=False)
        assert data["shouldInject"] is True
        assert data["hits"][0]["sourceTitle"] == "星蓝计划"
