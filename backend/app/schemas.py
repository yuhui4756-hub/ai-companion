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
    ftsReady: bool = False
    knowledgeSearchMode: str = "keyword"
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
    headingPath: str = ""
    chunkType: str = "paragraph"
    scores: dict[str, float] = Field(default_factory=dict)


class SearchKnowledgeRequest(BaseModel):
    query: str = Field(default="", max_length=4_000)
    topK: int = Field(default=3, ge=1, le=10)
    promptBudget: int = Field(default=1200, ge=100, le=4000)
    retrievalMode: str = Field(default="auto", pattern="^(auto|keyword|hybrid)$")
    embeddingRuntimeConfig: Optional["EmbeddingRuntimeConfig"] = None


class SearchKnowledgeResponse(BaseModel):
    hits: list[KnowledgeHitResponse]
    promptContext: str
    mode: str = "keyword"
    shouldInject: bool = False
    needsClarification: bool = False
    reason: str = ""
    ftsReady: bool = False
    embeddingUsed: bool = False
    embeddingReady: bool = False
    embeddingReason: str = ""


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


class EmbeddingRuntimeConfig(BaseModel):
    providerName: str = Field(default="openai_compatible", max_length=80)
    baseURL: str = Field(default="https://api.openai.com/v1", max_length=500)
    model: str = Field(default="text-embedding-3-small", max_length=160)
    dimensions: int = Field(default=1536, ge=1, le=8192)
    batchSize: int = Field(default=16, ge=1, le=64)
    timeoutMs: int = Field(default=10_000, ge=1_000, le=60_000)
    enabled: bool = False
    apiKey: Optional[str] = Field(default=None, max_length=4_000)


class EmbeddingConfigRequest(BaseModel):
    providerName: str = Field(default="openai_compatible", max_length=80)
    baseURL: str = Field(default="https://api.openai.com/v1", max_length=500)
    model: str = Field(default="text-embedding-3-small", max_length=160)
    dimensions: int = Field(default=1536, ge=1, le=8192)
    batchSize: int = Field(default=16, ge=1, le=64)
    timeoutMs: int = Field(default=10_000, ge=1_000, le=60_000)
    enabled: bool = False


class EmbeddingConfigResponse(BaseModel):
    id: str = "default"
    providerName: str
    baseURL: str
    model: str
    dimensions: int
    batchSize: int
    timeoutMs: int
    enabled: bool
    apiKeyRef: str = "renderer-localStorage"
    lastCheckedAt: Optional[str] = None
    lastStatus: Optional[str] = None
    lastError: Optional[str] = None


class EmbeddingHealthCheckRequest(BaseModel):
    runtimeConfig: EmbeddingRuntimeConfig


class EmbeddingHealthCheckResponse(BaseModel):
    ok: bool
    status: str
    message: str
    dimensions: Optional[int] = None
    checkedAt: str


class KnowledgeEmbeddingStatusResponse(BaseModel):
    providerId: str = "default"
    providerName: str
    model: str
    dimensions: int
    enabled: bool
    activeChunkCount: int
    readyCount: int
    pendingCount: int
    indexingCount: int
    failedCount: int
    staleCount: int
    vectorReady: bool
    lastIndexedAt: Optional[str] = None
    lastError: Optional[str] = None
    lexicalReady: bool = True
    message: str


class ReindexKnowledgeEmbeddingsRequest(BaseModel):
    sourceId: Optional[str] = None
    force: bool = False
    embeddingRuntimeConfig: EmbeddingRuntimeConfig


class ReindexKnowledgeEmbeddingsResponse(BaseModel):
    ok: bool
    status: str
    indexed: int
    skipped: int
    failed: int
    stale: int
    pending: int
    ready: int
    message: str
