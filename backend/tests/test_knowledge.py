import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_initializes_sqlite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "suoyi.sqlite"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dbReady"] is True
    assert data["schemaVersion"] == 4
    assert not str(tmp_path) in data["dbPath"]


def test_import_search_duplicate_and_soft_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "suoyi.sqlite"))
    payload = {
        "title": "星蓝计划",
        "sourceType": "manual_text",
        "content": "星蓝计划是给所依准备的本地知识库验证资料。用户问到星蓝计划时，应该引用这段用户导入资料。",
    }

    with TestClient(app) as client:
        created = client.post("/knowledge/sources", json=payload)
        assert created.status_code == 201
        source = created.json()
        assert source["title"] == "星蓝计划"
        assert source["status"] == "active"
        assert source["chunkCount"] >= 1
        assert "content" not in source

        duplicate = client.post("/knowledge/sources", json=payload)
        assert duplicate.status_code == 409

        search = client.post("/knowledge/search", json={"query": "星蓝计划是什么", "topK": 3})
        assert search.status_code == 200
        search_data = search.json()
        assert len(search_data["hits"]) >= 1
        assert "用户导入资料" in search_data["promptContext"]
        assert "星蓝计划" in search_data["promptContext"]

        deleted = client.delete(f"/knowledge/sources/{source['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "deleted"

        search_after_delete = client.post("/knowledge/search", json={"query": "星蓝计划是什么", "topK": 3})
        assert search_after_delete.status_code == 200
        assert search_after_delete.json()["hits"] == []
        assert search_after_delete.json()["promptContext"] == ""


def test_common_english_words_do_not_trigger_unrelated_hits(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "suoyi.sqlite"))
    payload = {
        "title": "English stopword guard",
        "sourceType": "manual_text",
        "content": "This is a local note about lavender2718. It should only match the distinctive marker.",
    }

    with TestClient(app) as client:
        assert client.post("/knowledge/sources", json=payload).status_code == 201

        unrelated = client.post("/knowledge/search", json={"query": "what is the thing", "topK": 3})
        assert unrelated.status_code == 200
        assert unrelated.json()["hits"] == []
        assert unrelated.json()["promptContext"] == ""

        related = client.post("/knowledge/search", json={"query": "lavender2718", "topK": 3})
        assert related.status_code == 200
        assert len(related.json()["hits"]) == 1
        assert "用户导入资料" in related.json()["promptContext"]


def test_sqlite_persists_between_clients(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "suoyi.sqlite"))
    payload = {
        "title": "持久化资料",
        "sourceType": "markdown",
        "content": "## 持久化验证\n\n重启服务后，这段资料仍应在 SQLite 里。",
    }

    with TestClient(app) as client:
        assert client.post("/knowledge/sources", json=payload).status_code == 201

    with TestClient(app) as client:
        sources = client.get("/knowledge/sources")
        assert sources.status_code == 200
        assert [source["title"] for source in sources.json()] == ["持久化资料"]


