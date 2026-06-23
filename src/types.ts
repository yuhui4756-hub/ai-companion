export type LegacyCompanionType = "friend" | "romantic" | "rational" | "healing" | "roleplay";

export type RelationshipType = "friend" | "light_romance" | "companion" | "support" | "roleplay";

export type TraitCategory =
  | "tone_temperature"
  | "response_pace"
  | "emotion_response"
  | "problem_solving"
  | "intimacy_boundary"
  | "initiative"
  | "humor"
  | "realism_roleplay";

export type CompanionTrait = {
  id: string;
  category: TraitCategory;
  label: string;
  promptText: string;
  conflictWith?: string[];
  recommendedWith?: string[];
  safetyNotes?: string;
};

export type MemoryCategory =
  | "identity"
  | "preference"
  | "goal"
  | "event"
  | "emotion_pattern"
  | "boundary"
  | "taboo"
  | "relationship"
  | "style_preference";

export type MemoryImportance = 1 | 2 | 3;

export type MemoryScope = "global" | "companion";
export type MemorySource = "chat" | "manual" | "import_summary";
export type MemorySensitivity = "normal" | "sensitive";
export type MemoryStatus = "active" | "superseded" | "expired" | "deleted";
export type MemoryAction = "create" | "merge" | "replace" | "skip" | "needs_review";

export type CompanionProfile = {
  id: string;
  name: string;
  relationshipType: RelationshipType;
  traitIds: string[];
  customPersonalityText?: string;
  intimacyBoundary?: string;
  responsePace?: string;
  problemSolvingStyle?: string;
  activeStyleSummaryId?: string;
  boundaryNotes?: string;
  createdAt: string;
  updatedAt: string;
};

export type UserMemory = {
  id: string;
  scope: MemoryScope;
  companionId?: string;
  category: MemoryCategory;
  content: string;
  source: MemorySource;
  confidence: number;
  importance: MemoryImportance;
  sensitivity: MemorySensitivity;
  status: MemoryStatus;
  sourceMessageId?: string;
  supersededById?: string;
  expiresAt?: string;
  createdAt: string;
  updatedAt: string;
};

export type MemoryCandidate = {
  id: string;
  content: string;
  suggestedScope: MemoryScope;
  suggestedCompanionId?: string;
  category: MemoryCategory;
  sourceSnippet: string;
  confidence: number;
  sensitivity: MemorySensitivity;
  suggestedAction: MemoryAction;
  reason: string;
  relatedMemoryId?: string;
};

export type StyleSummary = {
  id: string;
  name: string;
  sourceType: "imported_chat";
  summaryText: string;
  tone: string;
  pace: string;
  addressing: string;
  emotionResponse: string;
  interactionPatterns: string;
  forbiddenIdentityClaims: string[];
  boundCompanionIds: string[];
  userReviewed: boolean;
  createdAt: string;
  updatedAt: string;
};

export type ModelProviderConfig = {
  providerName: string;
  baseURL: string;
  apiKey: string;
  model: string;
};

export type PrivacyNoticeAck = {
  acknowledged: boolean;
  acknowledgedAt?: string;
};

export type ChatRole = "system" | "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: Exclude<ChatRole, "system">;
  content: string;
  createdAt: string;
};

export type OpenAIChatMessage = {
  role: ChatRole;
  content: string;
};

export type AppView = "chat" | "companion" | "settings" | "memory" | "style";
