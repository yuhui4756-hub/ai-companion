import type { MemoryCategory, UserMemory } from "../types";

export const memoryCategoryLabels: Record<MemoryCategory, string> = {
  basic: "基本信息",
  preference: "喜好偏好",
  event: "重要事件",
  emotion: "情绪模式",
  relationship: "关系进展",
  boundary: "禁忌雷区",
};

const categoryKeywords: Record<MemoryCategory, string[]> = {
  basic: ["我叫", "名字", "职业", "上学", "工作", "城市", "年龄"],
  preference: ["喜欢", "不喜欢", "偏好", "习惯", "希望你", "语气"],
  event: ["考试", "面试", "纪念日", "目标", "计划", "项目", "困难"],
  emotion: ["焦虑", "压力", "低落", "害怕", "难过", "失眠", "烦"],
  relationship: ["称呼", "关系", "陪我", "亲密", "边界", "朋友"],
  boundary: ["不要", "别提", "雷区", "讨厌", "不能接受", "隐私"],
};

export function createMemory(category: MemoryCategory, content: string, importance: UserMemory["importance"]): UserMemory {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    category,
    content: content.trim(),
    importance,
    createdAt: now,
    updatedAt: now,
  };
}

type MemorySuggestion = Pick<UserMemory, "category" | "content" | "importance">;

function normalizeMemoryText(value: string): string {
  return value.replace(/\s+/g, "").replace(/[。！？!?,，、；;：:]/g, "").toLowerCase();
}

function pickMatch(input: string, patterns: RegExp[]): string | null {
  for (const pattern of patterns) {
    const matched = input.match(pattern)?.[1]?.trim();
    if (matched) return matched.replace(/[。！？!?,，、；;：:].*$/, "").trim();
  }
  return null;
}

export function suggestMemoriesFromUserInput(input: string, existingMemories: UserMemory[]): MemorySuggestion[] {
  const text = input.trim();
  if (text.length < 5) return [];
  const suggestions: MemorySuggestion[] = [];

  const relationshipName = pickMatch(text, [
    /(?:希望你|以后你|你以后|请你|你可以)(?:叫我|称呼我)([^，。！？!?,；;]{1,16})/,
    /(?:叫我|称呼我)([^，。！？!?,；;]{1,16})/,
  ]);
  if (relationshipName) {
    pushUniqueSuggestion(
      suggestions,
      {
        category: "relationship",
        content: `用户希望被称呼为“${relationshipName}”。`,
        importance: 3,
      },
      existingMemories,
    );
  }

  const userName = pickMatch(text, [/我叫([^，。！？!?,；;]{1,16})/, /我的名字是([^，。！？!?,；;]{1,16})/]);
  if (userName) {
    pushUniqueSuggestion(
      suggestions,
      {
        category: "basic",
        content: `用户自称“${userName}”。`,
        importance: 2,
      },
      existingMemories,
    );
  }

  const boundary = pickMatch(text, [
    /(?:我不喜欢|不喜欢|讨厌|别|不要)([^。！？!?]{2,36})/,
    /(?:别提|不要提|不想被提起)([^。！？!?]{0,36})/,
  ]);
  if (boundary) {
    pushUniqueSuggestion(
      suggestions,
      {
        category: "boundary",
        content: `用户不喜欢或不希望：${boundary}。`,
        importance: 3,
      },
      existingMemories,
    );
  }

  if (!relationshipName && !boundary) {
    const preference = pickMatch(text, [
      /(?:我希望你|希望你|以后请你|请你|你可以)([^。！？!?]{2,40})/,
      /(?:我喜欢|喜欢)([^。！？!?]{2,36})/,
    ]);
    if (preference) {
      pushUniqueSuggestion(
        suggestions,
        {
          category: "preference",
          content: `用户偏好：${preference}。`,
          importance: 2,
        },
        existingMemories,
      );
    }
  }

  const emotion = pickMatch(text, [
    /(?:我容易|我经常|最近总是|最近有点|我会)(焦虑|紧张|低落|失眠|压力大|烦躁|害怕|难过)(?:[^。！？!?]{0,24})/,
    /(?:一到|每次)([^。！？!?]{2,18})(?:就会|就)(焦虑|紧张|低落|失眠|烦躁|害怕|难过)/,
  ]);
  if (emotion) {
    pushUniqueSuggestion(
      suggestions,
      {
        category: "emotion",
        content: `用户提到自己的情绪模式：${text.slice(0, 48)}。`,
        importance: 2,
      },
      existingMemories,
    );
  }

  const event = pickMatch(text, [
    /(?:我要|我准备|我正在准备|接下来要)(考试|面试|答辩|项目|搬家|旅行|复习|求职)(?:[^。！？!?]{0,24})/,
    /(?:我的目标是|我今年想|我计划)([^。！？!?]{2,40})/,
  ]);
  if (event) {
    pushUniqueSuggestion(
      suggestions,
      {
        category: "event",
        content: `用户的重要事件或目标：${text.slice(0, 52)}。`,
        importance: 2,
      },
      existingMemories,
    );
  }

  return suggestions.slice(0, 3);
}

export function suggestMemoryFromUserInput(input: string, existingMemories: UserMemory[]): MemorySuggestion | null {
  return suggestMemoriesFromUserInput(input, existingMemories)[0] ?? null;
}

function pushUniqueSuggestion(
  suggestions: MemorySuggestion[],
  suggestion: MemorySuggestion,
  existingMemories: UserMemory[],
): void {
  const normalizedSuggestion = normalizeMemoryText(suggestion.content);
  const exists = [...existingMemories, ...suggestions.map((item) => ({ content: item.content }) as UserMemory)].some((memory) => {
    const normalizedMemory = normalizeMemoryText(memory.content);
    return normalizedMemory.includes(normalizedSuggestion) || normalizedSuggestion.includes(normalizedMemory);
  });
  if (!exists) {
    suggestions.push(suggestion);
  }
}

export function selectRelevantMemories(memories: UserMemory[], userInput: string, limit = 6): UserMemory[] {
  const normalizedInput = userInput.toLowerCase();
  return [...memories]
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
      return {
        memory,
        score: memory.importance + categoryScore + contentScore,
      };
    })
    .sort((a, b) => b.score - a.score || b.memory.updatedAt.localeCompare(a.memory.updatedAt))
    .slice(0, limit)
    .map((item) => item.memory);
}
