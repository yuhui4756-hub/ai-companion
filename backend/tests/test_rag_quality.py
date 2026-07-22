import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


QUALITY_FIXTURES = [
    {
        "title": "星蓝计划",
        "sourceType": "manual_text",
        "content": "\n".join(
            [
                "编号：XLP-2026-041",
                "预算金额：12.8 万元",
                "负责人：许念",
                "截止日期：2026-08-15",
                "说明：星蓝计划用于验证所依本地知识库的精确召回。",
            ]
        ),
    },
    {
        "title": "月澜活动",
        "sourceType": "manual_text",
        "content": "\n".join(
            [
                "编号：YL-2026-009",
                "预算金额：3.4 万元",
                "负责人：林澈",
                "截止日期：2026-09-02",
                "说明：月澜活动是一场线下用户访谈和纪念品派发活动。",
            ]
        ),
    },
    {
        "title": "松果客服规范",
        "sourceType": "manual_text",
        "content": "\n".join(
            [
                "编号：SG-SERVICE-17",
                "负责人：周衡",
                "更新日期：2026-07-30",
                "规则：客服回复先确认用户问题，再给出下一步操作。",
            ]
        ),
    },
    {
        "title": "北桥设备清单",
        "sourceType": "manual_text",
        "content": "北桥设备清单包含笔记本、麦克风和备用路由器。保管人：陈序。位置：B2 储物柜。",
    },
    {
        "title": "风铃读书笔记",
        "sourceType": "manual_text",
        "content": "风铃读书笔记记录陪伴式产品的语气原则：少命令，多确认，多给用户选择感。",
    },
    {
        "title": "长 Markdown 运营手册",
        "sourceType": "markdown",
        "content": """
# 运营手册

## 项目档案
编号：MD-OPS-2026
预算金额：8.6 万元
负责人：唐栗
截止日期：2026-10-01

## 执行清单
- 第一步：整理用户授权文本。
- 第二步：检查导入资料是否包含敏感字段。
- 第三步：完成本地检索验收。

## 预算表
| 项目 | 金额 | 负责人 |
| --- | --- | --- |
| 场地 | 2.1 万元 | 唐栗 |
| 物料 | 1.6 万元 | 韩舟 |

## 常见问答
问：删除资料后还能命中吗？
答：不能。软删除后的 source 和 chunk 都不得进入检索结果。
""".strip(),
    },
]


def seed_quality_sources(client: TestClient) -> dict[str, dict]:
    created: dict[str, dict] = {}
    for payload in QUALITY_FIXTURES:
        response = client.post("/knowledge/sources", json=payload)
        assert response.status_code == 201
        created[payload["title"]] = response.json()
    return created


