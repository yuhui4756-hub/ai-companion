import { defaultCompanions } from "../companion/profiles";
import { buildBlendPromptSummary, getDefaultRomanceTemplate, getRomanceTemplate } from "../companion/romanceTemplates";
import type {
  ChatMessage,
  CompanionOnboardingState,
  CompanionProfile,
  KnowledgeChunk,
  KnowledgeSource,
  LegacyCompanionType,
  LocalDataExport,
  MemoryCategory,
  ModelProviderConfig,
  PrivacyNoticeAck,
  StyleSummary,
  SyncPolicy,
  UserMemory,
} from "../types";
import { defaultOneBotLocalConfig } from "../channel-adapter/onebotLocal";
import type { OneBotLocalConfig } from "../channel-adapter/types";

const STORAGE_KEYS = {
  config: "ai-companion:provider-config",
  memories: "ai-companion:memories",
  messages: "ai-companion:messages",
  messagesByCompanion: "ai-companion:messages-by-companion:v1",
  companion: "ai-companion:companion",
  companions: "ai-companion:companions",
  activeCompanionId: "ai-companion:active-companion-id",
  styleSummaries: "ai-companion:style-summaries",
  privacyNoticeAck: "ai-companion:privacy-notice-ack:v1",
  companionOnboarding: "ai-companion:companion-onboarding:v1",
  oneBotLocalConfig: "ai-companion:onebot-local-config:v1",
  knowledgeSources: "ai-companion:knowledge-sources:v1",
  knowledgeChunks: "ai-companion:knowledge-chunks:v1",
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
  [...defaultCompanions, ...companions].forEach((companion) => byId.set(companion.id, normalizeCompanion(companion)));
  return [...byId.values()];
}

function normalizeCompanion(companion: CompanionProfile): CompanionProfile {
  const isRomance = companion.primaryMode === "romance" || companion.relationshipType === "light_romance";
  if (!isRomance) {
    return {
      ...companion,
      primaryMode: companion.primaryMode ?? "legacy",
      isLegacyCompanion: companion.isLegacyCompanion ?? true,
      legacyRelationshipType: companion.legacyRelationshipType ?? companion.relationshipType,
      showInMainList: companion.showInMainList ?? false,
    };
  }

  const gender = companion.gender ?? (companion.genderDirection === "male" ? "male" : "female");
  const template = getRomanceTemplate(companion.primaryRomanceTemplateId ?? companion.romanceTemplateId) ?? getDefaultRomanceTemplate(gender);
  const blendTraitIds = companion.blendTraitIds ?? template.recommendedBlendTraitIds.slice(0, 2);

  return {
    ...companion,
    primaryMode: "romance",
    isLegacyCompanion: companion.isLegacyCompanion ?? false,
    showInMainList: companion.showInMainList ?? true,
    gender,
    primaryRomanceTemplateId: companion.primaryRomanceTemplateId ?? template.id,
    blendTraitIds,
    promptValidationStatus: companion.promptValidationStatus ?? "valid",
    promptValidationIssues: companion.promptValidationIssues ?? [],
    templateName: companion.templateName ?? template.label,
    templatePrompt: companion.templatePrompt ?? template.templatePrompt,
    blendPromptSummary: companion.blendPromptSummary ?? buildBlendPromptSummary(blendTraitIds),
  };
}

export function loadProviderConfig(): ModelProviderConfig {
  return readJSON(STORAGE_KEYS.config, defaultProviderConfig);
}

export function saveProviderConfig(config: ModelProviderConfig): void {
  writeJSON(STORAGE_KEYS.config, config);
}

export function loadOneBotLocalConfig(): OneBotLocalConfig {
  const stored = readJSON<Partial<OneBotLocalConfig>>(STORAGE_KEYS.oneBotLocalConfig, {});
  return {
    ...defaultOneBotLocalConfig,
    ...stored,
    wakeWords: Array.isArray(stored.wakeWords) ? stored.wakeWords : defaultOneBotLocalConfig.wakeWords,
  };
}

