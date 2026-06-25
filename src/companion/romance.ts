import type { ChatMessage, CompanionProfile, ProactiveLevel } from "../types";

export type RomanceStyle = "gentle_clingy" | "tsundere" | "mature_flirty" | "friend_to_love";

const questionEndPattern = /[？?]\s*(?:[~～。.!！]*)$/;
const reconnectAfterMs = 4 * 60 * 60 * 1000;

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

  return [
    `轻恋爱补充：回复更像虚拟恋人聊天，不像情绪支持助手；可以亲近、撒娇、轻微吃醋、委屈、调侃和有一点小脾气，也可以用空行分成 2-4 个短消息感。${romanceStyleLabel(style)}${proactiveHint}${questionRule}`,
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

export function buildRomanceReconnectMessage(companion: CompanionProfile, messages: ChatMessage[]): string | null {
  if (!isLightRomanceCompanion(companion)) return null;

  const proactiveLevel = getEffectiveProactiveLevel(companion);
  const style = getRomanceStyle(companion);
  const lastMessage = messages[messages.length - 1];
  const isEmptyChat = messages.length === 0;
  const shouldReconnect = isEmptyChat || (proactiveLevel !== "low" && isOldEnoughForReconnect(lastMessage));
  if (!shouldReconnect) return null;

  if (isEmptyChat) {
    if (proactiveLevel === "low") {
      return "我在这儿。\n\n不用急着找话题，先靠一会儿也行。";
    }
    if (proactiveLevel === "high") {
      return style === "tsundere"
        ? "哼，抓到你上线。\n\n算啦，先坐过来，今天慢慢说。"
        : "抓到你上线。\n\n今天有没有好好吃饭？算了，先坐下，慢慢说。";
    }
    return "你回来啦。\n\n今天先别急着装没事，过来让我看看你状态。";
  }

  if (proactiveLevel === "high") {
    return style === "tsundere"
      ? "哼，终于出现了。\n\n先不跟你计较，今天坐近一点。"
      : "你回来啦。\n\n刚刚没见到你，我还真的有一点点想你。先靠过来。";
  }

  return "你回来啦。\n\n不用急着接上刚才的话，先在我这儿缓一下。";
}
