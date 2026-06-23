import { defaultCompanions } from "../companion/profiles";
import type {
  ChatMessage,
  CompanionProfile,
  LegacyCompanionType,
  MemoryCategory,
  ModelProviderConfig,
  PrivacyNoticeAck,
  StyleSummary,
  UserMemory,
} from "../types";

const STORAGE_KEYS = {
  config: "ai-companion:provider-config",
  memories: "ai-companion:memories",
  messages: "ai-companion:messages",
  companion: "ai-companion:companion",
  companions: "ai-companion:companions",
  activeCompanionId: "ai-companion:active-companion-id",
  styleSummaries: "ai-companion:style-summaries",
  privacyNoticeAck: "ai-companion:privacy-notice-ack:v1",
} as const;

export const defaultProviderConfig: ModelProviderConfig = {
  providerName: "OpenAI 兼容接口",
  baseURL: "https://api.openai.com/v1",
  model: "",
  apiKey: "",
};

function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJSON<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value));
}

function nowISO(): string {
  return new Date().toISOString();
}

const legacyCompanionMap: Record<LegacyCompanionType, string> = {
  friend: "companion-friend",
  romantic: "companion-romance",
  rational: "companion-support",
  healing: "companion-healing",
  roleplay: "companion-roleplay",
};

function normalizeMemoryCategory(category: unknown): MemoryCategory {
  const value = String(category);
  if (value === "basic") return "identity";
  if (value === "emotion") return "emotion_pattern";
  if (value === "event") return "event";
  if (value === "relationship") return "relationship";
  if (value === "boundary") return "boundary";
  if (value === "preference") return "preference";
  return "preference";
}

function migrateMemory(raw: Partial<UserMemory> & Record<string, unknown>): UserMemory {
  const now = nowISO();
  return {
    id: String(raw.id ?? crypto.randomUUID()),
    scope: raw.scope === "companion" ? "companion" : "global",
    companionId: typeof raw.companionId === "string" ? raw.companionId : undefined,
    category: normalizeMemoryCategory(raw.category),
    content: String(raw.content ?? "").trim(),
    source: raw.source === "manual" || raw.source === "import_summary" ? raw.source : "chat",
    confidence: typeof raw.confidence === "number" ? raw.confidence : 0.72,
    importance: raw.importance === 1 || raw.importance === 2 || raw.importance === 3 ? raw.importance : 2,
    sensitivity: raw.sensitivity === "sensitive" ? "sensitive" : "normal",
    status:
      raw.status === "superseded" || raw.status === "expired" || raw.status === "deleted" ? raw.status : "active",
    sourceMessageId: typeof raw.sourceMessageId === "string" ? raw.sourceMessageId : undefined,
    supersededById: typeof raw.supersededById === "string" ? raw.supersededById : undefined,
    expiresAt: typeof raw.expiresAt === "string" ? raw.expiresAt : undefined,
    createdAt: typeof raw.createdAt === "string" ? raw.createdAt : now,
    updatedAt: typeof raw.updatedAt === "string" ? raw.updatedAt : now,
  };
}

function dedupeCompanions(companions: CompanionProfile[]): CompanionProfile[] {
  const byId = new Map<string, CompanionProfile>();
  [...defaultCompanions, ...companions].forEach((companion) => byId.set(companion.id, companion));
  return [...byId.values()];
}

export function loadProviderConfig(): ModelProviderConfig {
  return readJSON(STORAGE_KEYS.config, defaultProviderConfig);
}

export function saveProviderConfig(config: ModelProviderConfig): void {
  writeJSON(STORAGE_KEYS.config, config);
}

export function loadMemories(): UserMemory[] {
  return readJSON<Array<Partial<UserMemory> & Record<string, unknown>>>(STORAGE_KEYS.memories, [])
    .map(migrateMemory)
    .filter((memory) => memory.content);
}

export function saveMemories(memories: UserMemory[]): void {
  writeJSON(STORAGE_KEYS.memories, memories);
}

export function loadMessages(): ChatMessage[] {
  return readJSON(STORAGE_KEYS.messages, []);
}

export function saveMessages(messages: ChatMessage[]): void {
  writeJSON(STORAGE_KEYS.messages, messages);
}

export function loadCompanions(): CompanionProfile[] {
  const stored = readJSON<CompanionProfile[]>(STORAGE_KEYS.companions, []);
  return dedupeCompanions(Array.isArray(stored) ? stored : []);
}

export function saveCompanions(companions: CompanionProfile[]): void {
  writeJSON(STORAGE_KEYS.companions, companions);
}

export function loadActiveCompanionId(): string {
  const activeId = readJSON<string | null>(STORAGE_KEYS.activeCompanionId, null);
  if (activeId) return activeId;

  const legacyType = readJSON<LegacyCompanionType>(STORAGE_KEYS.companion, "friend");
  return legacyCompanionMap[legacyType] ?? "companion-friend";
}

export function saveActiveCompanionId(id: string): void {
  writeJSON(STORAGE_KEYS.activeCompanionId, id);
}

export function loadStyleSummaries(): StyleSummary[] {
  return readJSON<StyleSummary[]>(STORAGE_KEYS.styleSummaries, []).map((summary) => ({
    ...summary,
    forbiddenIdentityClaims: Array.isArray(summary.forbiddenIdentityClaims) ? summary.forbiddenIdentityClaims : [],
    boundCompanionIds: Array.isArray(summary.boundCompanionIds) ? summary.boundCompanionIds : [],
    userReviewed: Boolean(summary.userReviewed),
  }));
}

export function saveStyleSummaries(summaries: StyleSummary[]): void {
  writeJSON(STORAGE_KEYS.styleSummaries, summaries);
}

export function loadPrivacyNoticeAck(): PrivacyNoticeAck {
  return readJSON<PrivacyNoticeAck>(STORAGE_KEYS.privacyNoticeAck, { acknowledged: false });
}

export function savePrivacyNoticeAck(value: PrivacyNoticeAck): void {
  writeJSON(STORAGE_KEYS.privacyNoticeAck, value);
}
