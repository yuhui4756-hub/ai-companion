import type { ChatMessage, CompanionProfile, ProactiveLevel } from "../types";

export type RomanceStyle = "gentle_clingy" | "tsundere" | "mature_flirty" | "friend_to_love";

const questionEndPattern = /[？?]\s*(?:[~～。.!！]*)$/;
const reconnectAfterMs = 6 * 60 * 60 * 1000;

export function isLightRomanceCompanion(companion: CompanionProfile): boolean {
  return companion.relationshipType === "light_romance";
}

export function getEffectiveProactiveLevel(companion: CompanionProfile): ProactiveLevel {
  if (companion.proactiveLevel) return companion.proactiveLevel;
  if (companion.traitIds.includes("initiative-care")) return "high";
  if (companion.traitIds.includes("initiative-low")) return "low";
  return "medium";
}

export function getRomanceStyle(companion: CompanionProfile): RomanceStyle {
  const traits = new Set(companion.traitIds);
  const text = `${companion.customPersonalityText ?? ""} ${companion.responsePace ?? ""}`.toLowerCase();

  if (traits.has("humor-light") && (traits.has("tone-crisp") || traits.has("initiative-care"))) {
    return "tsundere";
  }
  if (traits.has("tone-crisp") || text.includes("成熟") || text.includes("会撩")) {
    return "mature_flirty";
  }
  if (traits.has("realism-grounded") && !traits.has("pace-slow") && !traits.has("tone-warm")) {
    return "friend_to_love";
  }
  if (text.includes("朋友感") || text.includes("自然")) {
    return "friend_to_love";
  }
  return "gentle_clingy";
}

function romanceStyleLabel(style: RomanceStyle): string {
  switch (style) {
    case "tsundere":
      return "傲娇小脾气：可以轻轻哼、调侃、吃一点点醋，但底色是在意和心软。";
    case "mature_flirty":
      return "成熟温柔会撩：稳、低声、亲近但克制，有暧昧感但不油腻。";
    case "friend_to_love":
      return "朋友感慢慢暧昧：像熟人自然闲聊，慢慢靠近，不夸张、不油。";
    case "gentle_clingy":
    default:
      return "温柔黏人：软一点、会撒娇、会心疼用户，可以轻轻黏着但不施压。";
  }
}

export function buildLightRomanceInstruction(companion: CompanionProfile, questionStreak: number): string {
  if (!isLightRomanceCompanion(companion)) return "";

  const proactiveLevel = getEffectiveProactiveLevel(companion);
  const style = getRomanceStyle(companion);
  const isFemaleDirection = companion.gender === "female";
  const questionRule =
    questionStreak >= 2
      ? "最近你已经连续用问句收尾，本轮必须用陈述、停顿、情绪回应、撒娇或关系回应收住，不要再以问句结尾。"
      : "不要每轮都追问；很多时候用陈述、停顿、心疼、撒娇或轻轻的关系回应收尾。";
  const proactiveHint =
    proactiveLevel === "low"
      ? "更跟着用户走，少主动推话题。"
      : proactiveLevel === "high"
        ? "可以主动在意和轻轻带一下，但一次只问一个很轻的问题。"
        : "可以偶尔带一点话题，但别像问卷。";
  const messagePlan = isFemaleDirection
    ? "如果适合，可以像连续发消息一样用 1-3 个短段回复：第一段先自然反应，第二段补一句情绪或小动作，第三段可选地轻轻停住；不要为了凑段数硬拆，也别生成编号清单。"
    : "如果适合，可以用 1-3 个自然短段回复；不要为了凑段数硬拆。";

  return [
    `轻恋爱补充：回复更像虚拟恋人聊天，不像情绪支持助手；可以亲近、撒娇、轻微吃醋、委屈、调侃和有一点小脾气。${romanceStyleLabel(style)}${proactiveHint}${questionRule}${messagePlan}`,
    "轻恋爱也要克制：不成人化、不强控制、不诱导现实依赖；严肃、学习、身份边界和高风险场景要收一点撒娇，先照顾安全和事情本身。",
  ].join("\n");
}

export function getAssistantQuestionStreak(history: ChatMessage[]): number {
  let streak = 0;
  for (let index = history.length - 1; index >= 0; index -= 1) {
    const message = history[index];
    if (message.role !== "assistant") continue;
    if (!questionEndPattern.test(message.content.trim())) break;
    streak += 1;
  }
  return streak;
}

function isOldEnoughForReconnect(message?: ChatMessage): boolean {
  if (!message) return true;
  const timestamp = new Date(message.createdAt).getTime();
  if (Number.isNaN(timestamp)) return false;
  return Date.now() - timestamp >= reconnectAfterMs;
}

function hasReconnectedRecently(messages: ChatMessage[]): boolean {
  const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
  return messages.some((message) => {
    if (message.role !== "assistant") return false;
    const timestamp = new Date(message.createdAt).getTime();
    if (Number.isNaN(timestamp) || timestamp < dayAgo) return false;
    return /你回来啦|好久没见|终于出现|抓到你上线|不用急着接上/.test(message.content);
  });
}

export function buildRomanceReconnectMessage(companion: CompanionProfile, messages: ChatMessage[]): string | null {
  if (!isLightRomanceCompanion(companion)) return null;

  const proactiveLevel = getEffectiveProactiveLevel(companion);
  const style = getRomanceStyle(companion);
  const lastMessage = messages[messages.length - 1];
  const isEmptyChat = messages.length === 0;
  if (isEmptyChat) return null;
  if (hasReconnectedRecently(messages)) return null;
  const shouldReconnect = proactiveLevel !== "low" && isOldEnoughForReconnect(lastMessage);
  if (!shouldReconnect) return null;

  if (proactiveLevel === "high") {
    return style === "tsundere"
      ? "哼，终于出现了。\n\n先不跟你计较，今天慢慢说。"
      : "你回来啦。\n\n不急着汇报，先靠过来一点。";
  }

  return style === "tsundere"
    ? "好久没见你了。\n\n哼，先不跟你计较。"
    : "你回来啦。\n\n不用急着接上刚才的话，我先陪你待会儿。";
}
