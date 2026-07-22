import type {
  ChatMessage,
  CompanionProfile,
  EmbeddingProviderLocalConfig,
  EmbeddingProviderPublicConfig,
  KnowledgeSourceStatus,
  KnowledgeSourceType,
  KnowledgeRetrievalMode,
  ModelProviderConfig,
  StyleSummary,
  UserMemory,
} from "../types";

const DEFAULT_PYTHON_BACKEND_BASE_URL = "http://127.0.0.1:8765";
const DEFAULT_TIMEOUT_MS = 1800;
let pythonBackendBaseURL = DEFAULT_PYTHON_BACKEND_BASE_URL;

function normalizeBackendBaseURL(value: string): string | null {
  try {
    const parsed = new URL(value.trim());
    const isLocalHost = parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost";
    if (parsed.protocol !== "http:" || !isLocalHost) return null;
    parsed.pathname = parsed.pathname.replace(/\/+$/, "");
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString().replace(/\/+$/, "");
  } catch {
    return null;
  }
}

export function setPythonBackendBaseURL(value?: string | null): void {
  const normalized = value ? normalizeBackendBaseURL(value) : null;
  pythonBackendBaseURL = normalized ?? DEFAULT_PYTHON_BACKEND_BASE_URL;
}

export function getPythonBackendBaseURL(): string {
  return pythonBackendBaseURL;
}

export type PythonBackendHealth = {
  available: boolean;
  status: "checking" | "ok" | "unavailable" | "error";
  dbReady: boolean;
  schemaVersion?: number;
  dbPath?: string;
  message: string;
};

export type CoreProviderConfigWithoutApiKey = Omit<ModelProviderConfig, "apiKey"> & {
  apiKeyRemoved: true;
  options?: Record<string, unknown>;
};

export type CoreSnapshot = {
  snapshotVersion: "core-snapshot-v1";
  snapshotHash?: string;
  activeCompanionId: string;
  providerConfigWithoutApiKey: CoreProviderConfigWithoutApiKey;
  companions: CompanionProfile[];
  messagesByCompanionId: Record<string, ChatMessage[]>;
  memories: UserMemory[];
  styleSummaries: StyleSummary[];
};

export type CoreCounts = {
  companions: number;
  messages: number;
  memories: number;
  styleSummaries: number;
  providerConfigs: number;
  migrationRuns: number;
};

export type CoreStatus = {
  schemaVersion: number;
  coreReady: boolean;
  latestMigrationHash?: string;
  latestMigrationStatus?: string;
  counts: CoreCounts;
  message: string;
};

export type CoreMigrationResult = {
  ok: boolean;
  status: string;
  snapshotHash: string;
  counts: CoreCounts;
  message: string;
};

export type PythonKnowledgeSource = {
  id: string;
  title: string;
  sourceType: KnowledgeSourceType;
  status: KnowledgeSourceStatus;
  chunkCount: number;
  createdAt: string;
  updatedAt: string;
};

export type PythonKnowledgeHit = {
  sourceId: string;
  sourceTitle: string;
  chunkIndex: number;
  content: string;
  score: number;
  headingPath?: string;
  chunkType?: string;
  scores?: Record<string, number>;
};

export type PythonKnowledgeSearchResult = {
  hits: PythonKnowledgeHit[];
  promptContext: string;
  mode?: string;
  shouldInject?: boolean;
  needsClarification?: boolean;
  reason?: string;
  ftsReady?: boolean;
  embeddingUsed?: boolean;
  embeddingReady?: boolean;
  embeddingReason?: string;
};

export type PythonEmbeddingHealthCheckResult = {
  ok: boolean;
  status: string;
  message: string;
  dimensions?: number;
  checkedAt: string;
};

export type PythonKnowledgeEmbeddingStatus = {
  providerId: string;
  providerName: string;
  model: string;
  dimensions: number;
  enabled: boolean;
  activeChunkCount: number;
  readyCount: number;
  pendingCount: number;
  indexingCount: number;
  failedCount: number;
  staleCount: number;
  vectorReady: boolean;
  lastIndexedAt?: string;
  lastError?: string;
  lexicalReady: boolean;
  message: string;
};

export type PythonKnowledgeEmbeddingReindexResult = {
  ok: boolean;
  status: string;
  indexed: number;
  skipped: number;
  failed: number;
  stale: number;
  pending: number;
  ready: number;
  message: string;
};

export class PythonBackendError extends Error {
  code: "unavailable" | "duplicate" | "request";
  status?: number;
  existingSourceId?: string;

  constructor(code: PythonBackendError["code"], message: string, options?: { status?: number; existingSourceId?: string }) {
    super(message);
    this.name = "PythonBackendError";
    this.code = code;
    this.status = options?.status;
    this.existingSourceId = options?.existingSourceId;
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof PythonBackendError) return error.message;
  if (error instanceof Error && error.name === "AbortError") {
    return "本地 Python 后端响应超时，请确认服务正在运行。";
  }
  return "本地 Python 后端未运行，本地知识库和 SQLite 暂不可用。";
}

function parseErrorPayload(value: unknown): { message: string; existingSourceId?: string } {
  if (!value || typeof value !== "object") return { message: "本地 Python 后端请求失败。" };
  const detail = (value as { detail?: unknown }).detail;
  if (typeof detail === "string") return { message: detail };
  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; existingSourceId?: unknown };
    return {
      message: typeof record.message === "string" ? record.message : "本地 Python 后端请求失败。",
      existingSourceId: typeof record.existingSourceId === "string" ? record.existingSourceId : undefined,
    };
  }
  return { message: "本地 Python 后端请求失败。" };
}

