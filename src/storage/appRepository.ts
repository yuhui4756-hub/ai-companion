import type {
  ChatMessage,
  CompanionOnboardingState,
  CompanionProfile,
  KnowledgeChunk,
  KnowledgeSource,
  ModelProviderConfig,
  PrivacyNoticeAck,
  StyleSummary,
  UserMemory,
} from "../types";
import type { OneBotLocalConfig } from "../channel-adapter/types";
import {
  loadActiveCompanionId,
  loadCompanionOnboardingState,
  loadCompanions,
  loadKnowledgeChunks,
  loadKnowledgeSources,
  loadMemories,
  loadMessagesByCompanionId,
  loadOneBotLocalConfig,
  loadPrivacyNoticeAck,
  loadProviderConfig,
  loadStyleSummaries,
  saveActiveCompanionId,
  saveCompanionOnboardingState,
  saveCompanions,
  saveKnowledgeChunks,
  saveKnowledgeSources,
  saveMemories,
  saveMessagesByCompanionId,
  saveOneBotLocalConfig,
  savePrivacyNoticeAck,
  saveProviderConfig,
  saveStyleSummaries,
} from "./localStorage";

export type MessagesByCompanionId = Record<string, ChatMessage[]>;

export type AppRepository = {
  loadProviderConfig: () => ModelProviderConfig;
  saveProviderConfig: (config: ModelProviderConfig) => void;
  loadCompanions: () => CompanionProfile[];
  saveCompanions: (companions: CompanionProfile[]) => void;
  loadActiveCompanionId: () => string;
  saveActiveCompanionId: (id: string) => void;
  loadMessagesByCompanionId: (activeCompanionId: string) => MessagesByCompanionId;
  saveMessagesByCompanionId: (messagesByCompanionId: MessagesByCompanionId) => void;
  loadMemories: () => UserMemory[];
  saveMemories: (memories: UserMemory[]) => void;
  loadStyleSummaries: () => StyleSummary[];
  saveStyleSummaries: (summaries: StyleSummary[]) => void;
  loadKnowledgeSources: () => KnowledgeSource[];
  saveKnowledgeSources: (sources: KnowledgeSource[]) => void;
  loadKnowledgeChunks: () => KnowledgeChunk[];
  saveKnowledgeChunks: (chunks: KnowledgeChunk[]) => void;
  loadPrivacyNoticeAck: () => PrivacyNoticeAck;
  savePrivacyNoticeAck: (value: PrivacyNoticeAck) => void;
  loadCompanionOnboardingState: () => CompanionOnboardingState;
  saveCompanionOnboardingState: (value: CompanionOnboardingState) => void;
  loadOneBotLocalConfig: () => OneBotLocalConfig;
  saveOneBotLocalConfig: (config: OneBotLocalConfig) => void;
};

// Future SQLite storage can implement this interface while keeping localStorage as migration fallback.
export const appRepository: AppRepository = {
  loadProviderConfig,
  saveProviderConfig,
  loadCompanions,
  saveCompanions,
  loadActiveCompanionId,
  saveActiveCompanionId,
  loadMessagesByCompanionId,
  saveMessagesByCompanionId,
  loadMemories,
  saveMemories,
  loadStyleSummaries,
  saveStyleSummaries,
  loadKnowledgeSources,
  saveKnowledgeSources,
  loadKnowledgeChunks,
  saveKnowledgeChunks,
  loadPrivacyNoticeAck,
  savePrivacyNoticeAck,
  loadCompanionOnboardingState,
  saveCompanionOnboardingState,
  loadOneBotLocalConfig,
  saveOneBotLocalConfig,
};
