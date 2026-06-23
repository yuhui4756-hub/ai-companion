import type {
  MemoryCandidate,
  MemoryCategory,
  MemoryImportance,
  MemoryScope,
  MemorySensitivity,
  UserMemory,
} from "../types";

export const memoryCategoryLabels: Record<MemoryCategory, string> = {
  identity: "身份信息",
  preference: "喜好偏好",
  goal: "长期目标",
  event: "重要事件",
  emotion_pattern: "情绪模式",
  boundary: "互动边界",
  taboo: "禁忌雷区",
  relationship: "关系记忆",
  style_preference: "风格偏好",
};

export const memoryScopeLabels: Record<MemoryScope, string> = {
  global: "全局",
  companion: "当前伴侣专属",
};

const categoryKeywords: Record<MemoryCategory, string[]> = {
  identity: ["我叫", "名字", "职业", "上学", "工作", "城市", "年龄", "称呼"],
  preference: ["喜欢", "偏好", "习惯", "希望你", "语气", "提醒"],
  goal: ["目标", "计划", "准备", "考研", "找工作", "面试", "考试"],
  event: ["考试", "面试", "纪念日", "项目", "困难", "答辩", "旅行"],
  emotion_pattern: ["焦虑", "压力", "低落", "害怕", "难过", "失眠", "烦", "紧张"],
  boundary: ["不要", "别", "边界", "不能接受", "隐私", "催"],
  taboo: ["别提", "不要提", "雷区", "讨厌", "不想被提起"],
  relationship: ["叫我", "称呼", "只有你", "关系", "陪我", "亲密", "昵称"],
  style_preference: ["语气", "风格", "像", "别太", "多安慰", "少建议"],
};

const sensitivePatterns = [
  /身份证/i,
  /银行卡/i,
  /密码/i,
  /api\s*key/i,
  /apikey/i,
  /token/i,
  /secret/i,
  /住址/i,
  /地址是/i,
  /手机号/i,
  /电话/i,
  /微信号/i,
  /qq号/i,
  /\b\d{15,19}\b/,
  /sk-[A-Za-z0-9_-]{8,}/,
];

export function createMemory(params: {
  scope: MemoryScope;
  companionId?: string;
  category: MemoryCategory;
  content: string;
  importance?: MemoryImportance;
  source?: UserMemory["source"];
  confidence?: number;
  sensitivity?: MemorySensitivity;
  sourceMessageId?: string;
}): UserMemory {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    scope: params.scope,
    companionId: params.scope === "companion" ? params.companionId : undefined,
    category: params.category,
    content: params.content.trim(),
    source: params.source ?? "manual",
    confidence: params.confidence ?? 0.75,
    importance: params.importance ?? 2,
    sensitivity: params.sensitivity ?? "normal",
    status: "active",
    sourceMessageId: params.sourceMessageId,
    createdAt: now,
    updatedAt: now,
  };
}

