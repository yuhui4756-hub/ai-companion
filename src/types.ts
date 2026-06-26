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
export type ProactiveLevel = "low" | "medium" | "high";
export type CompanionSource = "default" | "manual" | "onboarding";
export type PrimaryMode = "romance" | "legacy";
export type RomanceGender = "female" | "male";
export type RomanceTemplateId =
  | "female_soft_cute"
  | "female_mature_sister"
  | "female_tsundere"
  | "female_sweet_girl"
  | "female_cool_caring"
  | "female_yandere_safe_edge"
  | "male_gentle_boyfriend"
  | "male_dominant_caring"
  | "male_sunny_boy"
  | "male_mature_brother"
  | "male_roast_but_spoil"
  | "male_cool_god";
export type BlendTraitId =
  | "soft_comfort"
  | "playful_tease"
  | "cute_clingy"
  | "jealous_light"
  | "mature_hold"
  | "cool_restraint"
  | "tsundere_mood"
  | "dominant_care";
export type PromptValidationStatus = "valid" | "warning" | "blocked";
export type PromptValidationIssue = {
  code:
    | "secret"
    | "sensitive_identity"
    | "impersonation"
    | "fake_real_world_action"
    | "explicit_adult"
    | "minor_sexual"
    | "danger_illegal"
    | "self_harm_or_harm"
    | "coercive_dependency";
  message: string;
  severity: "warning" | "blocked";
};

export type RomanceTemplate = {
  id: RomanceTemplateId;
  gender: RomanceGender;
  label: string;
  baseTone: string;
  templatePrompt: string;
  recommendedBlendTraitIds: BlendTraitId[];
  defaultProactiveLevel?: ProactiveLevel;
  defaultTraits?: string[];
};

export type BlendTrait = {
  id: BlendTraitId;
  label: string;
  sceneHint: string;
  promptHint: string;
  safetyNotes?: string;
};

export type LegacyRomanceStyle =
  | "gentle_clingy"
  | "tsundere"
  | "mature_flirty"
  | "friend_to_love"
  | "sunny_boy"
  | "cool_restrained"
  | "mature_partner"
  | "neutral_soft"
  | "ambiguous"
  | "soulmate"
  | "quiet_guardian"
  | "custom_written"
  | "custom_blank";

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
  proactiveLevel?: ProactiveLevel;
  source?: CompanionSource;
  openingMessage?: string;
  primaryMode?: PrimaryMode;
  gender?: RomanceGender;
  primaryRomanceTemplateId?: RomanceTemplateId;
  blendTraitIds?: BlendTraitId[];
  promptValidationStatus?: PromptValidationStatus;
  promptValidationIssues?: PromptValidationIssue[];
  genderDirection?: string;
  romanceTemplateId?: string;
  templateName?: string;
  templatePrompt?: string;
  blendPromptSummary?: string;
  customSystemPrompt?: string;
  userNickname?: string;
  romanceStyle?: LegacyRomanceStyle | RomanceTemplateId;
  isLegacyCompanion?: boolean;
  legacyRelationshipType?: RelationshipType;
  showInMainList?: boolean;
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

export type LocalDataExport = {
  version: string;
  exportedAt: string;
  providerConfigWithoutApiKey: Omit<ModelProviderConfig, "apiKey"> & { apiKeyRemoved: true };
  companions: CompanionProfile[];
  memories: UserMemory[];
  styleSummaries: StyleSummary[];
};

export type LocalDataCategory =
  | "apiKey"
  | "chatSessions"
  | "memories"
  | "styleSummaries"
  | "companions"
  | "privacyNotice";

export type SyncCapability = "local_only" | "manual_export" | "user_authorized_sync";

export type SyncPolicy = {
  category: LocalDataCategory;
  defaultCapability: SyncCapability;
  canSync: boolean;
  requiresExplicitConsent: boolean;
  mustEncryptAtRest: boolean;
  notes: string;
};

export type OnboardingStatus = "new" | "skipped" | "completed";
export type OnboardingStep = 0 | 1 | 2 | 3;

export type CompanionOnboardingState = {
  status: OnboardingStatus;
  updatedAt?: string;
};

export type OnboardingAnswer = {
  companionshipDirection?: "listen" | "casual" | "clarify" | "encourage" | "roleplay" | "custom";
  directionCustomText?: string;
  toneFeeling?: "gentle_slow" | "natural_friend" | "direct_warm" | "lively" | "quiet" | "custom";
  toneCustomText?: string;
  proactiveLevel?: ProactiveLevel;
  companionName?: string;
};

export type RomanceCreationStep = 0 | 1 | 2 | 3 | 4;

export type RomanceCreationDraft = {
  gender?: RomanceGender;
  primaryRomanceTemplateId?: RomanceTemplateId;
  blendTraitIds?: BlendTraitId[];
  customSystemPromptDraft?: string;
  customSystemPrompt?: string;
  companionName?: string;
  userNickname?: string;
  proactiveLevel?: ProactiveLevel;
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