def test_generic_and_unrelated_queries_do_not_inject(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-quality.sqlite"))

    with TestClient(app) as client:
        seed_quality_sources(client)

        generic_budget = client.post("/knowledge/search", json={"query": "预算金额是多少？", "topK": 3})
        assert generic_budget.status_code == 200
        generic_data = generic_budget.json()
        assert generic_data["hits"] == []
        assert generic_data["promptContext"] == ""
        assert generic_data["shouldInject"] is False
        assert generic_data["needsClarification"] is True

        generic_owner = client.post("/knowledge/search", json={"query": "负责人是谁？", "topK": 3})
        assert generic_owner.status_code == 200
        owner_data = generic_owner.json()
        assert owner_data["hits"] == []
        assert owner_data["promptContext"] == ""
        assert owner_data["shouldInject"] is False

        unrelated = client.post("/knowledge/search", json={"query": "今晚适合吃什么？", "topK": 3})
        assert unrelated.status_code == 200
        assert unrelated.json()["hits"] == []
        assert unrelated.json()["promptContext"] == ""


def test_unique_identifier_and_named_entity_rank_target_first(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-quality.sqlite"))

    with TestClient(app) as client:
        seed_quality_sources(client)

        by_identifier = client.post("/knowledge/search", json={"query": "XLP-2026-041 对应哪份资料？", "topK": 3})
        assert by_identifier.status_code == 200
        identifier_data = by_identifier.json()
        assert identifier_data["shouldInject"] is True
        assert identifier_data["hits"][0]["sourceTitle"] == "星蓝计划"
        assert "XLP-2026-041" in identifier_data["promptContext"]

        by_person = client.post("/knowledge/search", json={"query": "许念负责什么？", "topK": 3})
        assert by_person.status_code == 200
        person_data = by_person.json()
        assert person_data["shouldInject"] is True
        assert person_data["hits"][0]["sourceTitle"] == "星蓝计划"
        assert "许念" in person_data["promptContext"]


def test_named_source_field_query_does_not_mix_other_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-quality.sqlite"))

    with TestClient(app) as client:
        seed_quality_sources(client)

        star_budget = client.post("/knowledge/search", json={"query": "星蓝计划的预算金额是多少？", "topK": 3})
        assert star_budget.status_code == 200
        star_data = star_budget.json()
        assert star_data["shouldInject"] is True
        assert {hit["sourceTitle"] for hit in star_data["hits"]} == {"星蓝计划"}
        assert "12.8 万元" in star_data["promptContext"]
        assert "3.4 万元" not in star_data["promptContext"]
        assert "林澈" not in star_data["promptContext"]

        moon_owner = client.post("/knowledge/search", json={"query": "月澜活动由哪位负责？", "topK": 3})
        assert moon_owner.status_code == 200
        moon_data = moon_owner.json()
        assert moon_data["shouldInject"] is True
        assert {hit["sourceTitle"] for hit in moon_data["hits"]} == {"月澜活动"}
        assert "林澈" in moon_data["promptContext"]
        assert "许念" not in moon_data["promptContext"]


def test_deleted_source_is_not_recalled_or_injected(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-quality.sqlite"))

    with TestClient(app) as client:
        created = seed_quality_sources(client)
        deleted = client.delete(f"/knowledge/sources/{created['星蓝计划']['id']}")
        assert deleted.status_code == 200

        search = client.post("/knowledge/search", json={"query": "星蓝计划负责人是谁？", "topK": 3})
        assert search.status_code == 200
        data = search.json()
        assert data["hits"] == []
        assert data["promptContext"] == ""
        assert data["shouldInject"] is False


def test_duplicate_import_and_multi_document_field_question_do_not_mix_answer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(tmp_path / "rag-quality.sqlite"))

    with TestClient(app) as client:
        seed_quality_sources(client)

        duplicate = client.post("/knowledge/sources", json=QUALITY_FIXTURES[0])
        assert duplicate.status_code == 409

        multi_doc_field = client.post("/knowledge/search", json={"query": "这些项目的负责人是谁？", "topK": 3})
        assert multi_doc_field.status_code == 200
        data = multi_doc_field.json()
        assert data["shouldInject"] is False
        assert data["promptContext"] == ""
        assert data["hits"] == []


def test_markdown_structured_chunks_keep_metadata_and_fact_blocks(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "rag-quality.sqlite"
    monkeypatch.setenv("SUOYI_BACKEND_DB_PATH", str(db_path))

    with TestClient(app) as client:
        seed_quality_sources(client)
        markdown_search = client.post("/knowledge/search", json={"query": "MD-OPS-2026 的预算表有什么？", "topK": 3})
        assert markdown_search.status_code == 200
        assert markdown_search.json()["shouldInject"] is True

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT c.heading_path, c.chunk_type, c.content, c.content_hash, c.chunker_version,
                   c.token_estimate, c.metadata_json
            FROM knowledge_chunks c
            JOIN knowledge_sources s ON s.id = c.source_id
            WHERE s.title = '长 Markdown 运营手册'
            ORDER BY c.chunk_index
            """
        ).fetchall()

    assert rows
    assert {row["chunker_version"] for row in rows} == {"v2-structured"}
    assert all(row["content_hash"] for row in rows)
    assert all(row["token_estimate"] > 0 for row in rows)
    chunk_types = {row["chunk_type"] for row in rows}
    assert {"fact_block", "list", "table_block", "qa"}.issubset(chunk_types)
    assert any(row["heading_path"] == "运营手册 / 项目档案" for row in rows)
    fact_block = next(row for row in rows if row["chunk_type"] == "fact_block" and "MD-OPS-2026" in row["content"])
    assert "预算金额：8.6 万元" in fact_block["content"]
    assert "负责人：唐栗" in fact_block["content"]
    metadata = [json for json in (row["metadata_json"] for row in rows) if "headingPath" in json]
    assert metadata