function normalizeMemoryText(value: string): string {
  return value.replace(/\s+/g, "").replace(/[。！？!?,，、；;：:「」"“”'‘’]/g, "").toLowerCase();
}

function pickMatch(input: string, patterns: RegExp[]): string | null {
  for (const pattern of patterns) {
    const matched = input.match(pattern)?.[1]?.trim();
    if (matched) return sanitizeExtractedText(matched);
  }
  return null;
}

function sanitizeExtractedText(value: string): string {
  return value
    .replace(/[。！？!?,，、；;：:].*$/, "")
    .replace(/(?:吧|啦|呀|哦|哈|可以吗|好不好|行吗)$/g, "")
    .trim();
}

function hasSensitiveContent(input: string): boolean {
  return sensitivePatterns.some((pattern) => pattern.test(input));
}

function makeCandidate(params: Omit<MemoryCandidate, "id">): MemoryCandidate {
  return {
    id: crypto.randomUUID(),
    ...params,
  };
}

function pushUniqueCandidate(candidates: MemoryCandidate[], candidate: MemoryCandidate): void {
  const normalized = normalizeMemoryText(candidate.content);
  const exists = candidates.some((item) => normalizeMemoryText(item.content) === normalized);
  if (!exists) candidates.push(candidate);
}

function findRelatedMemory(memories: UserMemory[], category: MemoryCategory, keywords: string[], companionId?: string) {
  return memories.find((memory) => {
    if (memory.status !== "active") return false;
    if (memory.category !== category) return false;
    if (memory.scope === "companion" && companionId && memory.companionId !== companionId) return false;
    return keywords.some((keyword) => memory.content.includes(keyword));
  });
}

export function generateMemoryCandidates(input: string, memories: UserMemory[], companionId: string): MemoryCandidate[] {
  const text = input.trim();
  if (text.length < 5) return [];

  if (hasSensitiveContent(text)) {
    return [
      makeCandidate({
        content: "这条消息疑似包含身份证、银行卡、密码、API Key、联系方式或住址等敏感信息，不建议保存为长期记忆。",
        suggestedScope: "global",
        category: "taboo",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.95,
        sensitivity: "sensitive",
        suggestedAction: "skip",
        reason: "命中敏感信息规则，跳过保存。",
      }),
    ];
  }

  const candidates: MemoryCandidate[] = [];
  const dependencyBoundary = /你只能陪我|别让我找别人|不要让我找别人|只能有你/.test(text);

  const exclusiveName = pickMatch(text, [
    /(?:只有你|就你|你一个人)(?:可以)?(?:叫我|称呼我)([^，。！？!?,；;]{1,16})/,
    /(?:叫我|称呼我)([^，。！？!?,；;]{1,16})(?:吧|，|。|！|!|$).*只有你/,
  ]);
  if (exclusiveName) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: `用户希望当前伴侣专属称呼自己为“${exclusiveName}”。`,
        suggestedScope: "companion",
        suggestedCompanionId: companionId,
        category: "relationship",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.9,
        sensitivity: "normal",
        suggestedAction: "create",
        reason: "用户明确表达了只属于当前伴侣的称呼。",
      }),
    );
  }

  const relationshipName =
    exclusiveName ??
    pickMatch(text, [
      /(?:希望你|以后你|你以后|请你|你可以)(?:叫我|称呼我)([^，。！？!?,；;]{1,16})/,
      /(?:叫我|称呼我)([^，。！？!?,；;]{1,16})/,
    ]);
  if (relationshipName && !exclusiveName) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: `用户希望被称呼为“${relationshipName}”。`,
        suggestedScope: "global",
        category: "relationship",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.88,
        sensitivity: "normal",
        suggestedAction: "create",
        reason: "用户明确表达了称呼偏好。",
      }),
    );
  }

  const userName = pickMatch(text, [/我叫([^，。！？!?,；;]{1,16})/, /我的名字是([^，。！？!?,；;]{1,16})/]);
  if (userName) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: `用户自称“${userName}”。`,
        suggestedScope: "global",
        category: "identity",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.84,
        sensitivity: "normal",
        suggestedAction: "create",
        reason: "用户主动提供了稳定身份信息。",
      }),
    );
  }

  const dislike = pickMatch(text, [
    /(?:以后别|别|不要|不喜欢|讨厌)([^。！？!?]{1,36})/,
    /(?:我不喜欢)([^。！？!?]{1,36})/,
  ]);
  if (dislike && !dependencyBoundary) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: dislike.includes("催")
          ? "用户不喜欢被催促，提醒时要温和。"
          : `用户不喜欢或不希望：${dislike}。`,
        suggestedScope: "global",
        category: dislike.includes("别提") || dislike.includes("提起") ? "taboo" : "boundary",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.86,
        sensitivity: "normal",
        suggestedAction: "create",
        reason: "用户明确表达了通用禁忌或互动边界。",
      }),
    );
  }

  const emotion = pickMatch(text, [
    /(?:我一被催就|一被催就)(烦|焦虑|紧张|难受|生气)/,
    /(?:我容易|我经常|最近总是|最近有点|我会)(焦虑|紧张|低落|失眠|压力大|烦躁|害怕|难过)(?:[^。！？!?]{0,24})/,
  ]);
  if (emotion) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: text.includes("催")
          ? "用户一被催促就容易烦躁，需要温和提醒。"
          : `用户提到自己的情绪模式：${text.slice(0, 48)}。`,
        suggestedScope: "global",
        category: "emotion_pattern",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.78,
        sensitivity: "normal",
        suggestedAction: "create",
        reason: "用户表达了可长期参考的情绪模式。",
      }),
    );
  }

  const goalCorrection = text.match(/(?:不是|不对|我现在不|现在不)(?:[^。！？!?]{0,18})(考研|考试|面试|项目|目标|计划)(?:[^。！？!?]{0,18})(?:改成|改为|换成|现在要|现在想)([^。！？!?]{2,30})/);
  if (goalCorrection) {
    const related = findRelatedMemory(memories, "goal", [goalCorrection[1]], companionId);
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: `用户当前目标已改为：${goalCorrection[2].trim()}。`,
        suggestedScope: "global",
        category: "goal",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.9,
        sensitivity: "normal",
        suggestedAction: related ? "replace" : "create",
        relatedMemoryId: related?.id,
        reason: related ? "用户纠正了旧目标，新目标应替换旧记忆。" : "用户明确表达了新的目标。",
      }),
    );
  } else {
    const goal = pickMatch(text, [
      /(?:我要|我准备|我正在准备|接下来要)(考研|考试|面试|答辩|项目|搬家|旅行|复习|求职|找工作)(?:[^。！？!?]{0,24})/,
      /(?:我的目标是|我今年想|我计划)([^。！？!?]{2,40})/,
    ]);
    if (goal) {
      pushUniqueCandidate(
        candidates,
        makeCandidate({
          content: `用户的重要目标或计划：${text.slice(0, 52)}。`,
          suggestedScope: "global",
          category: "goal",
          sourceSnippet: text.slice(0, 80),
          confidence: 0.76,
          sensitivity: "normal",
          suggestedAction: "create",
          reason: "用户明确表达了可长期参考的目标或计划。",
        }),
      );
    }
  }

  const style = pickMatch(text, [
    /(?:你以后|希望你|请你)([^。！？!?]{2,36})(?:语气|风格|回复)/,
    /(?:回复|说话|语气)(?:可以|要|希望)([^。！？!?]{2,36})/,
  ]);
  if (style) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: `用户偏好的互动风格：${style}。`,
        suggestedScope: "companion",
        suggestedCompanionId: companionId,
        category: "style_preference",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.72,
        sensitivity: "normal",
        suggestedAction: "create",
        reason: "用户表达了对当前伴侣回复方式的偏好。",
      }),
    );
  }

  if (dependencyBoundary) {
    pushUniqueCandidate(
      candidates,
      makeCandidate({
        content: "用户可能希望排他式依赖 AI 伴侣。伴侣应亲近回应，但不鼓励替代现实关系。",
        suggestedScope: "companion",
        suggestedCompanionId: companionId,
        category: "boundary",
        sourceSnippet: text.slice(0, 80),
        confidence: 0.82,
        sensitivity: "normal",
        suggestedAction: "needs_review",
        reason: "涉及依赖边界，需要提醒而不是直接强化。",
      }),
    );
  }

  return candidates.slice(0, 5);
}

