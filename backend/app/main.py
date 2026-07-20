from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .core import get_core_counts, get_core_status, load_core_snapshot, save_core_snapshot
from .db import SCHEMA_VERSION, connect, get_db_path_label, init_db
from .knowledge import (
    DuplicateKnowledgeSourceError,
    KnowledgeSourceNotFoundError,
    create_source,
    get_db_counts,
    list_sources,
    search_knowledge,
    soft_delete_source,
)
from .schemas import (
    CoreMigrationResponse,
    CoreSnapshot,
    CoreStatusResponse,
    CreateKnowledgeSourceRequest,
    DbStatusResponse,
    DeleteKnowledgeSourceResponse,
    HealthResponse,
    KnowledgeSourceResponse,
    SearchKnowledgeRequest,
    SearchKnowledgeResponse,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    with connect() as connection:
        init_db(connection)
    yield


app = FastAPI(
    title="Suoyi Local Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "null"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    init_db(connection)
    try:
        yield connection
    finally:
        connection.close()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        with connect() as connection:
            init_db(connection)
        return HealthResponse(status="ok", dbReady=True, schemaVersion=SCHEMA_VERSION, dbPath=get_db_path_label())
    except sqlite3.Error:
        return HealthResponse(status="error", dbReady=False, schemaVersion=SCHEMA_VERSION, dbPath=get_db_path_label())


@app.get("/db/status", response_model=DbStatusResponse)
def db_status(connection: sqlite3.Connection = Depends(get_connection)) -> DbStatusResponse:
    source_count, active_source_count, chunk_count, active_chunk_count = get_db_counts(connection)
    return DbStatusResponse(
        schemaVersion=SCHEMA_VERSION,
        sourceCount=source_count,
        activeSourceCount=active_source_count,
        chunkCount=chunk_count,
        activeChunkCount=active_chunk_count,
        coreCounts=get_core_counts(connection),
    )


@app.get("/core/status", response_model=CoreStatusResponse)
def core_status(connection: sqlite3.Connection = Depends(get_connection)) -> CoreStatusResponse:
    return get_core_status(connection, SCHEMA_VERSION)


@app.get("/core/snapshot", response_model=CoreSnapshot)
def get_core_snapshot(connection: sqlite3.Connection = Depends(get_connection)) -> CoreSnapshot:
    return load_core_snapshot(connection)


@app.put("/core/snapshot", response_model=CoreMigrationResponse)
def put_core_snapshot(
    payload: CoreSnapshot,
    connection: sqlite3.Connection = Depends(get_connection),
) -> CoreMigrationResponse:
    return save_core_snapshot(connection, payload, source="renderer-auto", replace=True, record_migration=False)


@app.post("/core/migrations/local-storage-snapshot", response_model=CoreMigrationResponse)
def post_local_storage_snapshot_migration(
    payload: CoreSnapshot,
    connection: sqlite3.Connection = Depends(get_connection),
) -> CoreMigrationResponse:
    try:
        return save_core_snapshot(connection, payload, source="localStorage", replace=False, record_migration=True)
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="核心数据迁移失败，已保留 localStorage fallback。",
        ) from error


@app.post(
    "/knowledge/sources",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_knowledge_source(
    payload: CreateKnowledgeSourceRequest,
    connection: sqlite3.Connection = Depends(get_connection),
) -> KnowledgeSourceResponse:
    try:
        return create_source(
            connection,
            title=payload.title,
            source_type=payload.sourceType,
            content=payload.content,
        )
    except DuplicateKnowledgeSourceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "同内容资料已存在，未重复导入。",
                "existingSourceId": error.source_id,
            },
        ) from error


@app.get("/knowledge/sources", response_model=list[KnowledgeSourceResponse])
def get_knowledge_sources(connection: sqlite3.Connection = Depends(get_connection)) -> list[KnowledgeSourceResponse]:
    return list_sources(connection)


@app.delete("/knowledge/sources/{source_id}", response_model=DeleteKnowledgeSourceResponse)
def delete_knowledge_source(
    source_id: str,
    connection: sqlite3.Connection = Depends(get_connection),
) -> DeleteKnowledgeSourceResponse:
    try:
        return soft_delete_source(connection, source_id)
    except KnowledgeSourceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资料不存在。") from error


@app.post("/knowledge/search", response_model=SearchKnowledgeResponse)
def post_knowledge_search(
    payload: SearchKnowledgeRequest,
    connection: sqlite3.Connection = Depends(get_connection),
) -> SearchKnowledgeResponse:
    return search_knowledge(
        connection,
        query=payload.query,
        top_k=payload.topK,
        prompt_budget=payload.promptBudget,
    )