async function requestJSON<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${pythonBackendBaseURL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      const parsed = parseErrorPayload(payload);
      throw new PythonBackendError(response.status === 409 ? "duplicate" : "request", parsed.message, {
        status: response.status,
        existingSourceId: parsed.existingSourceId,
      });
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof PythonBackendError) throw error;
    throw new PythonBackendError("unavailable", getErrorMessage(error));
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function getPythonCoreStatus(): Promise<CoreStatus> {
  return requestJSON<CoreStatus>("/core/status", { method: "GET" });
}

export async function getPythonCoreSnapshot(): Promise<CoreSnapshot> {
  return requestJSON<CoreSnapshot>("/core/snapshot", { method: "GET" });
}

export async function importLocalStorageCoreSnapshot(snapshot: CoreSnapshot): Promise<CoreMigrationResult> {
  return requestJSON<CoreMigrationResult>(
    "/core/migrations/local-storage-snapshot",
    {
      method: "POST",
      body: JSON.stringify(snapshot),
    },
    8000,
  );
}

export async function savePythonCoreSnapshot(snapshot: CoreSnapshot): Promise<CoreMigrationResult> {
  return requestJSON<CoreMigrationResult>(
    "/core/snapshot",
    {
      method: "PUT",
      body: JSON.stringify(snapshot),
    },
    5000,
  );
}

export async function getPythonBackendHealth(): Promise<PythonBackendHealth> {
  try {
    const health = await requestJSON<{
      status: string;
      dbReady: boolean;
      schemaVersion: number;
      dbPath: string;
    }>("/health", { method: "GET" }, 1200);
    return {
      available: health.status === "ok" && health.dbReady,
      status: health.status === "ok" ? "ok" : "error",
      dbReady: health.dbReady,
      schemaVersion: health.schemaVersion,
      dbPath: health.dbPath,
      message:
        health.status === "ok" && health.dbReady
          ? "本地 Python 后端已连接，知识库和 SQLite 数据可用。"
          : "本地 Python 后端已响应，但 SQLite 暂不可用。",
    };
  } catch (error) {
    return {
      available: false,
      status: "unavailable",
      dbReady: false,
      message: getErrorMessage(error),
    };
  }
}

export function listPythonKnowledgeSources(): Promise<PythonKnowledgeSource[]> {
  return requestJSON<PythonKnowledgeSource[]>("/knowledge/sources", { method: "GET" });
}

export function importPythonKnowledgeSource(payload: {
  title: string;
  sourceType: KnowledgeSourceType;
  content: string;
}): Promise<PythonKnowledgeSource> {
  return requestJSON<PythonKnowledgeSource>(
    "/knowledge/sources",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    5000,
  );
}

export function deletePythonKnowledgeSource(sourceId: string): Promise<{ id: string; status: KnowledgeSourceStatus; deletedChunkCount: number }> {
  return requestJSON(`/knowledge/sources/${encodeURIComponent(sourceId)}`, { method: "DELETE" });
}

export function searchPythonKnowledge(payload: {
  query: string;
  topK?: number;
  promptBudget?: number;
  retrievalMode?: KnowledgeRetrievalMode;
  embeddingRuntimeConfig?: EmbeddingProviderLocalConfig;
}): Promise<PythonKnowledgeSearchResult> {
  return requestJSON<PythonKnowledgeSearchResult>(
    "/knowledge/search",
    {
      method: "POST",
      body: JSON.stringify({
        query: payload.query,
        topK: payload.topK ?? 3,
        promptBudget: payload.promptBudget ?? 1200,
        retrievalMode: payload.retrievalMode ?? "auto",
        embeddingRuntimeConfig: payload.embeddingRuntimeConfig,
      }),
    },
    payload.embeddingRuntimeConfig?.enabled ? 5000 : 2500,
  );
}

function publicEmbeddingConfig(config: EmbeddingProviderLocalConfig): Omit<EmbeddingProviderLocalConfig, "apiKey"> {
  const { apiKey: _apiKey, ...publicConfig } = config;
  return publicConfig;
}

export function getPythonEmbeddingConfig(): Promise<EmbeddingProviderPublicConfig> {
  return requestJSON<EmbeddingProviderPublicConfig>("/embedding/config", { method: "GET" });
}

export function savePythonEmbeddingConfig(config: EmbeddingProviderLocalConfig): Promise<EmbeddingProviderPublicConfig> {
  return requestJSON<EmbeddingProviderPublicConfig>(
    "/embedding/config",
    {
      method: "PUT",
      body: JSON.stringify(publicEmbeddingConfig(config)),
    },
    2500,
  );
}

export function checkPythonEmbeddingHealth(config: EmbeddingProviderLocalConfig): Promise<PythonEmbeddingHealthCheckResult> {
  return requestJSON<PythonEmbeddingHealthCheckResult>(
    "/embedding/health/check",
    {
      method: "POST",
      body: JSON.stringify({ runtimeConfig: config }),
    },
    Math.max(config.timeoutMs + 1000, 2500),
  );
}

export function getPythonKnowledgeEmbeddingStatus(): Promise<PythonKnowledgeEmbeddingStatus> {
  return requestJSON<PythonKnowledgeEmbeddingStatus>("/knowledge/embeddings/status", { method: "GET" });
}

export function reindexPythonKnowledgeEmbeddings(payload: {
  sourceId?: string;
  force?: boolean;
  embeddingRuntimeConfig: EmbeddingProviderLocalConfig;
}): Promise<PythonKnowledgeEmbeddingReindexResult> {
  return requestJSON<PythonKnowledgeEmbeddingReindexResult>(
    "/knowledge/embeddings/reindex",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    Math.max(payload.embeddingRuntimeConfig.timeoutMs * 4, 10000),
  );
}
