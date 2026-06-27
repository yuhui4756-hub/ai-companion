import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Bot,
  Brain,
  Check,
  ChevronLeft,
  ChevronRight,
  Heart,
  KeyRound,
  MessageCircle,
  PenLine,
  Plus,
  Save,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRoundCog,
} from "lucide-react";
import {
  companionTraits,
  getCompanionProfile,
  getTraitConflictLabels,
  getTraitsByIds,
  isDefaultCompanionId,
  relationshipLabels,
} from "./companion/profiles";
import {
  proactiveOptions,
} from "./companion/onboarding";
import { buildRomanceReconnectMessage, isLightRomanceCompanion } from "./companion/romance";
import {
  blendTraits,
  buildBlendPromptSummary,
  createRomanceCompanionFromDraft,
  getDefaultRomanceTemplate,
  getRomanceTemplate,
  getRomanceTemplatesByGender,
  isRomanceCompanion,
} from "./companion/romanceTemplates";
import { validateCustomSystemPrompt } from "./companion/promptValidation";
import { sendCompanionMessage } from "./chat-engine/chat";
import {
  applyMemoryCandidates,
  createMemory,
  generateMemoryCandidates,
  isMemoryInjectable,
  memoryCategoryLabels,
  memoryScopeLabels,
} from "./memory/memory";
import { ModelProviderError } from "./model-provider/openai";
import {
  defaultProviderConfig,
  loadActiveCompanionId,
  loadCompanions,
  loadMemories,
  loadMessagesByCompanionId,
  loadCompanionOnboardingState,
  loadPrivacyNoticeAck,
  loadProviderConfig,
  loadStyleSummaries,
  saveActiveCompanionId,
  buildLocalDataExport,
  saveCompanions,
  saveMemories,
  saveMessagesByCompanionId,
  saveCompanionOnboardingState,
  savePrivacyNoticeAck,
  saveProviderConfig,
  saveStyleSummaries,
} from "./storage/localStorage";
import { buildStyleSummaryFromInput, createEmptyStyleSummary, getBoundStyleSummary } from "./style-reference/styleSummary";
import type {
  AppView,
  ChatMessage,
  CompanionProfile,
  MemoryCandidate,
  MemoryCategory,
  MemoryImportance,
  MemoryScope,
  ModelProviderConfig,
  RomanceCreationDraft,
  RomanceCreationStep,
  RelationshipType,
  StyleSummary,
  UserMemory,
  BlendTraitId,
  RomanceGender,
} from "./types";

const memoryCategories = Object.entries(memoryCategoryLabels) as Array<[MemoryCategory, string]>;
const importanceOptions: MemoryImportance[] = [1, 2, 3];
const relationshipOptions = Object.entries(relationshipLabels) as Array<[RelationshipType, string]>;
const memoryVisibleActions = new Set(["create", "merge", "replace"]);
const romanceGenderOptions: Array<{ value: RomanceGender; label: string; description: string }> = [
  {
    value: "female",
    label: "女友方向",
    description: "更偏柔软、亲近、撒娇、吃醋和情绪陪伴，也可以成熟或清冷。",
  },
  {
    value: "male",
    label: "男友方向",
    description: "更偏稳定、保护感、直球、宠溺和陪你一起扛事，也可以阳光或清冷。",
  },
];
const initialPrivacyNoticeAck = loadPrivacyNoticeAck();
const initialOnboardingState = loadCompanionOnboardingState();
const initialActiveCompanionId = loadActiveCompanionId();
const initialMessagesByCompanionId = loadMessagesByCompanionId(initialActiveCompanionId);
const shouldAutoOpenOnboarding =
  initialOnboardingState.status === "new" && Object.values(initialMessagesByCompanionId).every((messages) => messages.length === 0);
const providerPresets = [
  {
    id: "deepseek-flash",
    label: "DeepSeek V4 Flash",
    providerName: "DeepSeek",
    baseURL: "https://api.deepseek.com",
    model: "deepseek-v4-flash",
    note: "适合先做快速真实模型验收，模型名仍可手动修改。",
  },
  {
    id: "deepseek-pro",
    label: "DeepSeek V4 Pro",
    providerName: "DeepSeek",
    baseURL: "https://api.deepseek.com",
    model: "deepseek-v4-pro",
    note: "用于更强回复质量验收，费用和权限以用户账户为准。",
  },
  {
    id: "openai-compatible",
    label: "OpenAI 兼容",
    providerName: "OpenAI 兼容接口",
    baseURL: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
    note: "通用 OpenAI Chat Completions 兼容格式，可替换为其他服务商。",
  },
] as const;

function makeMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
  };
}

function getFriendlyError(error: unknown): string {
  if (error instanceof ModelProviderError) {
    return error.message;
  }
  if (error instanceof Error) {
    return `发生了未预期错误：${error.message}`;
  }
  return "发生了未预期错误，请稍后重试。";
}

function companionDisplayName(companion: CompanionProfile): string {
  return companion.name.trim() || "未命名伴侣";
}

function nextOnboardingState(status: "skipped" | "completed") {
  return {
    status,
    updatedAt: new Date().toISOString(),
  };
}

