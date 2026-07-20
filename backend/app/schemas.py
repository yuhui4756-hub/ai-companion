from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class KnowledgeSourceType(str, Enum):
    manual_text = "manual_text"
    markdown = "markdown"


class KnowledgeSourceStatus(str, Enum):
    active = "active"
    deleted = "deleted"


class HealthResponse(BaseModel):
    status: str
    dbReady: bool
    schemaVersion: int
    dbPath: str


class DbStatusResponse(BaseModel):
    schemaVersion: int
    sourceCount: int
    activeSourceCount: int
    chunkCount: int
    activeChunkCount: int
    coreCounts: Optional["CoreCounts"] = None


class CreateKnowledgeSourceRequest(BaseModel):
    title: str = Field(default="", max_length=120)
    sourceType: KnowledgeSourceType = KnowledgeSourceType.manual_text
    content: str = Field(min_length=1, max_length=200_000)


class KnowledgeSourceResponse(BaseModel):
    id: str
    title: str
    sourceType: KnowledgeSourceType
    status: KnowledgeSourceStatus
    chunkCount: int
    createdAt: str
    updatedAt: str


class KnowledgeHitResponse(BaseModel):
    sourceId: str
    sourceTitle: str
    chunkIndex: int
    content: str
    score: float


class SearchKnowledgeRequest(BaseModel):
    query: str = Field(default="", max_length=4_000)
    topK: int = Field(default=3, ge=1, le=10)
    promptBudget: int = Field(default=1200, ge=100, le=4000)


class SearchKnowledgeResponse(BaseModel):
    hits: list[KnowledgeHitResponse]
    promptContext: str


class DeleteKnowledgeSourceResponse(BaseModel):
    id: str
    status: KnowledgeSourceStatus
    deletedChunkCount: int


class ErrorResponse(BaseModel):
    detail: str
    existingSourceId: Optional[str] = None


class CoreProviderConfigWithoutKey(BaseModel):
    providerName: str = ""
    baseURL: str = ""
    model: str = ""
    options: dict[str, Any] = Field(default_factory=dict)
    apiKeyRemoved: bool = True


class CoreSnapshot(BaseModel):
    snapshotVersion: str = "core-snapshot-v1"
    snapshotHash: Optional[str] = None
    activeCompanionId: str = ""
    providerConfigWithoutApiKey: CoreProviderConfigWithoutKey = Field(default_factory=CoreProviderConfigWithoutKey)
    companions: list[dict[str, Any]] = Field(default_factory=list)
    messagesByCompanionId: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    memories: list[dict[str, Any]] = Field(default_factory=list)
    styleSummaries: list[dict[str, Any]] = Field(default_factory=list)


class CoreCounts(BaseModel):
    companions: int = 0
    messages: int = 0
    memories: int = 0
    styleSummaries: int = 0
    providerConfigs: int = 0
    migrationRuns: int = 0


class CoreMigrationResponse(BaseModel):
    ok: bool
    status: str
    snapshotHash: str
    counts: CoreCounts
    message: str


class CoreStatusResponse(BaseModel):
    schemaVersion: int
    coreReady: bool
    latestMigrationHash: Optional[str] = None
    latestMigrationStatus: Optional[str] = None
    counts: CoreCounts
    message: str
