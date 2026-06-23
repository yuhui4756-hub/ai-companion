import type { StyleSummary } from "../types";

export function createEmptyStyleSummary(): StyleSummary {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    name: "新的风格参考",
    sourceType: "imported_chat",
    summaryText: "",
    tone: "",
    pace: "",
    addressing: "",
    emotionResponse: "",
    interactionPatterns: "",
    forbiddenIdentityClaims: ["不能声称自己是聊天记录中的真实个人", "不能复制私人经历、联系方式或现实承诺"],
    boundCompanionIds: [],
    userReviewed: true,
    createdAt: now,
    updatedAt: now,
  };
}

export function buildStyleSummaryFromInput(input: string): StyleSummary {
  const summary = createEmptyStyleSummary();
  return {
    ...summary,
    name: "导入聊天风格摘要",
    summaryText: input.trim() ? "用户导入了一段聊天记录，以下字段由用户确认后作为风格摘要使用。原文不进入提示词。" : "",
    tone: inferField(input, ["温柔", "冷淡", "直接", "可爱", "幽默", "克制"], "请填写语气特点"),
    pace: inferField(input, ["慢", "快", "简短", "详细", "追问"], "请填写回复节奏"),
    addressing: inferAddressing(input),
    emotionResponse: inferField(input, ["安慰", "鼓励", "共情", "陪", "抱抱"], "请填写情绪回应方式"),
    interactionPatterns: inferInteractionPatterns(input),
  };
}

function inferField(input: string, keywords: string[], fallback: string): string {
  const matched = keywords.filter((keyword) => input.includes(keyword)).slice(0, 3);
  return matched.length > 0 ? `倾向于${matched.join("、")}。` : fallback;
}

function inferAddressing(input: string): string {
  const matched = input.match(/(?:叫你|叫我|称呼你|称呼我)([^，。！？!?,；;]{1,12})/);
  return matched?.[1] ? `可能使用“${matched[1]}”一类称呼，请由用户确认。` : "请填写称呼习惯";
}

function inferInteractionPatterns(input: string): string {
  const patterns: string[] = [];
  if (/[？?]/.test(input) || input.includes("怎么了") || input.includes("想聊")) {
    patterns.push("会通过轻量追问确认用户状态");
  }
  if (input.includes("抱抱") || input.includes("陪") || input.includes("没事")) {
    patterns.push("先陪伴安抚，再进入具体话题");
  }
  if (input.includes("建议") || input.includes("计划") || input.includes("步骤")) {
    patterns.push("会把建议拆成较小步骤");
  }
  return patterns.length > 0 ? `${patterns.join("；")}。` : "请填写互动方式摘要，避免粘贴原文长句。";
}

export function getBoundStyleSummary(styleSummaries: StyleSummary[], companionId: string, summaryId?: string) {
  return styleSummaries.find(
    (summary) =>
      summary.userReviewed &&
      (summary.id === summaryId || summary.boundCompanionIds.includes(companionId)) &&
      summary.boundCompanionIds.includes(companionId),
  );
}
