import type { ChatMessage, CompanionType, ModelProviderConfig, UserMemory } from "../types";

const STORAGE_KEYS = {
  config: "ai-companion:provider-config",
  memories: "ai-companion:memories",
  messages: "ai-companion:messages",
  companion: "ai-companion:companion",
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

export function loadProviderConfig(): ModelProviderConfig {
  return readJSON(STORAGE_KEYS.config, defaultProviderConfig);
}

export function saveProviderConfig(config: ModelProviderConfig): void {
  writeJSON(STORAGE_KEYS.config, config);
}

export function loadMemories(): UserMemory[] {
  return readJSON(STORAGE_KEYS.memories, []);
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

export function loadCompanionType(): CompanionType {
  return readJSON(STORAGE_KEYS.companion, "friend");
}

export function saveCompanionType(type: CompanionType): void {
  writeJSON(STORAGE_KEYS.companion, type);
}
