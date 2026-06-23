import type { ChatMessage, CompanionProfile, OpenAIChatMessage, UserMemory } from "../types";
import { memoryCategoryLabels } from "../memory/memory";
import { buildSafetyInstruction, hasHighRiskContent } from "../safety/safety";

function formatMemories(memories: UserMemory[]): string {
  if (memories.length === 0) {
    return "暂无相关长期记忆。";
  }

  return memories
    .map((memory) => `- [${memoryCategoryLabels[memory.category]} / 重要度${memory.importance}] ${memory.content}`)
    .join("\n");
}

export function buildSystemPrompt(
  companion: CompanionProfile,
  memories: UserMemory[],
  latestUserInput: string,
): string {
  const riskInstruction = hasHighRiskContent(latestUserInput)
    ? "\n用户当前可能涉及高风险表达。请先稳定、关心地回应，建议联系现实中可信的人或当地紧急服务，不要给出危险方法。"
    : "";

  return [
    "你是一个中文 AI 伴侣网页 Demo 中的伴侣，不是普通客服机器人。",
    `当前伴侣：${companion.title}（${companion.name}）。`,
    `关系类型：${companion.relationshipType}`,
    `语气风格：${companion.tone}`,
    `情绪回应方式：${companion.emotionalStyle}`,
    `解决问题方式：${companion.problemSolvingStyle}`,
    `角色扮演范围：${companion.roleplayScope}`,
    companion.prompt,
    "",
    "回应顺序：先判断用户是在倾诉、闲聊、求建议、任务求助还是角色扮演；有情绪先接住，有具体问题再给可执行帮助。避免空泛安慰。",
    "",
    "可参考的长期记忆：",
    formatMemories(memories),
    "",
    buildSafetyInstruction(),
    riskInstruction,
  ].join("\n");
}

export function buildChatMessages(
  companion: CompanionProfile,
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
      content: buildSystemPrompt(companion, memories, latestUserInput),
    },
    ...recentHistory,
    {
      role: "user",
      content: latestUserInput,
    },
  ];
}