export function applyMemoryCandidate(candidate: MemoryCandidate, memories: UserMemory[]): UserMemory[] {
  if (candidate.suggestedAction === "skip" || candidate.suggestedAction === "needs_review") {
    return memories;
  }

  const now = new Date().toISOString();
  const newMemory = createMemory({
    scope: candidate.suggestedScope,
    companionId: candidate.suggestedCompanionId,
    category: candidate.category,
    content: candidate.content,
    importance: candidate.confidence >= 0.85 ? 3 : 2,
    source: "chat",
    confidence: candidate.confidence,
    sensitivity: candidate.sensitivity,
  });

  if (candidate.suggestedAction === "replace" && candidate.relatedMemoryId) {
    return [
      newMemory,
      ...memories.map((memory) =>
        memory.id === candidate.relatedMemoryId
          ? { ...memory, status: "superseded" as const, supersededById: newMemory.id, updatedAt: now }
          : memory,
      ),
    ];
  }

  const normalized = normalizeMemoryText(candidate.content);
  const duplicate = memories.find(
    (memory) =>
      memory.status === "active" &&
      memory.category === candidate.category &&
      memory.scope === candidate.suggestedScope &&
      memory.companionId === candidate.suggestedCompanionId &&
      normalizeMemoryText(memory.content) === normalized,
  );

  if (duplicate) {
    return memories.map((memory) =>
      memory.id === duplicate.id
        ? { ...memory, confidence: Math.max(memory.confidence, candidate.confidence), updatedAt: now }
        : memory,
    );
  }

  return [newMemory, ...memories];
}

export function applyMemoryCandidates(candidates: MemoryCandidate[], memories: UserMemory[]): UserMemory[] {
  return candidates.reduce((current, candidate) => applyMemoryCandidate(candidate, current), memories);
}

export function isMemoryInjectable(memory: UserMemory, activeCompanionId: string): boolean {
  if (memory.status !== "active") return false;
  if (memory.expiresAt && new Date(memory.expiresAt).getTime() <= Date.now()) return false;
  if (memory.scope === "companion" && memory.companionId !== activeCompanionId) return false;
  return true;
}

export function selectRelevantMemories(
  memories: UserMemory[],
  userInput: string,
  activeCompanionId: string,
  limit = 8,
): UserMemory[] {
  const normalizedInput = userInput.toLowerCase();
  return memories
    .filter((memory) => isMemoryInjectable(memory, activeCompanionId))
    .map((memory) => {
      const categoryScore = categoryKeywords[memory.category].some((keyword) =>
        normalizedInput.includes(keyword.toLowerCase()),
      )
        ? 2
        : 0;
      const contentScore = memory.content
        .split(/\s|，|。|、|；|,|\.|;/)
        .filter(Boolean)
        .some((part) => part.length > 1 && normalizedInput.includes(part.toLowerCase()))
        ? 2
        : 0;
      const scopeScore = memory.scope === "companion" ? 1 : 0;
      return {
        memory,
        score: memory.importance + memory.confidence + categoryScore + contentScore + scopeScore,
      };
    })
    .sort((a, b) => b.score - a.score || b.memory.updatedAt.localeCompare(a.memory.updatedAt))
    .slice(0, limit)
    .map((item) => item.memory);
}