def test_core_snapshot_migration_is_idempotent_and_redacts_secrets(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "suoyi.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))
    fake_key = "sk-" + "localtest1234"
    fake_bearer = "Bearer " + "abcdefghi12345"
    payload = {
        "snapshotVersion": "core-snapshot-v1",
        "activeCompanionId": "companion-custom",
        "providerConfigWithoutApiKey": {
            "providerName": "Fake Provider",
            "baseURL": "https://example.test/v1?api_key=should-not-store",
            "model": "fake-model",
            "apiKey": fake_key,
            "options": {"accessToken": fake_bearer},
        },
        "companions": [
            {
                "id": "companion-custom",
                "name": "测试伴侣",
                "relationshipType": "light_romance",
                "traitIds": [],
                "createdAt": "2026-07-20T00:00:00Z",
                "updatedAt": "2026-07-20T00:00:00Z",
            }
        ],
        "messagesByCompanionId": {
            "companion-custom": [
                {
                    "role": "user",
                    "content": f"请不要把 {fake_key} 原样写入 SQLite。",
                    "createdAt": "2026-07-20T00:01:00Z",
                }
            ]
        },
        "memories": [
            {
                "id": "memory-1",
                "scope": "global",
                "category": "preference",
                "content": f"测试记忆 {fake_bearer}",
                "importance": 2,
                "confidence": 0.8,
                "sensitivity": "normal",
                "status": "active",
                "createdAt": "2026-07-20T00:02:00Z",
                "updatedAt": "2026-07-20T00:02:00Z",
            }
        ],
        "styleSummaries": [
            {
                "id": "style-1",
                "name": "测试风格",
                "sourceType": "imported_chat",
                "summaryText": "短句回应。",
                "tone": "温柔",
                "pace": "慢",
                "addressing": "你",
                "emotionResponse": "先接住情绪",
                "interactionPatterns": "少追问",
                "forbiddenIdentityClaims": [],
                "boundCompanionIds": ["companion-custom"],
                "userReviewed": True,
                "createdAt": "2026-07-20T00:03:00Z",
                "updatedAt": "2026-07-20T00:03:00Z",
            }
        ],
    }

    with TestClient(app) as client:
        first = client.post("/core/migrations/local-storage-snapshot", json=payload)
        assert first.status_code == 200
        first_data = first.json()
        assert first_data["ok"] is True
        assert first_data["counts"]["companions"] == 1
        assert first_data["counts"]["messages"] == 1
        assert first_data["counts"]["memories"] == 1
        assert first_data["counts"]["styleSummaries"] == 1
        assert first_data["counts"]["providerConfigs"] == 1

        second = client.post("/core/migrations/local-storage-snapshot", json=payload)
        assert second.status_code == 200
        assert second.json()["counts"]["companions"] == 1
        assert second.json()["counts"]["messages"] == 1
        assert second.json()["counts"]["memories"] == 1
        assert second.json()["counts"]["styleSummaries"] == 1

        snapshot = client.get("/core/snapshot")
        assert snapshot.status_code == 200
        snapshot_text = json.dumps(snapshot.json(), ensure_ascii=False)
        assert fake_key not in snapshot_text
        assert "abcdefghi12345" not in snapshot_text
        assert snapshot.json()["activeCompanionId"] == "companion-custom"
        generated_message_id = snapshot.json()["messagesByCompanionId"]["companion-custom"][0]["id"]
        assert generated_message_id.startswith("message-")

        status = client.get("/core/status")
        assert status.status_code == 200
        assert status.json()["latestMigrationStatus"] == "success"

    with sqlite3.connect(db_path) as connection:
        database_text = "\n".join(
            " ".join(str(value) for value in row)
            for table in ["provider_configs", "messages", "memories"]
            for row in connection.execute(f"SELECT * FROM {table}").fetchall()
        )
    assert fake_key not in database_text
    assert "abcdefghi12345" not in database_text


def test_put_core_snapshot_replaces_runtime_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "suoyi.sqlite"))
    base_payload = {
        "snapshotVersion": "core-snapshot-v1",
        "activeCompanionId": "companion-a",
        "providerConfigWithoutApiKey": {"providerName": "A", "baseURL": "https://example.test/v1", "model": "a"},
        "companions": [{"id": "companion-a", "name": "A", "createdAt": "2026-07-20T00:00:00Z", "updatedAt": "2026-07-20T00:00:00Z"}],
        "messagesByCompanionId": {
            "companion-a": [{"id": "message-a", "role": "user", "content": "hello", "createdAt": "2026-07-20T00:01:00Z"}]
        },
        "memories": [],
        "styleSummaries": [],
    }
    next_payload = {
        **base_payload,
        "messagesByCompanionId": {"companion-a": []},
        "memories": [{"id": "memory-a", "content": "new memory", "createdAt": "2026-07-20T00:02:00Z", "updatedAt": "2026-07-20T00:02:00Z"}],
    }

    with TestClient(app) as client:
        assert client.post("/core/migrations/local-storage-snapshot", json=base_payload).status_code == 200
        replaced = client.put("/core/snapshot", json=next_payload)
        assert replaced.status_code == 200
        assert replaced.json()["counts"]["messages"] == 0
        assert replaced.json()["counts"]["memories"] == 1

        snapshot = client.get("/core/snapshot").json()
        assert snapshot["messagesByCompanionId"].get("companion-a", []) == []
        assert [memory["id"] for memory in snapshot["memories"]] == ["memory-a"]
