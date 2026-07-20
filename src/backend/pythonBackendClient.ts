import type { KnowledgeSourceStatus, KnowledgeSourceType } from "../types";

const PYTHON_BACKEND_BASE_URL = "http://127.0.0.1:8765";
const DEFAULT_TIMEOUT_MS = 1800;

export type PythonBackendHealth = {
  available: boolean;
  status: "checking" | "ok" | "unavailable" | "error";
  dbReady: boolean;
  schemaVersion?: number;
  dbPath?: string;
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
};

export type PythonKnowledgeSearchResult = {
  hits: PythonKnowledgeHit[];
  promptContext: string;
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
  return "本地 Python 后端未运行，知识库暂不可用。";
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
    const response = await fetch(`${PYTHON_BACKEND_BASE_URL}${path}`, {
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
          ? "本地 Python 后端已连接，知识库会保存到 SQLite。"
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
}): Promise<PythonKnowledgeSearchResult> {
  return requestJSON<PythonKnowledgeSearchResult>(
    "/knowledge/search",
    {
      method: "POST",
      body: JSON.stringify({
        query: payload.query,
        topK: payload.topK ?? 3,
        promptBudget: payload.promptBudget ?? 1200,
      }),
    },
    2500,
  );
}
