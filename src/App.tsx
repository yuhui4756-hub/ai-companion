import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Bot,
  Brain,
  Check,
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
  defaultCompanions,
  getCompanionProfile,
  getTraitConflictLabels,
  getTraitsByIds,
  relationshipLabels,
} from "./companion/profiles";
import { sendCompanionMessage } from "./chat-engine/chat";
import {
  applyMemoryCandidates,
  createMemory,
  generateMemoryCandidates,
  isMemoryInjectable,
  memoryCategoryLabels,
  memoryScopeLabels,
  selectRelevantMemories,
} from "./memory/memory";
import { ModelProviderError } from "./model-provider/openai";
import {
  defaultProviderConfig,
  loadActiveCompanionId,
  loadCompanions,
  loadMemories,
  loadMessages,
  loadPrivacyNoticeAck,
  loadProviderConfig,
  loadStyleSummaries,
  saveActiveCompanionId,
  saveCompanions,
  saveMemories,
  saveMessages,
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
  RelationshipType,
  StyleSummary,
  UserMemory,
} from "./types";

const memoryCategories = Object.entries(memoryCategoryLabels) as Array<[MemoryCategory, string]>;
const importanceOptions: MemoryImportance[] = [1, 2, 3];
const relationshipOptions = Object.entries(relationshipLabels) as Array<[RelationshipType, string]>;
const memoryVisibleActions = new Set(["create", "merge", "replace"]);
const initialPrivacyNoticeAck = loadPrivacyNoticeAck();

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

function maskKey(apiKey: string): string {
  if (!apiKey) return "未填写";
  if (apiKey.length <= 8) return "已保存";
  return `${apiKey.slice(0, 4)}...${apiKey.slice(-4)}`;
}

function newCompanion(): CompanionProfile {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    name: "",
    relationshipType: "friend",
    traitIds: ["tone-warm", "emotion-hold", "solve-listen", "boundary-independent"],
    customPersonalityText: "",
    intimacyBoundary: "尊重边界，不制造依赖。",
    responsePace: "跟随用户节奏。",
    problemSolvingStyle: "先接住情绪，再给可执行建议。",
    boundaryNotes: "不冒充真实个人或专业人士。",
    createdAt: now,
    updatedAt: now,
  };
}

function companionDisplayName(companion: CompanionProfile): string {
  return companion.name.trim() || "未命名伴侣";
}

