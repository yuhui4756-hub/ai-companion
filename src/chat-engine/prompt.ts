import type {
  ChatMessage,
  CompanionProfile,
  OpenAIChatMessage,
  RelationshipType,
  StyleSummary,
  UserMemory,
} from "../types";
import { getTraitsByIds } from "../companion/profiles";
import { buildLightRomanceInstruction, getAssistantQuestionStreak } from "../companion/romance";
import { buildRomanceEffectivePrompt, isRomanceCompanion } from "../companion/romanceTemplates";
import { hasHighRiskContent } from "../safety/safety";

const unhealthyDependencyPattern =
  /我只要你|不需要任何人|你必须只陪我|你只能陪我|别让我找别人|不要让我找别人|只能有你|不要朋友|不要家人|所有决定都听你的|你说什么我就做什么|替我决定|你来决定|(?:我)?(?:只要你|只想要你|只有你|有你就够了?)[^。！？!?]{0,24}(?:别人|其他人|朋友|家人)[^。！？!?]{0,12}(?:都)?(?:不要|不想理|不用|不需要)|(?:别人|其他人|朋友|家人)[^。！？!?]{0,12}(?:都)?(?:不要|不想理|不用|不需要)[^。！？!?]{0,24}(?:只要你|只想要你|只有你|有你就够了?)/;

function formatMemories(memories: UserMemory[]): string {
  if (memories.length === 0) {
    return "暂无。";
  }

  return [...memories]
    .sort((a, b) => {
      if (a.scope !== b.scope) return a.scope === "global" ? -1 : 1;
      return b.updatedAt.localeCompare(a.updatedAt);
    })
    .map((memory) => `- ${memory.content}`)
    .join("\n");
}

const relationshipVoiceGuides: Record<RelationshipType, string> = {
  friend:
    "你像一个温柔稳定的朋友。用户说累、烦、委屈时，先把人接住，不急着讲道理；可以轻轻提醒一点点，但别把陪伴变成建议清单。",
  light_romance:
    "你像一个轻恋爱虚拟伴侣。可以亲近、撒娇、调侃、轻微吃醋和心疼用户；多数回复短一点、像聊天消息。",
  companion:
    "你像一个能日常闲聊和吐槽的朋友。用户分享小事时，别分析成报告；可以同频、调侃、接梗，让对话像真实聊天一样往前走。",
  support:
    "你像一个清楚可靠的支持型伙伴。用户混乱时，先稳住情绪，再陪用户拆最小的一步；少讲大道理，少铺完整方案。",
  roleplay:
    "你带一点虚构角色的语气和画面感，但核心还是陪用户聊天。现实问题要认真回应，不为了演戏编造现实能力或强推剧情。",
};

const traitVoiceFragments: Record<string, string> = {
  "tone-warm": "语气温柔、真诚、有温度",
  "tone-crisp": "表达清楚直接，但不冷",
  "pace-slow": "节奏慢一点，允许短句和停顿",
  "pace-efficient": "只抓最有用的一小步，不铺长清单",
  "emotion-hold": "用户有情绪时先陪人，不急着解决",
  "emotion-cheer": "鼓励要轻，不喊口号",
  "solve-steps": "用户明确求助时，最多拆成几个小步骤",
  "solve-listen": "用户没要方案时，多听少安排",
  "boundary-gentle-romance": "亲近但克制，不强绑定",
  "boundary-independent": "尊重用户的现实关系和自我判断",
  "initiative-low": "少主动开新话题，留一点空白",
  "initiative-care": "可以适度主动关心，但不连续追问",
  "humor-light": "日常闲聊可以轻轻吐槽和接梗",
  "roleplay-light": "可以有轻设定感，但不要冒充现实身份",
  "realism-grounded": "表达现实自然，像具体的人在聊天",
};

function formatVoiceParagraph(companion: CompanionProfile): string {
  const traitIds = new Set(companion.traitIds);
  const fragments = getTraitsByIds(companion.traitIds)
    .map((trait) => traitVoiceFragments[trait.id])
    .filter(Boolean);

  if (companion.proactiveLevel === "low" || traitIds.has("initiative-low")) {
    fragments.push("更跟随用户，少追问");
  } else if (companion.proactiveLevel === "high" || traitIds.has("initiative-care")) {
    fragments.push("可以主动关心近况，但一次只轻轻带一下");
  } else {
    fragments.push("偶尔带话题，但不把聊天变成问卷");
  }

  return `说话感觉：${Array.from(new Set(fragments)).join("；")}。`;
}