export function saveOneBotLocalConfig(config: OneBotLocalConfig): void {
  writeJSON(STORAGE_KEYS.oneBotLocalConfig, config);
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

export function loadMessagesByCompanionId(activeCompanionId: string): Record<string, ChatMessage[]> {
  const grouped = readJSON<Record<string, ChatMessage[]>>(STORAGE_KEYS.messagesByCompanion, {});
  if (grouped && typeof grouped === "object" && Object.keys(grouped).length > 0) {
    return grouped;
  }

  const legacyMessages = loadMessages();
  if (legacyMessages.length === 0) return {};
  return {
    [activeCompanionId]: legacyMessages,
  };
}

export function saveMessagesByCompanionId(messagesByCompanionId: Record<string, ChatMessage[]>): void {
  writeJSON(STORAGE_KEYS.messagesByCompanion, messagesByCompanionId);
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

  const legacyType = readJSON<LegacyCompanionType>(STORAGE_KEYS.companion, "romantic");
  return legacyCompanionMap[legacyType] ?? "companion-romance";
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

export function loadKnowledgeSources(): KnowledgeSource[] {
  return readJSON<KnowledgeSource[]>(STORAGE_KEYS.knowledgeSources, []).filter(
    (source) => source.status === "active" || source.status === "deleted",
  );
}

export function saveKnowledgeSources(sources: KnowledgeSource[]): void {
  writeJSON(STORAGE_KEYS.knowledgeSources, sources);
}

export function loadKnowledgeChunks(): KnowledgeChunk[] {
  return readJSON<KnowledgeChunk[]>(STORAGE_KEYS.knowledgeChunks, []).filter(
    (chunk) => chunk.status === "active" || chunk.status === "deleted",
  );
}

export function saveKnowledgeChunks(chunks: KnowledgeChunk[]): void {
  writeJSON(STORAGE_KEYS.knowledgeChunks, chunks);
}

export function loadPrivacyNoticeAck(): PrivacyNoticeAck {
  return readJSON<PrivacyNoticeAck>(STORAGE_KEYS.privacyNoticeAck, { acknowledged: false });
}

export function savePrivacyNoticeAck(value: PrivacyNoticeAck): void {
  writeJSON(STORAGE_KEYS.privacyNoticeAck, value);
}

export function loadCompanionOnboardingState(): CompanionOnboardingState {
  const state = readJSON<CompanionOnboardingState>(STORAGE_KEYS.companionOnboarding, { status: "new" });
  if (state.status === "completed" || state.status === "skipped") return state;
  return { status: "new", updatedAt: state.updatedAt };
}

export function saveCompanionOnboardingState(value: CompanionOnboardingState): void {
  writeJSON(STORAGE_KEYS.companionOnboarding, value);
}

export function buildLocalDataExport(params: {
  providerConfig: ModelProviderConfig;
  companions: CompanionProfile[];
  memories: UserMemory[];
  styleSummaries: StyleSummary[];
}): LocalDataExport {
  const { apiKey: _apiKey, ...providerConfigWithoutApiKey } = params.providerConfig;
  return {
    version: "v0.4.2",
    exportedAt: nowISO(),
    providerConfigWithoutApiKey: {
      ...providerConfigWithoutApiKey,
      apiKeyRemoved: true,
    },
    companions: params.companions,
    memories: params.memories,
    styleSummaries: params.styleSummaries,
  };
}

export const localSyncPolicies: SyncPolicy[] = [
  {
    category: "apiKey",
    defaultCapability: "local_only",
    canSync: false,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "BYOK API Key 默认只保存在当前浏览器，本项目不代管商业 Key。",
  },
  {
    category: "chatSessions",
    defaultCapability: "local_only",
    canSync: false,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "原始聊天记录默认不同步，P0 导出也不包含原始聊天。",
  },
  {
    category: "memories",
    defaultCapability: "manual_export",
    canSync: true,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "长期记忆只允许用户主动导出或未来明确授权同步，且需要可查看、可撤回、可删除。",
  },
  {
    category: "styleSummaries",
    defaultCapability: "manual_export",
    canSync: true,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "风格摘要可手动导出；原始导入文本不应默认上传或同步。",
  },
  {
    category: "companions",
    defaultCapability: "manual_export",
    canSync: true,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "伴侣配置可手动导出，未来同步必须由用户主动开启。",
  },
  {
    category: "knowledgeSources",
    defaultCapability: "local_only",
    canSync: false,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "知识库来源默认只在本地保存；后续同步或迁移必须由用户明确授权。",
  },
  {
    category: "knowledgeChunks",
    defaultCapability: "local_only",
    canSync: false,
    requiresExplicitConsent: true,
    mustEncryptAtRest: true,
    notes: "知识库切片只用于本地检索；命中片段只会随当前模型请求发给用户配置的服务商。",
  },
  {
    category: "privacyNotice",
    defaultCapability: "local_only",
    canSync: false,
    requiresExplicitConsent: false,
    mustEncryptAtRest: false,
    notes: "隐私提示确认状态仅用于当前浏览器体验。",
  },
];