export default function App() {
  const [activeView, setActiveView] = useState<AppView>("chat");
  const [companions, setCompanions] = useState<CompanionProfile[]>(() => loadCompanions());
  const [activeCompanionId, setActiveCompanionId] = useState<string>(() => loadActiveCompanionId());
  const [providerConfig, setProviderConfig] = useState<ModelProviderConfig>(() => loadProviderConfig());
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadMessages());
  const [memories, setMemories] = useState<UserMemory[]>(() => loadMemories());
  const [styleSummaries, setStyleSummaries] = useState<StyleSummary[]>(() => loadStyleSummaries());
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
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

  const activeCompanion = useMemo(
    () => getCompanionProfile(activeCompanionId, companions),
    [activeCompanionId, companions],
  );
  const activeStyleSummary = useMemo(
    () => getBoundStyleSummary(styleSummaries, activeCompanion.id, activeCompanion.activeStyleSummaryId),
    [activeCompanion, styleSummaries],
  );
  const activeTraits = useMemo(() => getTraitsByIds(activeCompanion.traitIds), [activeCompanion.traitIds]);
  const traitConflicts = useMemo(() => getTraitConflictLabels(activeCompanion.traitIds), [activeCompanion.traitIds]);
  const relevantPreview = useMemo(
    () => selectRelevantMemories(memories, input || messages[messages.length - 1]?.content || "", activeCompanion.id),
    [input, memories, messages, activeCompanion.id],
  );
  const visibleCandidates = latestCandidates.filter((candidate) => memoryVisibleActions.has(candidate.suggestedAction));
  const visibleMemories = memories.filter((memory) => {
    if (memoryFilter !== "all" && memory.scope !== memoryFilter) return false;
    if (memory.scope === "companion" && memory.companionId !== activeCompanion.id) return false;
    return memory.status !== "deleted";
  });

  useEffect(() => saveActiveCompanionId(activeCompanion.id), [activeCompanion.id]);
  useEffect(() => saveCompanions(companions), [companions]);
  useEffect(() => saveMessages(messages), [messages]);
  useEffect(() => saveMemories(memories), [memories]);
  useEffect(() => saveStyleSummaries(styleSummaries), [styleSummaries]);

  function updateProviderConfig(field: keyof ModelProviderConfig, value: string) {
    setSettingsSaved(false);
    setProviderConfig((current) => ({
      ...current,
      [field]: value,
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

  function addCompanion() {
    const companion = newCompanion();
    setCompanions((current) => [companion, ...current]);
    setActiveCompanionId(companion.id);
    setActiveView("companion");
  }

  function toggleTrait(traitId: string) {
    const exists = activeCompanion.traitIds.includes(traitId);
    const nextTraitIds = exists
      ? activeCompanion.traitIds.filter((id) => id !== traitId)
      : [...activeCompanion.traitIds, traitId].slice(0, 6);
    updateCompanion(activeCompanion.id, { traitIds: nextTraitIds });
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const userInput = input.trim();
    if (!userInput || isSending) return;

    const userMessage = makeMessage("user", userInput);
    const nextMessages = [...messages, userMessage];
    const candidates = generateMemoryCandidates(userInput, memories, activeCompanion.id);
    const actionableCandidates = candidates.filter((candidate) => memoryVisibleActions.has(candidate.suggestedAction));
    const nextMemories = applyMemoryCandidates(actionableCandidates, memories);

    setMessages(nextMessages);
    setLatestCandidates(candidates);
    if (nextMemories !== memories) {
      setMemories(nextMemories);
    }
    setInput("");
    setError("");
    setIsSending(true);

    try {
      const reply = await sendCompanionMessage({
        config: providerConfig,
        companion: activeCompanion,
        styleSummary: activeStyleSummary,
        memories: nextMemories,
        history: messages,
        userInput,
      });
      setMessages([...nextMessages, makeMessage("assistant", reply)]);
    } catch (err) {
      setError(getFriendlyError(err));
    } finally {
      setIsSending(false);
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
    setMessages([]);
    setError("");
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

  const isConfigured =
    Boolean(providerConfig.baseURL.trim()) &&
    Boolean(providerConfig.model.trim()) &&
    Boolean(providerConfig.apiKey.trim());

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

        <nav className="nav-list" aria-label="主导航">
          <button className={activeView === "chat" ? "active" : ""} onClick={() => setActiveView("chat")}>
            <MessageCircle size={18} />
            聊天
          </button>
          <button className={activeView === "companion" ? "active" : ""} onClick={() => setActiveView("companion")}>
            <UserRoundCog size={18} />
            伴侣
          </button>
          <button className={activeView === "memory" ? "active" : ""} onClick={() => setActiveView("memory")}>
            <BookOpen size={18} />
            记忆
          </button>
          <button className={activeView === "style" ? "active" : ""} onClick={() => setActiveView("style")}>
            <Sparkles size={18} />
            风格
          </button>
          <button className={activeView === "settings" ? "active" : ""} onClick={() => setActiveView("settings")}>
            <Settings size={18} />
            设置
          </button>
        </nav>

        <section className="status-panel" aria-label="当前状态">
          <div className="status-row">
            <span>当前伴侣</span>
            <strong>{companionDisplayName(activeCompanion)}</strong>
          </div>
          <div className="status-row">
            <span>关系</span>
            <strong>{relationshipLabels[activeCompanion.relationshipType]}</strong>
          </div>
          <div className="status-row">
            <span>模型</span>
            <strong>{providerConfig.model || "未配置"}</strong>
          </div>
          <div className="status-row">
            <span>API Key</span>
            <strong>{maskKey(providerConfig.apiKey)}</strong>
          </div>
          <div className={isConfigured ? "safe-note good" : "safe-note warn"}>
            <ShieldCheck size={16} />
            {isConfigured ? "配置仅保存在本机浏览器" : "先到设置填写接口配置"}
          </div>
          <button className="text-button" type="button" onClick={openPrivacyNotice}>
            查看本地隐私说明
          </button>
        </section>
      </aside>

      <main className="main">
        {isPrivacyNoticeOpen && (
          <section className="privacy-notice" aria-label="本地隐私提示">
            <div>
              <strong>本地隐私提示</strong>
              <p>
                当前 Demo 没有后端服务器。你的 API Key、聊天记录、长期记忆、伴侣配置和风格摘要会保存在当前浏览器本地；
                换浏览器或清理浏览器数据可能会丢失。聊天时，浏览器会用你填写的接口直接请求模型服务商。
              </p>
            </div>
            <div className="privacy-notice-actions">
              {privacyNoticeAck.acknowledged && (
                <button className="ghost-button" type="button" onClick={() => setIsPrivacyNoticeOpen(false)}>
                  关闭
                </button>
              )}
              <button className="primary-button" type="button" onClick={acknowledgePrivacyNotice}>
                知道了
              </button>
            </div>
          </section>
        )}

        <header className="topbar">
          <div>
            <p className="eyebrow">v0.2 本地自定义伴侣 Demo</p>
            <h2>
              {activeView === "chat"
                ? "陪伴聊天"
                : activeView === "settings"
                  ? "BYOK 设置"
                  : activeView === "memory"
                    ? "长期记忆"
                    : activeView === "style"
                      ? "风格参考"
                      : "自定义伴侣"}
            </h2>
          </div>
          <button className="ghost-button" onClick={() => setActiveView("settings")}>
            <KeyRound size={17} />
            配置接口
          </button>
        </header>

        {activeView === "chat" && (
          <div className="content-grid chat-layout">
            <section className="workspace-panel companion-panel">
              <div className="section-title">
                <Bot size={18} />
                <h3>当前伴侣</h3>
              </div>
              <div className="companion-list">
                {companions.map((profile) => (
                  <button
                    key={profile.id}
                    className={profile.id === activeCompanion.id ? "companion-card selected" : "companion-card"}
                    onClick={() => setActiveCompanionId(profile.id)}
                  >
                    <span>{relationshipLabels[profile.relationshipType]}</span>
                    <strong>{companionDisplayName(profile)}</strong>
                    <small>{getTraitsByIds(profile.traitIds).map((trait) => trait.label).join("、") || "未选择特质"}</small>
                  </button>
                ))}
              </div>
              <button className="ghost-button full-width" onClick={addCompanion}>
                <Plus size={16} />
                新建伴侣
              </button>
              <div className="profile-detail">
                <h3>{companionDisplayName(activeCompanion)}</h3>
                <p>{activeCompanion.customPersonalityText || "还没有自定义性格补充。"}</p>
                <p>{activeCompanion.boundaryNotes || "默认遵守安全边界。"}</p>
              </div>
            </section>

            <section className="workspace-panel chat-panel">
              <div className="message-list" aria-live="polite">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <Brain size={30} />
                    <h3>创建或选择一个伴侣，然后开始聊天</h3>
                    <p>系统会注入当前伴侣设定、风格参考、全局记忆和当前伴侣专属记忆。</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <article key={message.id} className={`message ${message.role}`}>
                      <span>{message.role === "user" ? "你" : companionDisplayName(activeCompanion)}</span>
                      <p>{message.content}</p>
                    </article>
                  ))
                )}
                {isSending && (
                  <article className="message assistant">
                    <span>{companionDisplayName(activeCompanion)}</span>
                    <p>正在认真想怎么回你...</p>
                  </article>
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
                  <button className="primary-button" type="submit" disabled={isSending || !input.trim()}>
                    <Send size={17} />
                    发送
                  </button>
                </div>
              </form>
            </section>

            <section className="workspace-panel memory-preview">
              <div className="section-title">
                <BookOpen size={18} />
                <h3>本轮相关记忆</h3>
              </div>
              {relevantPreview.length === 0 ? (
                <p className="muted">还没有可注入的 active 记忆。可以聊天自动沉淀，或去“记忆”手动添加。</p>
              ) : (
                <ul className="memory-mini-list">
                  {relevantPreview.map((memory) => (
                    <li key={memory.id}>
                      <strong>
                        {memoryScopeLabels[memory.scope]} · {memoryCategoryLabels[memory.category]}
                      </strong>
                      <span>{memory.content}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="style-mini">
                <strong>风格参考</strong>
                <span>{activeStyleSummary ? activeStyleSummary.name : "未绑定"}</span>
              </div>
            </section>
          </div>
        )}

        {activeView === "companion" && (
          <div className="content-grid companion-editor-layout">
            <section className="workspace-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{companions.length} 个本地伴侣</p>
                  <h3>选择或新建</h3>
                </div>
                <button className="ghost-button" onClick={addCompanion}>
                  <Plus size={16} />
                  新建
                </button>
              </div>
              <div className="companion-list">
                {companions.map((profile) => (
                  <button
                    key={profile.id}
                    className={profile.id === activeCompanion.id ? "companion-card selected" : "companion-card"}
                    onClick={() => setActiveCompanionId(profile.id)}
                  >
                    <span>{relationshipLabels[profile.relationshipType]}</span>
                    <strong>{companionDisplayName(profile)}</strong>
                    <small>{profile.customPersonalityText || "未填写自定义性格"}</small>
                  </button>
                ))}
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
                    value={activeCompanion.name}
                    onChange={(event) => updateCompanion(activeCompanion.id, { name: event.target.value })}
                    placeholder="可留空；提示词会使用“当前伴侣”，不会编造固定名字"
                  />
                </label>
                <label>
                  关系类型
                  <select
                    value={activeCompanion.relationshipType}
                    onChange={(event) =>
                      updateCompanion(activeCompanion.id, { relationshipType: event.target.value as RelationshipType })
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
                    value={activeCompanion.customPersonalityText ?? ""}
                    onChange={(event) =>
                      updateCompanion(activeCompanion.id, { customPersonalityText: event.target.value })
                    }
                    rows={3}
                    placeholder="例如：说话更像可靠的朋友，少说大道理，多陪我把事情拆开。"
                  />
                </label>
                <label>
                  亲密边界
                  <input
                    value={activeCompanion.intimacyBoundary ?? ""}
                    onChange={(event) => updateCompanion(activeCompanion.id, { intimacyBoundary: event.target.value })}
                  />
                </label>
                <label>
                  回应节奏
                  <input
                    value={activeCompanion.responsePace ?? ""}
                    onChange={(event) => updateCompanion(activeCompanion.id, { responsePace: event.target.value })}
                  />
                </label>
                <label>
                  问题处理方式
                  <input
                    value={activeCompanion.problemSolvingStyle ?? ""}
                    onChange={(event) =>
                      updateCompanion(activeCompanion.id, { problemSolvingStyle: event.target.value })
                    }
                  />
                </label>
                <label>
                  边界备注
                  <textarea
                    value={activeCompanion.boundaryNotes ?? ""}
                    onChange={(event) => updateCompanion(activeCompanion.id, { boundaryNotes: event.target.value })}
                    rows={2}
                  />
                </label>
              </div>
            </section>

            <section className="workspace-panel trait-panel">
              <div className="section-title">
                <Sparkles size={18} />
                <h3>性格/特质组合</h3>
              </div>
              <div className="trait-grid">
                {companionTraits.map((trait) => (
                  <button
                    key={trait.id}
                    className={activeCompanion.traitIds.includes(trait.id) ? "trait-chip selected" : "trait-chip"}
                    onClick={() => toggleTrait(trait.id)}
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
            </section>
          </div>
        )}

        {activeView === "settings" && (
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
              <button className="ghost-button" type="button" onClick={openPrivacyNotice}>
                <ShieldCheck size={17} />
                查看本地隐私说明
              </button>
              <button className="primary-button" type="submit">
                <Save size={17} />
                保存设置
              </button>
            </form>
          </section>
        )}

        {activeView === "memory" && (
          <div className="content-grid memory-layout">
            <section className="workspace-panel">
              <div className="section-title">
                <Plus size={18} />
                <h3>新增记忆</h3>
              </div>
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
                    rows={5}
                  />
                </label>
                <button className="primary-button" type="submit" disabled={!memoryDraft.content.trim()}>
                  <Plus size={17} />
                  添加记忆
                </button>
              </form>
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
                        {memoryScopeLabels[memory.scope]} · {memoryCategoryLabels[memory.category]} · {memory.status} · 置信度{" "}
                        {memory.confidence.toFixed(2)}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {activeView === "style" && (
          <div className="content-grid style-layout">
            <section className="workspace-panel">
              <div className="section-title">
                <Sparkles size={18} />
                <h3>导入前提示</h3>
              </div>
              <div className="privacy-callout">
                <ShieldCheck size={18} />
                <p>
                  请只导入你有权使用、已获得必要同意，且不会侵犯他人隐私的聊天记录。导入内容将用于生成“风格参考摘要”，帮助你的虚构 AI
                  伴侣学习语气和互动方式；它不会复刻、复活或冒充任何真实个人。P0 不会把导入内容发送给第三方模型。
                </p>
              </div>
              <label>
                粘贴少量参考文本
                <textarea
                  value={styleImportText}
                  onChange={(event) => setStyleImportText(event.target.value)}
                  rows={8}
                  placeholder="粘贴你有权使用的片段；保存后请编辑摘要字段，而不是保留原文。"
                />
              </label>
              <button className="primary-button" onClick={createStyleFromImport} disabled={!styleImportText.trim()}>
                <Plus size={17} />
                生成本地摘要草稿
              </button>
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
        )}
      </main>
    </div>
  );
}
