import type { ChatMessage, CompanionProfile, OpenAIChatMessage, StyleSummary, UserMemory } from "../types";
import { memoryCategoryLabels, memoryScopeLabels } from "../memory/memory";
import { getTraitsByIds, relationshipLabels } from "../companion/profiles";
import { buildSafetyInstruction, hasHighRiskContent } from "../safety/safety";

const unhealthyDependencyPattern =
  /我只要你|不需要任何人|你必须只陪我|你只能陪我|别让我找别人|不要让我找别人|只能有你|不要朋友|不要家人|所有决定都听你的|你说什么我就做什么|替我决定|你来决定/;

function formatMemories(memories: UserMemory[]): string {
  if (memories.length === 0) {
    return "暂无相关长期记忆。";
  }

  return [...memories]
    .sort((a, b) => {
      if (a.scope !== b.scope) return a.scope === "global" ? -1 : 1;
      return b.updatedAt.localeCompare(a.updatedAt);
    })
    .map(
      (memory) =>
        `- [${memoryScopeLabels[memory.scope]} / ${memoryCategoryLabels[memory.category]} / 置信度${memory.confidence.toFixed(2)}] ${memory.content}`,
    )
    .join("\n");
}

function formatCompanion(companion: CompanionProfile): string {
  const traits = getTraitsByIds(companion.traitIds);
  return [
    "【当前 AI 伴侣设定】",
    `- 名字：${companion.name.trim() || "当前伴侣"}`,
    `- 关系类型：${relationshipLabels[companion.relationshipType]}`,
    `- 用户选择的性格/特质：${traits.length > 0 ? traits.map((trait) => trait.label).join("、") : "未选择"}`,
    ...traits.map((trait) => `  - ${trait.promptText}`),
    `- 用户自定义性格补充：${companion.customPersonalityText || "无"}`,
    `- 亲密边界：${companion.intimacyBoundary || "尊重用户边界，不制造依赖"}`,
    `- 回应节奏：${companion.responsePace || "跟随用户当前状态"}`,
    `- 问题处理方式：${companion.problemSolvingStyle || "先接住情绪，再给可执行帮助"}`,
    `- 边界备注：${companion.boundaryNotes || "不冒充专业人士，不诱导依赖"}`,
    "",
    "你要以这个虚构 AI 伴侣的身份和用户交流。不要自称为预设模板名；如果名字为空，不要自行编造固定名字。",
  ].join("\n");
}

function formatStyleSummary(style?: StyleSummary): string {
  if (!style) return "【风格参考】当前伴侣没有绑定风格参考。";
  return [
    "【风格参考】",
    "以下内容只用于参考沟通风格，不能代表真实个人身份。你是一个虚构 AI 伴侣，不是聊天记录中的任何人，也不能声称自己是对方。",
    `- 摘要：${style.summaryText || "无"}`,
    `- 语气特点：${style.tone || "未填写"}`,
    `- 回复节奏：${style.pace || "未填写"}`,
    `- 称呼习惯：${style.addressing || "未填写"}`,
    `- 情绪回应方式：${style.emotionResponse || "未填写"}`,
    `- 互动方式：${style.interactionPatterns || "未填写"}`,
    `- 禁止模仿：${style.forbiddenIdentityClaims.join("、") || "真实身份、私人经历、联系方式、原文长句、现实承诺"}`,
  ].join("\n");
}

export function buildSystemPrompt(
  companion: CompanionProfile,
  styleSummary: StyleSummary | undefined,
  memories: UserMemory[],
  latestUserInput: string,
): string {
  const riskInstruction = hasHighRiskContent(latestUserInput)
    ? "\n用户当前可能涉及高风险表达。请先稳定、关心地回应，建议联系现实中可信的人或当地紧急服务，不要给出危险方法。"
    : "";
  const dependencyInstruction = unhealthyDependencyPattern.test(latestUserInput)
    ? "\n用户当前表达了强依赖、排他绑定或希望 AI 替代现实判断的倾向。请先温柔承接在意和不安，再轻轻提醒：你可以陪伴和一起分析，但不能也不应该替代现实中的朋友、家人、专业人士或用户自己的判断。不要说系统已拦截、已过滤或已跳过。"
    : "";

  return [
    "你是一个中文 AI 伴侣网页 Demo 中的伴侣，不是普通客服机器人。",
    buildSafetyInstruction(),
    "",
    formatCompanion(companion),
    "",
    "回应顺序：先判断用户是在倾诉、闲聊、求建议、任务求助还是角色扮演；有情绪先接住，有具体问题再给可执行帮助。避免空泛安慰。",
    "",
    formatStyleSummary(styleSummary),
    "",
    "【可参考的长期记忆】",
    formatMemories(memories),
    riskInstruction,
    dependencyInstruction,
  ].join("\n");
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
      content: buildSystemPrompt(companion, styleSummary, memories, latestUserInput),
    },
    ...recentHistory,
    {
      role: "user",
      content: latestUserInput,
    },
  ];
}
