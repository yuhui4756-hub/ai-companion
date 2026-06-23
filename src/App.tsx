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
  Trash2,
} from "lucide-react";
import { companionProfiles, getCompanionProfile } from "./companion/profiles";
import { sendCompanionMessage } from "./chat-engine/chat";
import { createMemory, memoryCategoryLabels, selectRelevantMemories, suggestMemoriesFromUserInput } from "./memory/memory";
import { ModelProviderError } from "./model-provider/openai";
import {
  defaultProviderConfig,
  loadCompanionType,
  loadMemories,
  loadMessages,
  loadProviderConfig,
  saveCompanionType,
  saveMemories,
  saveMessages,
  saveProviderConfig,
} from "./storage/localStorage";
import type {
  AppView,
  ChatMessage,
  CompanionType,
  MemoryCategory,
  MemoryImportance,
  ModelProviderConfig,
  UserMemory,
} from "./types";

const memoryCategories = Object.entries(memoryCategoryLabels) as Array<[MemoryCategory, string]>;
const importanceOptions: MemoryImportance[] = [1, 2, 3];

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

export default function App() {
  const [activeView, setActiveView] = useState<AppView>("chat");
  const [companionType, setCompanionType] = useState<CompanionType>(() => loadCompanionType());
  const [providerConfig, setProviderConfig] = useState<ModelProviderConfig>(() => loadProviderConfig());
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadMessages());
  const [memories, setMemories] = useState<UserMemory[]>(() => loadMemories());
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState(false);
  const [memoryDraft, setMemoryDraft] = useState({
    category: "preference" as MemoryCategory,
    content: "",
    importance: 2 as MemoryImportance,
  });

  const companion = useMemo(() => getCompanionProfile(companionType), [companionType]);
  const relevantPreview = useMemo(
    () => selectRelevantMemories(memories, input || messages[messages.length - 1]?.content || ""),
    [input, memories, messages],
  );

  useEffect(() => saveCompanionType(companionType), [companionType]);
  useEffect(() => saveMessages(messages), [messages]);
  useEffect(() => saveMemories(memories), [memories]);

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

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const userInput = input.trim();
    if (!userInput || isSending) return;

    const userMessage = makeMessage("user", userInput);
    const nextMessages = [...messages, userMessage];
    const memorySuggestions = suggestMemoriesFromUserInput(userInput, memories);
    const nextMemories =
      memorySuggestions.length > 0
        ? [
            ...memorySuggestions.map((suggestion) =>
              createMemory(suggestion.category, suggestion.content, suggestion.importance),
            ),
            ...memories,
          ]
        : memories;

    setMessages(nextMessages);
    if (memorySuggestions.length > 0) {
      setMemories(nextMemories);
    }
    setInput("");
    setError("");
    setIsSending(true);

    try {
      const reply = await sendCompanionMessage({
        config: providerConfig,
        companion,
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
      createMemory(memoryDraft.category, memoryDraft.content, memoryDraft.importance),
      ...current,
    ]);
    setMemoryDraft({
      category: memoryDraft.category,
      content: "",
      importance: memoryDraft.importance,
    });
  }

  function updateMemory(id: string, patch: Partial<Pick<UserMemory, "category" | "content" | "importance">>) {
    setMemories((current) =>
      current.map((memory) =>
        memory.id === id
          ? {
              ...memory,
              ...patch,
              updatedAt: new Date().toISOString(),
            }
          : memory,
      ),
    );
  }

  function deleteMemory(id: string) {
    setMemories((current) => current.filter((memory) => memory.id !== id));
  }

  function clearChat() {
    setMessages([]);
    setError("");
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
          <button className={activeView === "settings" ? "active" : ""} onClick={() => setActiveView("settings")}>
            <Settings size={18} />
            设置
          </button>
          <button className={activeView === "memory" ? "active" : ""} onClick={() => setActiveView("memory")}>
            <BookOpen size={18} />
            记忆
          </button>
        </nav>

        <section className="status-panel" aria-label="当前状态">
          <div className="status-row">
            <span>当前伴侣</span>
            <strong>{companion.title}</strong>
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
        </section>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">中文单页 Demo</p>
            <h2>{activeView === "chat" ? "陪伴聊天" : activeView === "settings" ? "BYOK 设置" : "长期记忆"}</h2>
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
                <h3>选择伴侣</h3>
              </div>
              <div className="companion-list">
                {companionProfiles.map((profile) => (
                  <button
                    key={profile.id}
                    className={profile.id === companionType ? "companion-card selected" : "companion-card"}
                    onClick={() => setCompanionType(profile.id)}
                  >
                    <span>{profile.title}</span>
                    <strong>{profile.name}</strong>
                    <small>{profile.tone}</small>
                  </button>
                ))}
              </div>
              <div className="profile-detail">
                <h3>{companion.name}</h3>
                <p>{companion.emotionalStyle}</p>
                <p>{companion.problemSolvingStyle}</p>
              </div>
            </section>

            <section className="workspace-panel chat-panel">
              <div className="message-list" aria-live="polite">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <Brain size={30} />
                    <h3>先选一个伴侣，然后开始聊天</h3>
                    <p>系统会把当前伴侣人设和相关长期记忆注入提示词。API Key 只保存在你的浏览器本机。</p>
                  </div>
                ) : (
                  messages.map((message) => (
                    <article key={message.id} className={`message ${message.role}`}>
                      <span>{message.role === "user" ? "你" : companion.name}</span>
                      <p>{message.content}</p>
                    </article>
                  ))
                )}
                {isSending && (
                  <article className="message assistant">
                    <span>{companion.name}</span>
                    <p>正在认真想怎么回你...</p>
                  </article>
                )}
              </div>

              {error && <div className="error-banner">{error}</div>}

              <form className="composer" onSubmit={handleSend}>
                <textarea
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="把想说的话写在这里..."
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
                <p className="muted">还没有可注入的长期记忆。可以去“记忆”手动添加。</p>
              ) : (
                <ul className="memory-mini-list">
                  {relevantPreview.map((memory) => (
                    <li key={memory.id}>
                      <strong>{memoryCategoryLabels[memory.category]}</strong>
                      <span>{memory.content}</span>
                    </li>
                  ))}
                </ul>
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
                  第一版不内置、不上传、不代管商业 API Key。浏览器直连你填写的 OpenAI 兼容接口；
                  如果服务商不允许浏览器跨域请求，可能需要后续加本地代理。
                </p>
              </div>
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
                    placeholder="例如：用户希望被叫作小林；用户不喜欢过度说教。"
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
                  <p className="eyebrow">{memories.length} 条本地记忆</p>
                  <h3>查看、编辑、删除</h3>
                </div>
              </div>
              {memories.length === 0 ? (
                <div className="empty-state compact">
                  <BookOpen size={26} />
                  <p>还没有长期记忆。新增后，聊天时会按相关性注入提示词。</p>
                </div>
              ) : (
                <div className="memory-list">
                  {memories.map((memory) => (
                    <article className="memory-card" key={memory.id}>
                      <div className="memory-card-row">
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
                        <select
                          value={memory.importance}
                          onChange={(event) =>
                            updateMemory(memory.id, {
                              importance: Number(event.target.value) as MemoryImportance,
                            })
                          }
                          aria-label="重要度"
                        >
                          {importanceOptions.map((value) => (
                            <option key={value} value={value}>
                              重要度 {value}
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
                        更新于 {new Date(memory.updatedAt).toLocaleString("zh-CN")}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
