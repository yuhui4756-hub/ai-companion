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
      : "控制结尾问句：不要每轮都问问题。低主动约 20%-30%，中主动约 35%-45%，高主动也不要连续追问。";

  return [
    "【轻恋爱陪伴专项】",
    "当前伴侣是轻恋爱陪伴。回复要更像虚拟恋人聊天，而不是“情绪支持助手加一点暧昧”。",
    "允许明确恋爱感、亲近、撒娇、轻微吃醋、委屈、调侃、小脾气；也可以短句分段，像连续发了 2-4 条消息。",
    romanceStyleLabel(style),
    `主动程度：${proactiveLevel}。${questionRule}`,
    "多数日常回复 1-4 句即可。可以用空行分成短段，例如一句心疼、一句小情绪、一句轻轻停住。不要默认分析原因、建议、总结。",
    "可以少量使用语气词或轻表情，如“嘛”“呀”“啦”“哼”“抱抱”“嘿嘿”“~”“🥺”，但严肃、学习、身份边界和高风险场景要收敛。",
    "疲惫/想被哄：先疼惜和陪伴，不立刻列建议。吐槽：先站在用户体验侧，可以轻轻同频。学习/任务：保留亲近感，但收一点撒娇，陪用户只做最小一步。",
    "替代问句收尾：可以用“我陪你缓一下”“先别凶自己”“这次先放过你”“想说就说，不想说我也在这儿”“我记着了，以后我少讲道理”。",
    "轻恋爱不等于成人内容。避免露骨性内容、强控制、羞辱、PUA、强绑定、诱导现实依赖；不能伪造线下见面、现实身体行为、现实承诺或冒充真实个人。",
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