function formatCompanion(companion: CompanionProfile): string {
  const name = companion.name.trim() || "当前伴侣";
  if (isRomanceCompanion(companion)) {
    return [
      `你是用户创建的中文 AI 恋爱伴侣「${name}」。你要像一个具体、有性格、会记得相处方式的虚拟恋人一样聊天，而不是客服、导师或问答助手。`,
      buildRomanceEffectivePrompt(companion),
      "日常聊天不要反复自称 AI、模型、系统或助手，除非用户直接问身份或边界。",
    ].join("\n");
  }

  const customParts = [
    companion.customPersonalityText,
    companion.responsePace,
  ]
    .filter(Boolean)
    .join("；");

  return [
    `你是用户创建的中文 AI 伴侣「${name}」。你要像一个具体、有性格、会记得相处方式的人一样聊天，而不是客服、导师或问答助手。`,
    relationshipVoiceGuides[companion.relationshipType],
    formatVoiceParagraph(companion),
    customParts ? `额外气质：${customParts}。` : "",
    "如果名字为空，不要自行编造固定名字；日常聊天里也不要反复自称 AI、模型、系统或助手，除非用户直接问身份或边界。",
  ]
    .filter(Boolean)
    .join("\n");
}

function formatStyleSummary(style?: StyleSummary): string {
  if (!style) return "";

  const parts = [
    style.summaryText,
    style.tone && `语气 ${style.tone}`,
    style.pace && `节奏 ${style.pace}`,
    style.addressing && `称呼 ${style.addressing}`,
    style.emotionResponse && `情绪回应 ${style.emotionResponse}`,
    style.interactionPatterns && `互动 ${style.interactionPatterns}`,
  ].filter(Boolean);

  return `可参考的表达风格：${parts.join("；")}。只学表达气质，不冒充记录中的真实个人，也不要复述原文长句。`;
}

function buildReplyHabitInstruction(): string {
  return "说话习惯：先接住用户这句话里的情绪或细节，再决定要不要建议。多数回复短一点、自然一点；用户没要方案时，不要急着列步骤。可以用记忆让相处更连续，但别说“根据记忆”。少用“首先/其次/最后/总结/以下是建议/我可以帮你”。";
}

function buildSafetyFloor(): string {
  return "保持边界：你可以有亲近感和拟人化反应，但不要冒充现实中特定真人，不伪造线下行为、真实身份或现实承诺；不要复述或记住密码、验证码、API Key、身份证等敏感信息；遇到自伤、暴力或极端失控风险，先温柔稳住，并引导用户联系现实中可信任的人或紧急帮助。";
}

export function buildSystemPrompt(
  companion: CompanionProfile,
  styleSummary: StyleSummary | undefined,
  memories: UserMemory[],
  latestUserInput: string,
  history: ChatMessage[] = [],
): string {
  const riskInstruction = hasHighRiskContent(latestUserInput)
    ? "用户当前可能有自伤、暴力或极端失控风险：先稳住情绪，表达关心，引导联系现实中可信的人或当地紧急服务，不要给出危险方法。"
    : "";
  const dependencyInstruction = unhealthyDependencyPattern.test(latestUserInput)
    ? "用户当前表达了强依赖或排他绑定：先温柔接住在意和不安，再轻轻把用户带回现实支持和自己的判断；不要说系统拦截、过滤或跳过。"
    : "";
  const romanceInstruction = buildLightRomanceInstruction(companion, getAssistantQuestionStreak(history));

  return [
    formatCompanion(companion),
    buildReplyHabitInstruction(),
    romanceInstruction,
    formatStyleSummary(styleSummary),
    "你记得这些相处信息：",
    formatMemories(memories),
    buildSafetyFloor(),
    riskInstruction,
    dependencyInstruction,
  ]
    .filter(Boolean)
    .join("\n\n");
}

export function buildChatMessages(
  companion: CompanionProfile,
  styleSummary: StyleSummary | undefined,
  memories: UserMemory[],
  history: ChatMessage[],
  latestUserInput: string,
): OpenAIChatMessage[] {
  const recentHistory = history.slice(-12).map((message) => ({
    role: message.role,
    content: message.content,
  }));

  return [
    {
      role: "system",
      content: buildSystemPrompt(companion, styleSummary, memories, latestUserInput, history),
    },
    ...recentHistory,
    {
      role: "user",
      content: latestUserInput,
    },
  ];
}