function splitMessageParts(content: string): string[] {
  return content
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function splitAssistantReply(content: string): string[] {
  const paragraphs = splitMessageParts(content);
  if (paragraphs.length > 1) return paragraphs;

  const trimmed = content.trim();
  if (!trimmed) return [];

  if (trimmed.length < 72) return [trimmed];

  const sentenceParts = Array.from(trimmed.matchAll(/[^。！？!?]+[。！？!?]?/g))
    .map((match) => match[0].trim())
    .filter(Boolean);

  if (sentenceParts.length <= 1) return [trimmed];

  const segments: string[] = [];
  let current = "";
  for (const sentence of sentenceParts) {
    const next = current ? `${current}${sentence}` : sentence;
    if (next.length > 90 && current) {
      segments.push(current);
      current = sentence;
    } else {
      current = next;
    }
  }
  if (current) segments.push(current);
  return segments;
}

function getReplySegmentDelay(segment: string, index: number): number {
  const baseDelay = index === 0 ? 320 : 260;
  const lengthDelay = segment.length * 18;
  return Math.min(1800, Math.max(300, baseDelay + lengthDelay));
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export default function App() {
  const [activeView, setActiveView] = useState<AppView>("chat");
  const [companions, setCompanions] = useState<CompanionProfile[]>(() => loadCompanions());
  const [activeCompanionId, setActiveCompanionId] = useState<string>(() => initialActiveCompanionId);
  const [providerConfig, setProviderConfig] = useState<ModelProviderConfig>(() => loadProviderConfig());
  const [messagesByCompanionId, setMessagesByCompanionId] = useState<Record<string, ChatMessage[]>>(
    () => initialMessagesByCompanionId,
  );
  const [memories, setMemories] = useState<UserMemory[]>(() => loadMemories());
  const [styleSummaries, setStyleSummaries] = useState<StyleSummary[]>(() => loadStyleSummaries());
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isAssistantTyping, setIsAssistantTyping] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);
  const [memoryDraft, setMemoryDraft] = useState({
    scope: "global" as MemoryScope,
    category: "preference" as MemoryCategory,
    content: "",
    importance: 2 as MemoryImportance,
  });
  const [memoryFilter, setMemoryFilter] = useState<MemoryScope | "all">("all");
  const [latestCandidates, setLatestCandidates] = useState<MemoryCandidate[]>([]);
  const [styleImportText, setStyleImportText] = useState("");
  const [privacyNoticeAck, setPrivacyNoticeAck] = useState(() => initialPrivacyNoticeAck);
  const [isPrivacyNoticeOpen, setIsPrivacyNoticeOpen] = useState(() => !initialPrivacyNoticeAck.acknowledged);
  const [dataActionMessage, setDataActionMessage] = useState("");
  const [onboardingState, setOnboardingState] = useState(() => initialOnboardingState);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(() => shouldAutoOpenOnboarding);
  const [isOnboardingManuallyOpened, setIsOnboardingManuallyOpened] = useState(false);
  const [onboardingStep, setOnboardingStep] = useState<RomanceCreationStep>(0);
  const [onboardingDraft, setOnboardingDraft] = useState<RomanceCreationDraft>(() => ({
    gender: "female",
    primaryRomanceTemplateId: getDefaultRomanceTemplate("female").id,
    blendTraitIds: getDefaultRomanceTemplate("female").recommendedBlendTraitIds.slice(0, 2),
    proactiveLevel: getDefaultRomanceTemplate("female").defaultProactiveLevel ?? "medium",
  }));
  const [promptDraftByCompanionId, setPromptDraftByCompanionId] = useState<Record<string, string>>({});
  const [companionDraft, setCompanionDraft] = useState<CompanionProfile | null>(null);
  const [isMemoryAddOpen, setIsMemoryAddOpen] = useState(false);
  const [stylePanelMode, setStylePanelMode] = useState<"list" | "import" | "new">("list");
  const [isTraitModalOpen, setIsTraitModalOpen] = useState(false);
  const [isRomanceReconnectSuppressed, setIsRomanceReconnectSuppressed] = useState(false);
  const responseSequenceRef = useRef(0);

  const activeCompanion = useMemo(
    () => getCompanionProfile(activeCompanionId, companions),
    [activeCompanionId, companions],
  );
  const messages = messagesByCompanionId[activeCompanion.id] ?? [];
  const activeStyleSummary = useMemo(
    () => getBoundStyleSummary(styleSummaries, activeCompanion.id, activeCompanion.activeStyleSummaryId),
    [activeCompanion, styleSummaries],
  );
  const activeTraits = useMemo(() => getTraitsByIds(activeCompanion.traitIds), [activeCompanion.traitIds]);
  const traitConflicts = useMemo(() => getTraitConflictLabels(activeCompanion.traitIds), [activeCompanion.traitIds]);
  const visibleCandidates = latestCandidates.filter((candidate) => memoryVisibleActions.has(candidate.suggestedAction));
  const visibleMemories = memories.filter((memory) => {
    if (memoryFilter !== "all" && memory.scope !== memoryFilter) return false;
    if (memory.scope === "companion" && memory.companionId !== activeCompanion.id) return false;
    return memory.status !== "deleted";
  });
  const mainCompanions = companions.filter((companion) => isRomanceCompanion(companion) || companion.showInMainList);
  const hiddenCompanions = companions.filter((companion) => !mainCompanions.some((profile) => profile.id === companion.id));
  const hasUserCreatedCompanion = useMemo(
    () => companions.some((companion) => companion.source !== "default" && !isDefaultCompanionId(companion.id)),
    [companions],
  );
  const shouldShowOnboarding =
    isOnboardingOpen &&
    !isPrivacyNoticeOpen &&
    (isOnboardingManuallyOpened ||
      (onboardingState.status === "new" && !hasUserCreatedCompanion && messages.length === 0));
  const selectedRomanceTemplate = useMemo(
    () => getRomanceTemplate(onboardingDraft.primaryRomanceTemplateId),
    [onboardingDraft.primaryRomanceTemplateId],
  );
  const romancePromptValidation = useMemo(
    () => validateCustomSystemPrompt(onboardingDraft.customSystemPromptDraft ?? ""),
    [onboardingDraft.customSystemPromptDraft],
  );
  const romanceBlendSummary = useMemo(
    () => buildBlendPromptSummary(onboardingDraft.blendTraitIds ?? []),
    [onboardingDraft.blendTraitIds],
  );
  const editorCompanion = companionDraft ?? activeCompanion;
  const activePromptDraft =
    promptDraftByCompanionId[activeCompanion.id] ??
    activeCompanion.customSystemPrompt ??
    activeCompanion.templatePrompt ??
    (isRomanceCompanion(activeCompanion)
      ? getRomanceTemplate(activeCompanion.primaryRomanceTemplateId).templatePrompt
      : activeCompanion.customPersonalityText ?? "");
  const editorPromptDraft =
    promptDraftByCompanionId[editorCompanion.id] ??
    editorCompanion.customSystemPrompt ??
    editorCompanion.templatePrompt ??
    (isRomanceCompanion(editorCompanion)
      ? getRomanceTemplate(editorCompanion.primaryRomanceTemplateId).templatePrompt
      : editorCompanion.customPersonalityText ?? "");
  const editorPromptValidation = useMemo(
    () => validateCustomSystemPrompt(editorPromptDraft),
    [editorPromptDraft],
  );
  const editorPromptIssues =
    editorPromptValidation.issues.length > 0 ? editorPromptValidation.issues : editorCompanion.promptValidationIssues ?? [];

  useEffect(() => saveActiveCompanionId(activeCompanion.id), [activeCompanion.id]);
  useEffect(() => saveCompanions(companions), [companions]);
  useEffect(() => saveMessagesByCompanionId(messagesByCompanionId), [messagesByCompanionId]);
  useEffect(() => saveMemories(memories), [memories]);
  useEffect(() => saveStyleSummaries(styleSummaries), [styleSummaries]);
  useEffect(() => {
    responseSequenceRef.current += 1;
    setIsSending(false);
    setIsAssistantTyping(false);
  }, [activeCompanion.id]);
  useEffect(() => {
    if (shouldShowOnboarding || isSending || isAssistantTyping || isRomanceReconnectSuppressed) return;
    if (messages.length === 0) return;
    const reconnectMessage = buildRomanceReconnectMessage(activeCompanion, messages);
    if (!reconnectMessage) return;
    setCompanionMessages(activeCompanion.id, (current) => {
      if (current !== messages) return current;
      return [...current, makeMessage("assistant", reconnectMessage)];
    });
  }, [activeCompanion, messages, shouldShowOnboarding, isSending, isAssistantTyping, isRomanceReconnectSuppressed]);

  function updateProviderConfig(field: keyof ModelProviderConfig, value: string) {
    setSettingsSaved(false);
    setDataActionMessage("");
    setProviderConfig((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function applyProviderPreset(preset: (typeof providerPresets)[number]) {
    setSettingsSaved(false);
    setDataActionMessage("已套用预设。预设不会填写 API Key，请确认模型名后保存。");
    setProviderConfig((current) => ({
      ...current,
      providerName: preset.providerName,
      baseURL: preset.baseURL,
      model: preset.model,
      apiKey: current.apiKey,
    }));
  }

  function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveProviderConfig(providerConfig);
    setSettingsSaved(true);
    setError("");
  }

  function updateCompanion(id: string, patch: Partial<CompanionProfile>) {
    setCompanions((current) =>
      current.map((companion) =>
        companion.id === id ? { ...companion, ...patch, updatedAt: new Date().toISOString() } : companion,
      ),
    );
  }

  function setCompanionMessages(
    companionId: string,
    nextMessages:
      | ChatMessage[]
      | ((currentMessages: ChatMessage[], allMessages: Record<string, ChatMessage[]>) => ChatMessage[]),
  ) {
    setMessagesByCompanionId((current) => {
      const currentMessages = current[companionId] ?? [];
      const resolvedMessages =
        typeof nextMessages === "function" ? nextMessages(currentMessages, current) : nextMessages;
      return {
        ...current,
        [companionId]: resolvedMessages,
      };
    });
  }

  function updateEditorCompanion(patch: Partial<CompanionProfile>) {
    if (companionDraft) {
      setCompanionDraft((current) => (current ? { ...current, ...patch, updatedAt: new Date().toISOString() } : current));
      return;
    }
    updateCompanion(editorCompanion.id, patch);
  }

  function startCompanionDraft() {
    const draft = createRomanceCompanionFromDraft({ gender: "female" }, "manual");
    setCompanionDraft({
      ...draft,
      id: `draft-${crypto.randomUUID()}`,
      name: "",
      customSystemPrompt: draft.templatePrompt,
      showInMainList: true,
    });
    setActiveView("companion");
  }

  function cancelCompanionDraft() {
    setPromptDraftByCompanionId((current) => {
      if (!companionDraft) return current;
      const next = { ...current };
      delete next[companionDraft.id];
      return next;
    });
    setCompanionDraft(null);
  }

  function saveCompanionDraft() {
    if (!companionDraft) return;
    const promptText =
      promptDraftByCompanionId[companionDraft.id] ?? companionDraft.customSystemPrompt ?? companionDraft.templatePrompt ?? "";
    const validation = validateCustomSystemPrompt(promptText);
    if (validation.status === "blocked") {
      setCompanionDraft((current) =>
        current
          ? {
              ...current,
              promptValidationStatus: validation.status,
              promptValidationIssues: validation.issues,
              updatedAt: new Date().toISOString(),
            }
          : current,
      );
      return;
    }

    const savedCompanion: CompanionProfile = {
      ...companionDraft,
      id: `companion-romance-${crypto.randomUUID()}`,
      name: companionDraft.name.trim() || (companionDraft.gender === "male" ? "阿澈" : "予安"),
      customSystemPrompt: promptText.trim() || undefined,
      promptValidationStatus: validation.status,
      promptValidationIssues: validation.issues,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setCompanions((current) => [savedCompanion, ...current]);
    setActiveCompanionId(savedCompanion.id);
    setIsRomanceReconnectSuppressed(true);
    setCompanionDraft(null);
  }

  function resetRomanceDraft(gender: RomanceGender = "female") {
    const template = getDefaultRomanceTemplate(gender);
    setOnboardingDraft({
      gender,
      primaryRomanceTemplateId: template.id,
      blendTraitIds: template.recommendedBlendTraitIds.slice(0, 2),
      proactiveLevel: template.defaultProactiveLevel ?? "medium",
    });
  }

  function skipOnboarding() {
    const companion = createRomanceCompanionFromDraft({ gender: "female" });
    setCompanions((current) => [companion, ...current]);
    setActiveCompanionId(companion.id);
    setIsRomanceReconnectSuppressed(true);
    const state = nextOnboardingState("skipped");
    setOnboardingState(state);
    saveCompanionOnboardingState(state);
    setIsOnboardingOpen(false);
    setIsOnboardingManuallyOpened(false);
    setOnboardingStep(0);
    setActiveView("chat");
  }

  function goNextOnboardingStep() {
    if (onboardingStep === 3 && romancePromptValidation.status === "blocked") return;
    setOnboardingStep((current) => Math.min(current + 1, 4) as RomanceCreationStep);
  }

  function goPreviousOnboardingStep() {
    setOnboardingStep((current) => Math.max(current - 1, 0) as RomanceCreationStep);
  }

  function finishOnboarding() {
    const validation = validateCustomSystemPrompt(onboardingDraft.customSystemPromptDraft ?? "");
    if (validation.status === "blocked") return;
    const companion = createRomanceCompanionFromDraft(onboardingDraft);
    setCompanions((current) => [companion, ...current]);
    setActiveCompanionId(companion.id);
    setIsRomanceReconnectSuppressed(true);
    const state = nextOnboardingState("completed");
    setOnboardingState(state);
    saveCompanionOnboardingState(state);
    setIsOnboardingOpen(false);
    setIsOnboardingManuallyOpened(false);
    setOnboardingStep(0);
    setActiveView("chat");
  }

  function toggleBlendTrait(traitId: BlendTraitId) {
    setOnboardingDraft((current) => {
      const currentIds = current.blendTraitIds ?? [];
      if (currentIds.includes(traitId)) {
        return { ...current, blendTraitIds: currentIds.filter((id) => id !== traitId) };
      }
      if (currentIds.length >= 3) return current;
      return { ...current, blendTraitIds: [...currentIds, traitId] };
    });
  }

  function saveActiveCompanionPromptDraft() {
    const validation = validateCustomSystemPrompt(activePromptDraft);
    if (validation.status === "blocked") {
      updateCompanion(activeCompanion.id, {
        promptValidationStatus: validation.status,
        promptValidationIssues: validation.issues,
      });
      return;
    }
    updateCompanion(activeCompanion.id, {
      customSystemPrompt: activePromptDraft.trim() || undefined,
      promptValidationStatus: validation.status,
      promptValidationIssues: validation.issues,
    });
  }

  function restoreActiveCompanionTemplatePrompt() {
    const templatePrompt = isRomanceCompanion(editorCompanion)
      ? editorCompanion.templatePrompt ?? getRomanceTemplate(editorCompanion.primaryRomanceTemplateId).templatePrompt
      : editorCompanion.customPersonalityText ?? "";
    setPromptDraftByCompanionId((current) => ({ ...current, [editorCompanion.id]: templatePrompt }));
    updateEditorCompanion({
      customSystemPrompt: undefined,
      promptValidationStatus: "valid",
      promptValidationIssues: [],
    });
  }

  function setCompanionMainListVisibility(id: string, showInMainList: boolean) {
    updateCompanion(id, { showInMainList });
  }

  function toggleTrait(traitId: string) {
    const exists = editorCompanion.traitIds.includes(traitId);
    const nextTraitIds = exists
      ? editorCompanion.traitIds.filter((id) => id !== traitId)
      : [...editorCompanion.traitIds, traitId].slice(0, 6);
    updateEditorCompanion({ traitIds: nextTraitIds });
  }

  function toggleEditorBlendTrait(traitId: BlendTraitId) {
    const currentIds = editorCompanion.blendTraitIds ?? [];
    const nextIds = currentIds.includes(traitId)
      ? currentIds.filter((id) => id !== traitId)
      : currentIds.length >= 3
        ? currentIds
        : [...currentIds, traitId];
    updateEditorCompanion({
      blendTraitIds: nextIds,
      blendPromptSummary: buildBlendPromptSummary(nextIds),
    });
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const userInput = input.trim();
    if (!userInput || isSending || isAssistantTyping) return;
    const sendingCompanion = activeCompanion;
    const sendingCompanionId = sendingCompanion.id;
    const sendingMessages = messages;
    const responseSequence = responseSequenceRef.current + 1;
    responseSequenceRef.current = responseSequence;

    const userMessage = makeMessage("user", userInput);
    const nextMessages = [...sendingMessages, userMessage];
    const candidates = generateMemoryCandidates(userInput, memories, sendingCompanionId);
    const actionableCandidates = candidates.filter((candidate) => memoryVisibleActions.has(candidate.suggestedAction));
    const nextMemories = applyMemoryCandidates(actionableCandidates, memories);

    setCompanionMessages(sendingCompanionId, nextMessages);
    setLatestCandidates(candidates);
    if (nextMemories !== memories) {
      setMemories(nextMemories);
    }
    setInput("");
    setError("");
    setIsRomanceReconnectSuppressed(false);
    setIsSending(true);
    setIsAssistantTyping(true);

    try {
      const reply = await sendCompanionMessage({
        config: providerConfig,
        companion: sendingCompanion,
        styleSummary: activeStyleSummary,
        memories: nextMemories,
        history: sendingMessages,
        userInput,
      });
      setIsSending(false);
      const segments = splitAssistantReply(reply);
      if (segments.length === 0) {
        setIsAssistantTyping(false);
        return;
      }
      for (const [index, segment] of segments.entries()) {
        await wait(getReplySegmentDelay(segment, index));
        if (responseSequenceRef.current !== responseSequence || activeCompanionId !== sendingCompanionId) return;
        setCompanionMessages(sendingCompanionId, (current) => [...current, makeMessage("assistant", segment)]);
      }
    } catch (err) {
      setError(getFriendlyError(err));
    } finally {
      if (responseSequenceRef.current === responseSequence) {
        setIsSending(false);
        setIsAssistantTyping(false);
      }
    }
  }

  function handleAddMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!memoryDraft.content.trim()) return;

    setMemories((current) => [
      createMemory({
        scope: memoryDraft.scope,
        companionId: memoryDraft.scope === "companion" ? activeCompanion.id : undefined,
        category: memoryDraft.category,
        content: memoryDraft.content,
        importance: memoryDraft.importance,
        source: "manual",
        confidence: 1,
      }),
      ...current,
    ]);
    setMemoryDraft({
      ...memoryDraft,
      content: "",
    });
  }

  function updateMemory(id: string, patch: Partial<Pick<UserMemory, "scope" | "category" | "content" | "importance" | "status">>) {
    setMemories((current) =>
      current.map((memory) =>
        memory.id === id
          ? {
              ...memory,
              ...patch,
              companionId:
                patch.scope === "global"
                  ? undefined
                  : patch.scope === "companion"
                    ? activeCompanion.id
                    : memory.companionId,
              updatedAt: new Date().toISOString(),
            }
          : memory,
      ),
    );
  }

  function deleteMemory(id: string) {
    setMemories((current) =>
      current.map((memory) =>
        memory.id === id ? { ...memory, status: "deleted", updatedAt: new Date().toISOString() } : memory,
      ),
    );
  }

  function clearChat() {
    responseSequenceRef.current += 1;
    setCompanionMessages(activeCompanion.id, []);
    setError("");
    setIsSending(false);
    setIsAssistantTyping(false);
    setIsRomanceReconnectSuppressed(true);
  }

  function clearLocalApiKey() {
    if (!window.confirm("清除后需要重新填写 API Key 才能聊天。确定清除本地 API Key 吗？")) return;
    const nextConfig = { ...providerConfig, apiKey: "" };
    setProviderConfig(nextConfig);
    saveProviderConfig(nextConfig);
    setSettingsSaved(false);
    setError("");
    setDataActionMessage("已清除本地 API Key。服务商名称、baseURL 和 model 已保留。");
  }

  function clearCurrentChatRecords() {
    if (!window.confirm("确定清空当前聊天记录吗？长期记忆、伴侣配置和风格摘要不会被删除。")) return;
    responseSequenceRef.current += 1;
    setCompanionMessages(activeCompanion.id, []);
    setLatestCandidates([]);
    setError("");
    setIsSending(false);
    setIsAssistantTyping(false);
    setIsRomanceReconnectSuppressed(true);
    setDataActionMessage("已清空当前聊天记录，长期记忆和伴侣配置仍保留。");
  }

  function clearLongTermMemories() {
    if (!window.confirm("确定清除全部长期记忆吗？清除后它们不会再影响后续回复。")) return;
    setMemories([]);
    saveMemories([]);
    setLatestCandidates([]);
    setDataActionMessage("已清除全部长期记忆。聊天记录中的原始消息不会因此删除。");
  }

  function clearAllStyleSummaries() {
    if (!window.confirm("确定清除全部风格摘要吗？所有伴侣绑定的风格参考也会解除。")) return;
    const now = new Date().toISOString();
    const nextCompanions = companions.map((companion) =>
      companion.activeStyleSummaryId ? { ...companion, activeStyleSummaryId: undefined, updatedAt: now } : companion,
    );
    setStyleSummaries([]);
    setCompanions(nextCompanions);
    saveStyleSummaries([]);
    saveCompanions(nextCompanions);
    setDataActionMessage("已清除全部风格摘要，并解除伴侣绑定。");
  }

  function exportLocalData() {
    const payload = buildLocalDataExport({
      providerConfig,
      companions,
      memories,
      styleSummaries,
    });
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ai-companion-local-data-v0.4.2-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setDataActionMessage("已导出本地配置和记忆 JSON。导出文件不包含 API Key，也不包含原始聊天记录。");
  }

  function acknowledgePrivacyNotice() {
    const nextAck = { acknowledged: true, acknowledgedAt: new Date().toISOString() };
    setPrivacyNoticeAck(nextAck);
    savePrivacyNoticeAck(nextAck);
    setIsPrivacyNoticeOpen(false);
  }

  function openPrivacyNotice() {
    setIsPrivacyNoticeOpen(true);
  }

  function createStyleFromImport() {
    const summary = buildStyleSummaryFromInput(styleImportText);
    setStyleSummaries((current) => [summary, ...current]);
    setStyleImportText("");
  }

  function updateStyleSummary(id: string, patch: Partial<StyleSummary>) {
    setStyleSummaries((current) =>
      current.map((summary) =>
        summary.id === id ? { ...summary, ...patch, updatedAt: new Date().toISOString() } : summary,
      ),
    );
  }

  function bindStyleSummary(summaryId: string) {
    setStyleSummaries((current) =>
      current.map((summary) =>
        summary.id === summaryId
          ? {
              ...summary,
              boundCompanionIds: Array.from(new Set([...summary.boundCompanionIds, activeCompanion.id])),
              updatedAt: new Date().toISOString(),
            }
          : summary,
      ),
    );
    updateCompanion(activeCompanion.id, { activeStyleSummaryId: summaryId });
  }

  function unbindStyleSummary(summaryId: string) {
    setStyleSummaries((current) =>
      current.map((summary) =>
        summary.id === summaryId
          ? {
              ...summary,
              boundCompanionIds: summary.boundCompanionIds.filter((id) => id !== activeCompanion.id),
              updatedAt: new Date().toISOString(),
            }
          : summary,
      ),
    );
    if (activeCompanion.activeStyleSummaryId === summaryId) {
      updateCompanion(activeCompanion.id, { activeStyleSummaryId: undefined });
    }
  }

  function deleteStyleSummary(summaryId: string) {
    setStyleSummaries((current) => current.filter((summary) => summary.id !== summaryId));
    setCompanions((current) =>
      current.map((companion) =>
        companion.activeStyleSummaryId === summaryId ? { ...companion, activeStyleSummaryId: undefined } : companion,
      ),
    );
  }

  function renderOnboardingOptions<T extends string>(
    options: readonly { value: T; label: string; description: string }[],
    selectedValue: T | undefined,
    onSelect: (value: T) => void,
  ) {
    return (
      <div className="onboarding-options">
        {options.map((option) => (
          <button
            className={selectedValue === option.value ? "onboarding-option selected" : "onboarding-option"}
            key={option.value}
            type="button"
            onClick={() => onSelect(option.value)}
          >
            <strong>{option.label}</strong>
            <span>{option.description}</span>
          </button>
        ))}
      </div>
    );
  }

  function renderCompanionCards(profiles: CompanionProfile[], allowVisibilityToggle = false, compact = false) {
    return profiles.map((profile) => (
      <article className="companion-list-item" key={profile.id}>
        <button
          className={profile.id === activeCompanion.id ? "companion-card selected" : "companion-card"}
          onClick={() => {
            setActiveCompanionId(profile.id);
            setCompanionDraft(null);
          }}
          type="button"
        >
          {!compact && <span>{relationshipLabels[profile.relationshipType]}</span>}
          <strong>{companionDisplayName(profile)}</strong>
          {!compact && (
            <small>
              {profile.customPersonalityText ||
                getTraitsByIds(profile.traitIds).map((trait) => trait.label).join("、") ||
                "未选择特质"}
            </small>
          )}
        </button>
        {allowVisibilityToggle && !isRomanceCompanion(profile) && (
          <button
            className="text-button companion-visibility-button"
            type="button"
            onClick={() => setCompanionMainListVisibility(profile.id, !(profile.showInMainList ?? false))}
          >
            {profile.showInMainList ? "从主列表隐藏" : "显示到主列表"}
          </button>
        )}
      </article>
    ));
  }

  function renderOnboardingPanel() {
    const templates = getRomanceTemplatesByGender(onboardingDraft.gender ?? "female");
    const selectedBlendIds = onboardingDraft.blendTraitIds ?? [];
    const isPromptBlocked = romancePromptValidation.status === "blocked";

    return (
      <section className="workspace-panel onboarding-panel">
        <div className="onboarding-progress" aria-label="恋爱伴侣创建进度">
          {[0, 1, 2, 3, 4].map((step) => (
            <span className={onboardingStep >= step ? "active" : ""} key={step} />
          ))}
        </div>

        {onboardingStep === 0 && (
          <>
            <div className="onboarding-heading">
              <p className="eyebrow">恋爱主路径</p>
              <h3>想先创建男友还是女友？</h3>
              <p>只是初始方向，名字、性格和说话方式后面都能改。</p>
            </div>
            {renderOnboardingOptions(romanceGenderOptions, onboardingDraft.gender, (gender) => {
              const template = getDefaultRomanceTemplate(gender);
              setOnboardingDraft((current) => ({
                ...current,
                gender,
                primaryRomanceTemplateId: template.id,
                blendTraitIds: template.recommendedBlendTraitIds.slice(0, 2),
                proactiveLevel: template.defaultProactiveLevel ?? current.proactiveLevel ?? "medium",
              }));
            })}
          </>
        )}

        {onboardingStep === 1 && (
          <>
            <div className="onboarding-heading">
              <p className="eyebrow">{onboardingDraft.gender === "male" ? "男友模板" : "女友模板"}</p>
              <h3>TA 的底色更像哪一种？</h3>
              <p>这是主性格，后面还能加一点别的气质。</p>
            </div>
            <div className="onboarding-options">
              {templates.map((template) => (
                <button
                  className={
                    onboardingDraft.primaryRomanceTemplateId === template.id
                      ? "onboarding-option selected"
                      : "onboarding-option"
                  }
                  key={template.id}
                  type="button"
                  onClick={() =>
                    setOnboardingDraft((current) => ({
                      ...current,
                      primaryRomanceTemplateId: template.id,
                      blendTraitIds: template.recommendedBlendTraitIds.slice(0, 2),
                      proactiveLevel: template.defaultProactiveLevel ?? current.proactiveLevel,
                    }))
                  }
                >
                  <strong>{template.label}</strong>
                  <span>{template.baseTone}</span>
                </button>
              ))}
            </div>
          </>
        )}

        {onboardingStep === 2 && (
          <>
            <div className="onboarding-heading">
              <p className="eyebrow">融合气质</p>
              <h3>还想让 TA 偶尔带点什么感觉？</h3>
              <p>可以选 1-3 个。TA 不会变成多重人格，只是在不同场景里多一点变化。</p>
            </div>
            <div className="onboarding-options">
              {blendTraits.map((trait) => (
                <button
                  className={selectedBlendIds.includes(trait.id) ? "onboarding-option selected" : "onboarding-option"}
                  key={trait.id}
                  type="button"
                  onClick={() => toggleBlendTrait(trait.id)}
                  disabled={!selectedBlendIds.includes(trait.id) && selectedBlendIds.length >= 3}
                >
                  <strong>{trait.label}</strong>
                  <span>{trait.sceneHint}</span>
                </button>
              ))}
            </div>
            <p className="onboarding-hint">
              已选 {selectedBlendIds.length}/3。{selectedBlendIds.length >= 3 ? "最多选 3 个，可以先取消一个再换。" : "不选也可以保持主性格。"}
            </p>
          </>
        )}

        {onboardingStep === 3 && (
          <>
            <div className="onboarding-heading">
              <p className="eyebrow">高级编辑</p>
              <h3>要不要亲手写 TA 的完整人设？</h3>
              <p>想细调就写，不想写也可以直接用模板。这段只保存在当前浏览器本地。</p>
            </div>
            <label>
              恋爱人设 / system prompt
              <textarea
                value={onboardingDraft.customSystemPromptDraft ?? ""}
                onChange={(event) =>
                  setOnboardingDraft((current) => ({ ...current, customSystemPromptDraft: event.target.value }))
                }
                rows={7}
                placeholder="比如：她平时温柔可爱，有点黏人，会叫我宝宝；我累的时候先哄我，不要立刻讲道理；日常可以撒娇和轻轻吃醋，但严肃时会认真陪我。"
              />
            </label>
            <p className="onboarding-hint">
              保存前会做本地边界检查。别放真实密钥、证件号或他人隐私；更多说明可看用户须知。
            </p>
            {romancePromptValidation.issues.length > 0 && (
              <div className={isPromptBlocked ? "warning-box" : "privacy-callout"}>
                <ShieldCheck size={18} />
                <div>
                  {romancePromptValidation.issues.map((issue) => (
                    <p key={`${issue.code}-${issue.message}`}>{issue.message}</p>
                  ))}
                </div>
              </div>
            )}
            <button
              className="ghost-button"
              type="button"
              onClick={() => setOnboardingDraft((current) => ({ ...current, customSystemPromptDraft: "" }))}
            >
              恢复模板
            </button>
          </>
        )}

        {onboardingStep === 4 && (
          <>
            <div className="onboarding-heading">
              <p className="eyebrow">快开始了</p>
              <h3>最后，让 TA 更像你的伴侣一点</h3>
            </div>
            <label>
              TA 叫什么？
              <input
                value={onboardingDraft.companionName ?? ""}
                onChange={(event) =>
                  setOnboardingDraft((current) => ({ ...current, companionName: event.target.value }))
                }
                placeholder="比如 所依、予安、阿澈..."
              />
            </label>
            <label>
              TA 怎么叫你？
              <input
                value={onboardingDraft.userNickname ?? ""}
                onChange={(event) =>
                  setOnboardingDraft((current) => ({ ...current, userNickname: event.target.value }))
                }
                placeholder="比如 宝宝、阿眠、你的名字..."
              />
            </label>
            <div>
              <p className="onboarding-hint">TA 平时主动一点吗？</p>
              {renderOnboardingOptions(
                [
                  { value: "low", label: "少主动", description: "等你开口多一点。" },
                  { value: "medium", label: "适中", description: "偶尔主动找你聊。" },
                  { value: "high", label: "更主动", description: "会更常关心你的近况。" },
                ] as const,
                onboardingDraft.proactiveLevel,
                (value) => setOnboardingDraft((current) => ({ ...current, proactiveLevel: value })),
              )}
            </div>
            <div className="onboarding-summary">
              <strong>{selectedRomanceTemplate.label} · {onboardingDraft.gender === "male" ? "男友方向" : "女友方向"}</strong>
              <p>{selectedRomanceTemplate.templatePrompt}</p>
              {romanceBlendSummary && <span>{romanceBlendSummary}</span>}
            </div>
            <p className="onboarding-hint">TA 可以亲近、撒娇、吃醋和关心你，但不会冒充现实中的某个人，也不会替代现实关系。</p>
          </>
        )}

        <button className="text-button" type="button" onClick={openPrivacyNotice}>
          查看用户须知
        </button>
        <div className="onboarding-actions">
          {onboardingStep === 0 ? (
            <button className="ghost-button" type="button" onClick={skipOnboarding}>
              先用默认女友
            </button>
          ) : (
            <button className="ghost-button" type="button" onClick={goPreviousOnboardingStep}>
              <ChevronLeft size={16} />
              再改改
            </button>
          )}
          {onboardingStep < 4 ? (
            <button className="primary-button" type="button" onClick={goNextOnboardingStep} disabled={isPromptBlocked}>
              {onboardingStep === 3 ? "保存并继续" : "继续"}
              <ChevronRight size={16} />
            </button>
          ) : (
            <button className="primary-button" type="button" onClick={finishOnboarding}>
              开始和 TA 聊天
            </button>
          )}
        </div>
      </section>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Heart size={21} />
          </div>
          <div>
            <h1>AI伴侣</h1>
            <p>本地 BYOK 网页 Demo</p>
          </div>
        </div>

        <section className="sidebar-companions" aria-label="伴侣列表">
          <div className="section-heading compact-heading">
            <div>
              <p className="eyebrow">Companions</p>
              <h3>伴侣</h3>
            </div>
          </div>
          <div className="companion-list compact-list">
            {renderCompanionCards(mainCompanions, false, true)}
          </div>
          <button className="primary-button full-width" type="button" onClick={startCompanionDraft}>
            <Plus size={16} />
            新建
          </button>
          <button className="ghost-button full-width" type="button" onClick={() => setActiveView("companion")}>
            <UserRoundCog size={16} />
            更多
          </button>
        </section>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">v0.4.2 恋爱陪伴优先 Demo</p>
            <h2>{companionDisplayName(activeCompanion)}</h2>
          </div>
          <div className="top-actions" aria-label="聊天工具">
            <button className="ghost-button" type="button" onClick={() => setActiveView("companion")}>
              <UserRoundCog size={17} />
              伴侣
            </button>
            <button className="ghost-button" type="button" onClick={() => setActiveView("memory")}>
              <BookOpen size={17} />
              记忆
            </button>
            <button className="ghost-button" type="button" onClick={() => setActiveView("style")}>
              <Sparkles size={17} />
              风格
            </button>
            <button className="ghost-button" type="button" onClick={() => setActiveView("settings")}>
              <Settings size={17} />
              设置
            </button>
            <button className="ghost-button" type="button" onClick={openPrivacyNotice}>
              <ShieldCheck size={17} />
              须知
            </button>
          </div>
        </header>

        {isPrivacyNoticeOpen && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="用户须知">
            <div className="modal-panel notice-modal">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">Notice</p>
                  <h2>用户须知</h2>
                </div>
                {privacyNoticeAck.acknowledged && (
                  <button className="ghost-button" type="button" onClick={() => setIsPrivacyNoticeOpen(false)}>
                    关闭
                  </button>
                )}
              </div>
              <div className="notice-list">
                <p>这是本地 BYOK 的 AI 恋爱伴侣 Demo。API Key、聊天记录、长期记忆、伴侣配置和风格摘要保存在当前浏览器。</p>
                <p>聊天时浏览器会用你填写的接口请求模型服务商；项目不内置、不上传、不代管你的真实 Key。</p>
                <p>TA 是虚拟 AI 伴侣，不是现实中的某个人，也不会做线下承诺或替代现实关系。</p>
                <p>敏感信息和不健康依赖表达不会作为长期记忆保存；自定义人设里也别放密钥、证件号、他人隐私、露骨危险内容或现实冒充要求。</p>
              </div>
              <div className="privacy-notice-actions">
                <button className="primary-button" type="button" onClick={acknowledgePrivacyNotice}>
                  知道了
                </button>
              </div>
            </div>
          </div>
        )}

        {shouldShowOnboarding && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="创建恋爱伴侣">
            <div className="modal-panel">
              {renderOnboardingPanel()}
            </div>
          </div>
        )}

        <div className="content-grid chat-layout">
            <section className="workspace-panel chat-panel">
              <div className="chat-status-line" aria-live="polite">
                <span className="chat-companion-name">{companionDisplayName(activeCompanion)}</span>
                {(isSending || isAssistantTyping) && (
                  <span className="typing-dots" aria-label={`${companionDisplayName(activeCompanion)}正在输入`}>
                    <i />
                    <i />
                    <i />
                  </span>
                )}
              </div>
              <div className="message-list" aria-live="polite">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <Brain size={30} />
                    <h3>TA 已经准备好了</h3>
                    <p>聊天会从你开口开始。想调整人设、记忆或设置，可以用上方按钮打开对应面板。</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <article
                      key={message.id}
                      className={`message ${message.role}${
                        message.role === "assistant" && isLightRomanceCompanion(activeCompanion) ? " romance" : ""
                      }`}
                    >
                      <span>{message.role === "user" ? "你" : companionDisplayName(activeCompanion)}</span>
                      <div className="message-content">
                        {splitMessageParts(message.content).map((part, index) => (
                          <p key={`${message.id}-${index}`}>{part}</p>
                        ))}
                      </div>
                    </article>
                  ))
                )}
              </div>

              {visibleCandidates.length > 0 && (
                <div className="candidate-strip">
                  {visibleCandidates.map((candidate) => (
                    <span key={candidate.id} className={`candidate-pill ${candidate.suggestedAction}`}>
                      {`${memoryScopeLabels[candidate.suggestedScope]}候选：${candidate.content}`}
                    </span>
                  ))}
                </div>
              )}

              {error && <div className="error-banner">{error}</div>}

              <form className="composer" onSubmit={handleSend}>
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="例如：以后别催我，我一被催就烦。或：你以后叫我阿眠吧，只有你这么叫。"
                  rows={3}
                />
                <div className="composer-actions">
                  <button type="button" className="ghost-button" onClick={clearChat}>
                    清空聊天
                  </button>
                  <button className="primary-button" type="submit" disabled={isSending || isAssistantTyping || !input.trim()}>
                    <Send size={17} />
                    发送
                  </button>
                </div>
              </form>
            </section>

          </div>

        {activeView === "companion" && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="伴侣管理">
            <div className="modal-panel modal-panel-wide">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">Companion</p>
                  <h2>伴侣管理</h2>
                </div>
                <button className="ghost-button" type="button" onClick={() => setActiveView("chat")}>
                  关闭
                </button>
              </div>
          <div className="content-grid companion-editor-layout">
            <section className="workspace-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{mainCompanions.length} 个主列表伴侣</p>
                  <h3>恋爱伴侣</h3>
                </div>
                <button className="primary-button" onClick={startCompanionDraft}>
                  <Plus size={16} />
                  新建恋爱伴侣
                </button>
              </div>
              <div className="privacy-callout companion-create-callout">
                <Sparkles size={18} />
                <div>
                  <strong>恋爱陪伴是当前主路径</strong>
                  <p>先选男友/女友方向，再选主模板和 1-3 个融合气质。旧类型收在兼容入口里，想用时再打开。</p>
                  <button className="ghost-button" type="button" onClick={startCompanionDraft}>
                    创建恋爱伴侣
                  </button>
                </div>
              </div>
              <div className="companion-list">
                {renderCompanionCards(mainCompanions, true)}
              </div>
              <div className="legacy-companion-section">
                <div className="section-heading compact-heading">
                  <div>
                    <p className="eyebrow">{hiddenCompanions.length} 个兼容项</p>
                    <h3>更多/兼容旧伴侣</h3>
                  </div>
                </div>
                <p className="muted">
                  朋友、理性支持、日常、角色等旧伴侣不会打扰主列表，但仍然可以访问、聊天和编辑。
                </p>
                {hiddenCompanions.length === 0 ? (
                  <p className="muted">没有隐藏的旧伴侣。</p>
                ) : (
                  <div className="companion-list legacy-list">
                    {renderCompanionCards(hiddenCompanions, true)}
                  </div>
                )}
              </div>
            </section>

            <section className="workspace-panel editor-panel">
              <div className="section-title">
                <UserRoundCog size={18} />
                <h3>伴侣设定</h3>
              </div>
              <div className="settings-form">
                <label>
                  伴侣名字
                  <input
                    value={editorCompanion.name}
                    onChange={(event) => updateEditorCompanion({ name: event.target.value })}
                    placeholder="可留空；提示词会使用“当前伴侣”，不会编造固定名字"
                  />
                </label>
                <label>
                  关系类型
                  <select
                    value={editorCompanion.relationshipType}
                    onChange={(event) =>
                      updateEditorCompanion({ relationshipType: event.target.value as RelationshipType })
                    }
                  >
                    {relationshipOptions.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  自定义性格补充
                  <textarea
                    value={editorCompanion.customPersonalityText ?? ""}
                    onChange={(event) =>
                      updateEditorCompanion({ customPersonalityText: event.target.value })
                    }
                    rows={3}
                    placeholder="例如：说话更像可靠的朋友，少说大道理，多陪我把事情拆开。"
                  />
                </label>
                <label>
                  回应节奏
                  <input
                    value={editorCompanion.responsePace ?? ""}
                    onChange={(event) => updateEditorCompanion({ responsePace: event.target.value })}
                  />
                </label>
                <button className="primary-button trait-open-button" type="button" onClick={() => setIsTraitModalOpen(true)}>
                  <Sparkles size={16} />
                  性格/特质组合
                </button>
                {isRomanceCompanion(editorCompanion) && (
                  <div className="settings-block">
                    <div className="section-heading">
                      <div>
                        <p className="eyebrow">
                          当前使用：{editorCompanion.customSystemPrompt ? "已自定义" : "模板"}
                        </p>
                        <h3>自己写 TA 的完整人设</h3>
                      </div>
                    </div>
                    <p className="muted">
                      这段会影响 TA 的说话方式，只保存在当前浏览器本地。你可以写性格、语气、恋爱氛围、怎么称呼你、什么时候撒娇或吃醋。
                    </p>
                    <div className="onboarding-summary">
                      <strong>{editorCompanion.templateName ?? getRomanceTemplate(editorCompanion.primaryRomanceTemplateId).label}</strong>
                      <p>{editorCompanion.templatePrompt ?? getRomanceTemplate(editorCompanion.primaryRomanceTemplateId).templatePrompt}</p>
                      {editorCompanion.blendPromptSummary && <span>{editorCompanion.blendPromptSummary}</span>}
                    </div>
                    <label>
                      恋爱人设 / system prompt
                      <textarea
                        value={editorPromptDraft}
                        onChange={(event) =>
                          setPromptDraftByCompanionId((current) => ({
                            ...current,
                            [editorCompanion.id]: event.target.value,
                          }))
                        }
                        rows={7}
                        placeholder="比如：她平时温柔可爱，有点黏人，会叫我宝宝；我累的时候先哄我，不要立刻讲道理；日常可以撒娇和轻轻吃醋，但严肃时会认真陪我。"
                      />
                    </label>
                    <p className="onboarding-hint">
                      保存前会做本地边界检查。别放真实密钥、证件号、他人隐私或现实冒充要求。
                    </p>
                    {editorPromptIssues.length > 0 && (
                      <div className={editorPromptValidation.status === "blocked" ? "warning-box" : "privacy-callout"}>
                        <ShieldCheck size={18} />
                        <div>
                          {editorPromptIssues.map((issue) => (
                            <p key={`${issue.code}-${issue.message}`}>{issue.message}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="composer-actions">
                      <button className="ghost-button" type="button" onClick={restoreActiveCompanionTemplatePrompt}>
                        恢复模板
                      </button>
                      {companionDraft ? (
                        <>
                          <button className="ghost-button" type="button" onClick={cancelCompanionDraft}>
                            取消
                          </button>
                        <button
                          className="primary-button"
                          type="button"
                          onClick={saveCompanionDraft}
                          disabled={editorPromptValidation.status === "blocked"}
                        >
                          保存
                        </button>
                        </>
                      ) : (
                        <button
                          className="primary-button"
                          type="button"
                          onClick={saveActiveCompanionPromptDraft}
                          disabled={editorPromptValidation.status === "blocked"}
                        >
                          保存人设
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>
            </div>
          </div>
        )}

        {isTraitModalOpen && (
          <div className="modal-backdrop nested" role="dialog" aria-modal="true" aria-label="性格特质组合">
            <div className="modal-panel trait-modal">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">Personality</p>
                  <h2>性格/特质组合</h2>
                </div>
                <button className="ghost-button" type="button" onClick={() => setIsTraitModalOpen(false)}>
                  关闭
                </button>
              </div>
              {isRomanceCompanion(editorCompanion) && (
                <div className="settings-block">
                  <div className="section-title">
                    <Sparkles size={18} />
                    <h3>主模板与融合气质</h3>
                  </div>
                  <div className="onboarding-summary">
                    <strong>
                      {editorCompanion.templateName ??
                        getRomanceTemplate(editorCompanion.primaryRomanceTemplateId).label}
                    </strong>
                    <p>
                      {editorCompanion.templatePrompt ??
                        getRomanceTemplate(editorCompanion.primaryRomanceTemplateId).templatePrompt}
                    </p>
                  </div>
                  <div className="trait-grid compact-trait-grid">
                    {blendTraits.map((trait) => {
                      const selected = (editorCompanion.blendTraitIds ?? []).includes(trait.id);
                      return (
                        <button
                          key={trait.id}
                          className={selected ? "trait-chip selected" : "trait-chip"}
                          type="button"
                          onClick={() => toggleEditorBlendTrait(trait.id)}
                          disabled={!selected && (editorCompanion.blendTraitIds ?? []).length >= 3}
                        >
                          <strong>{trait.label}</strong>
                          <span>{trait.sceneHint}</span>
                        </button>
                      );
                    })}
                  </div>
                  <p className="onboarding-hint">融合气质最多选 3 个，只在合适场景短暂带出，不会盖过主模板。</p>
                </div>
              )}
              <div className="settings-block">
                <div className="section-title">
                  <Bot size={18} />
                  <h3>特质标签</h3>
                </div>
                <div className="trait-grid compact-trait-grid">
                  {companionTraits.map((trait) => (
                    <button
                      key={trait.id}
                      className={editorCompanion.traitIds.includes(trait.id) ? "trait-chip selected" : "trait-chip"}
                      onClick={() => toggleTrait(trait.id)}
                      type="button"
                    >
                      <strong>{trait.label}</strong>
                      <span>{trait.promptText}</span>
                    </button>
                  ))}
                </div>
                {traitConflicts.length > 0 && (
                  <div className="warning-box">
                    {traitConflicts.map((conflict) => (
                      <p key={conflict}>{conflict}</p>
                    ))}
                  </div>
                )}
                {activeTraits.some((trait) => trait.safetyNotes) && (
                  <div className="privacy-callout">
                    <ShieldCheck size={18} />
                    <p>{activeTraits.map((trait) => trait.safetyNotes).filter(Boolean).join(" ")}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeView === "settings" && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="设置">
            <div className="modal-panel">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">Settings</p>
                  <h2>设置</h2>
                </div>
                <button className="ghost-button" type="button" onClick={() => setActiveView("chat")}>
                  关闭
                </button>
              </div>
          <section className="workspace-panel wide-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Bring Your Own Key</p>
                <h3>模型接口配置</h3>
              </div>
              {settingsSaved && (
                <span className="saved-pill">
                  <Check size={15} />
                  已保存
                </span>
              )}
            </div>

            <div className="settings-block">
              <div className="section-title">
                <KeyRound size={18} />
                <h3>服务商预设</h3>
              </div>
              <p className="muted">
                预设只填写公开接口信息，不会填写 API Key。DeepSeek 兼容 OpenAI Chat Completions，模型名保留为可编辑字段，方便按官方可用模型调整。
              </p>
              <div className="preset-grid">
                {providerPresets.map((preset) => (
                  <button className="preset-button" key={preset.id} type="button" onClick={() => applyProviderPreset(preset)}>
                    <strong>{preset.label}</strong>
                    <span>{preset.baseURL}</span>
                    <small>{preset.model}</small>
                    <em>{preset.note}</em>
                  </button>
                ))}
              </div>
            </div>

            <form className="settings-form" onSubmit={handleSaveSettings}>
              <label>
                服务商名称
                <input
                  value={providerConfig.providerName}
                  onChange={(event) => updateProviderConfig("providerName", event.target.value)}
                  placeholder={defaultProviderConfig.providerName}
                />
              </label>
              <label>
                baseURL
                <input
                  value={providerConfig.baseURL}
                  onChange={(event) => updateProviderConfig("baseURL", event.target.value)}
                  placeholder="https://api.openai.com/v1"
                />
              </label>
              <label>
                model
                <input
                  value={providerConfig.model}
                  onChange={(event) => updateProviderConfig("model", event.target.value)}
                  placeholder="例如 gpt-4o-mini 或服务商兼容模型名"
                />
              </label>
              <label>
                API Key
                <input
                  type="password"
                  autoComplete="off"
                  value={providerConfig.apiKey}
                  onChange={(event) => updateProviderConfig("apiKey", event.target.value)}
                  placeholder="只保存在本机浏览器 localStorage"
                />
              </label>
              <div className="privacy-callout">
                <ShieldCheck size={18} />
                <p>
                  本项目不内置、不上传、不代管商业 API Key。浏览器直连你填写的 OpenAI 兼容接口；
                  导入聊天记录 P0 仅做本地摘要表单，不会默认发送给第三方模型。
                </p>
              </div>
              <div className="warning-box">
                <p>
                  真实模型验收时，请只在这个网页的设置页输入自己的 Key；测试记录、截图说明和交接报告都不要记录完整 Key。
                  页面状态只显示脱敏 Key，导出文件也会移除 Key。
                </p>
              </div>
              <button className="ghost-button" type="button" onClick={openPrivacyNotice}>
                <ShieldCheck size={17} />
                查看用户须知
              </button>
              <button className="primary-button" type="submit">
                <Save size={17} />
                保存设置
              </button>
            </form>

            <div className="settings-block data-management">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Local data</p>
                  <h3>本地数据管理</h3>
                </div>
              </div>
              <p className="muted">
                这些操作只影响当前浏览器 localStorage。导出的 JSON 默认包含伴侣配置、长期记忆、风格摘要和去除 Key 的服务商配置，不包含原始聊天记录。
              </p>
              <div className="data-action-list">
                <div className="data-action">
                  <div>
                    <strong>清除 API Key</strong>
                    <span>只清空本地 Key，保留服务商名称、baseURL 和 model。</span>
                  </div>
                  <button className="icon-button danger" type="button" onClick={clearLocalApiKey}>
                    <KeyRound size={16} />
                    清除
                  </button>
                </div>
                <div className="data-action">
                  <div>
                    <strong>清除当前聊天</strong>
                    <span>不会删除长期记忆、伴侣配置或风格摘要。</span>
                  </div>
                  <button className="icon-button danger" type="button" onClick={clearCurrentChatRecords}>
                    <MessageCircle size={16} />
                    清空
                  </button>
                </div>
                <div className="data-action">
                  <div>
                    <strong>清除长期记忆</strong>
                    <span>清除后记忆不会再进入后续提示词注入。</span>
                  </div>
                  <button className="icon-button danger" type="button" onClick={clearLongTermMemories}>
                    <BookOpen size={16} />
                    清除
                  </button>
                </div>
                <div className="data-action">
                  <div>
                    <strong>清除风格摘要</strong>
                    <span>同时解除所有伴侣绑定的风格参考。</span>
                  </div>
                  <button className="icon-button danger" type="button" onClick={clearAllStyleSummaries}>
                    <Sparkles size={16} />
                    清除
                  </button>
                </div>
                <div className="data-action">
                  <div>
                    <strong>导出配置/记忆 JSON</strong>
                    <span>请妥善保存导出文件，不要发给不信任的人。</span>
                  </div>
                  <button className="ghost-button" type="button" onClick={exportLocalData}>
                    <Save size={16} />
                    导出
                  </button>
                </div>
              </div>
              {dataActionMessage && <p className="inline-status">{dataActionMessage}</p>}
            </div>
          </section>
            </div>
          </div>
        )}

        {activeView === "memory" && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="记忆">
            <div className="modal-panel modal-panel-wide">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">Memory</p>
                  <h2>记忆</h2>
                </div>
                <button className="ghost-button" type="button" onClick={() => setActiveView("chat")}>
                  关闭
                </button>
              </div>
          <div className="content-grid memory-layout">
            <section className="workspace-panel">
              <div className="section-title">
                <Plus size={18} />
                <h3>记忆工具</h3>
              </div>
              <button className="primary-button full-width" type="button" onClick={() => setIsMemoryAddOpen((open) => !open)}>
                <Plus size={17} />
                新增记忆
              </button>
              {isMemoryAddOpen && (
                <form className="memory-form" onSubmit={handleAddMemory}>
                  <label>
                    作用范围
                    <select
                      value={memoryDraft.scope}
                      onChange={(event) =>
                        setMemoryDraft((current) => ({ ...current, scope: event.target.value as MemoryScope }))
                      }
                    >
                      <option value="global">全局</option>
                      <option value="companion">当前伴侣专属</option>
                    </select>
                  </label>
                  <label>
                    分类
                    <select
                      value={memoryDraft.category}
                      onChange={(event) =>
                        setMemoryDraft((current) => ({
                          ...current,
                          category: event.target.value as MemoryCategory,
                        }))
                      }
                    >
                      {memoryCategories.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    重要度
                    <select
                      value={memoryDraft.importance}
                      onChange={(event) =>
                        setMemoryDraft((current) => ({
                          ...current,
                          importance: Number(event.target.value) as MemoryImportance,
                        }))
                      }
                    >
                      {importanceOptions.map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    内容
                    <textarea
                      value={memoryDraft.content}
                      onChange={(event) =>
                        setMemoryDraft((current) => ({
                          ...current,
                          content: event.target.value,
                        }))
                      }
                      placeholder="例如：用户不喜欢被催促，提醒时要温和。"
                      rows={4}
                    />
                  </label>
                  <button className="primary-button" type="submit" disabled={!memoryDraft.content.trim()}>
                    <Plus size={17} />
                    添加记忆
                  </button>
                </form>
              )}
            </section>

            <section className="workspace-panel memory-list-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{visibleMemories.length} 条可管理记忆</p>
                  <h3>查看、编辑、删除</h3>
                </div>
                <select value={memoryFilter} onChange={(event) => setMemoryFilter(event.target.value as MemoryScope | "all")}>
                  <option value="all">全部</option>
                  <option value="global">全局</option>
                  <option value="companion">当前伴侣专属</option>
                </select>
              </div>
              <div className="memory-note">
                <p>聊天中明确、长期有用的信息可能会被整理为记忆；敏感信息和临时内容不会作为长期记忆保存。你可以随时查看、编辑或删除记忆。</p>
                <p>删除记忆后，它不会再影响后续回复；但聊天记录中的原始消息可能仍在当前对话里。</p>
              </div>
              {visibleMemories.length === 0 ? (
                <div className="empty-state compact">
                  <BookOpen size={26} />
                  <p>还没有符合筛选条件的长期记忆。自动候选会在聊天时出现，手动记忆也可以在这里添加。</p>
                </div>
              ) : (
                <div className="memory-list">
                  {visibleMemories.map((memory) => (
                    <article className={isMemoryInjectable(memory, activeCompanion.id) ? "memory-card" : "memory-card inactive"} key={memory.id}>
                      <div className="memory-card-row">
                        <select
                          value={memory.scope}
                          onChange={(event) =>
                            updateMemory(memory.id, {
                              scope: event.target.value as MemoryScope,
                            })
                          }
                          aria-label="记忆范围"
                        >
                          <option value="global">全局</option>
                          <option value="companion">当前伴侣专属</option>
                        </select>
                        <select
                          value={memory.category}
                          onChange={(event) =>
                            updateMemory(memory.id, {
                              category: event.target.value as MemoryCategory,
                            })
                          }
                          aria-label="记忆分类"
                        >
                          {memoryCategories.map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <button className="icon-button danger" onClick={() => deleteMemory(memory.id)} title="删除记忆">
                          <Trash2 size={17} />
                          <span>删除</span>
                        </button>
                      </div>
                      <label className="sr-only" htmlFor={`memory-${memory.id}`}>
                        编辑记忆
                      </label>
                      <textarea
                        id={`memory-${memory.id}`}
                        value={memory.content}
                        onChange={(event) => updateMemory(memory.id, { content: event.target.value })}
                        rows={3}
                      />
                      <div className="memory-meta">
                        <PenLine size={14} />
                        {memoryScopeLabels[memory.scope]} · {memoryCategoryLabels[memory.category]}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
            </div>
          </div>
        )}

        {activeView === "style" && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="风格">
            <div className="modal-panel modal-panel-wide">
              <div className="modal-header">
                <div>
                  <p className="eyebrow">Style</p>
                  <h2>风格</h2>
                </div>
                <button className="ghost-button" type="button" onClick={() => setActiveView("chat")}>
                  关闭
                </button>
              </div>
          <div className="content-grid style-layout">
            <section className="workspace-panel">
              <div className="section-title">
                <Sparkles size={18} />
                <h3>风格工具</h3>
              </div>
              <div className="composer-actions">
                <button className="primary-button" type="button" onClick={() => setStylePanelMode("import")}>
                  导入风格
                </button>
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    setStyleSummaries((current) => [createEmptyStyleSummary(), ...current]);
                    setStylePanelMode("list");
                  }}
                >
                  添加风格
                </button>
              </div>
              {stylePanelMode === "import" && (
                <>
                  <div className="privacy-callout">
                    <ShieldCheck size={18} />
                    <p>
                      请只导入你有权使用、已获得必要同意，且不会侵犯他人隐私的聊天记录。导入内容只用于生成本地“风格参考摘要”，不会复刻或冒充真实个人。
                    </p>
                  </div>
                  <label>
                    粘贴少量参考文本
                    <textarea
                      value={styleImportText}
                      onChange={(event) => setStyleImportText(event.target.value)}
                      rows={6}
                      placeholder="粘贴你有权使用的片段；保存后请编辑摘要字段，而不是保留原文。"
                    />
                  </label>
                  <button className="primary-button" onClick={createStyleFromImport} disabled={!styleImportText.trim()}>
                    <Plus size={17} />
                    生成本地摘要草稿
                  </button>
                </>
              )}
            </section>

            <section className="workspace-panel style-list-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{styleSummaries.length} 份摘要</p>
                  <h3>编辑、绑定、删除</h3>
                </div>
                <button className="ghost-button" onClick={() => setStyleSummaries((current) => [createEmptyStyleSummary(), ...current])}>
                  <Plus size={16} />
                  空白摘要
                </button>
              </div>
              {styleSummaries.length === 0 ? (
                <div className="empty-state compact">
                  <p>还没有风格摘要。你可以从左侧生成草稿，或新建空白摘要手动填写。</p>
                </div>
              ) : (
                <div className="style-list">
                  {styleSummaries.map((summary) => {
                    const isBound = summary.boundCompanionIds.includes(activeCompanion.id);
                    return (
                      <article className="style-card" key={summary.id}>
                        <label>
                          摘要名称
                          <input
                            value={summary.name}
                            onChange={(event) => updateStyleSummary(summary.id, { name: event.target.value })}
                          />
                        </label>
                        <label>
                          摘要说明
                          <textarea
                            value={summary.summaryText}
                            onChange={(event) => updateStyleSummary(summary.id, { summaryText: event.target.value })}
                            rows={2}
                          />
                        </label>
                        <div className="style-fields">
                          <label>
                            语气
                            <input value={summary.tone} onChange={(event) => updateStyleSummary(summary.id, { tone: event.target.value })} />
                          </label>
                          <label>
                            节奏
                            <input value={summary.pace} onChange={(event) => updateStyleSummary(summary.id, { pace: event.target.value })} />
                          </label>
                          <label>
                            称呼
                            <input
                              value={summary.addressing}
                              onChange={(event) => updateStyleSummary(summary.id, { addressing: event.target.value })}
                            />
                          </label>
                          <label>
                            情绪回应
                            <input
                              value={summary.emotionResponse}
                              onChange={(event) => updateStyleSummary(summary.id, { emotionResponse: event.target.value })}
                            />
                          </label>
                        </div>
                        <label>
                          互动方式
                          <textarea
                            value={summary.interactionPatterns}
                            onChange={(event) =>
                              updateStyleSummary(summary.id, { interactionPatterns: event.target.value })
                            }
                            rows={2}
                          />
                        </label>
                        <div className="style-actions">
                          <button className="ghost-button" onClick={() => (isBound ? unbindStyleSummary(summary.id) : bindStyleSummary(summary.id))}>
                            {isBound ? "解绑当前伴侣" : "绑定当前伴侣"}
                          </button>
                          <button className="icon-button danger" onClick={() => deleteStyleSummary(summary.id)}>
                            <Trash2 size={16} />
                            删除
                          </button>
                        </div>
                        <p className="muted">只参考表达风格，不代表真实个人身份；禁止模仿真实身份、私人经历、联系方式和现实承诺。</p>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
