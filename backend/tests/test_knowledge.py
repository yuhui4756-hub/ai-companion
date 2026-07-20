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
    assert data["schemaVersion"] == 1
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
