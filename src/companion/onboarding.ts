import type {
  CompanionProfile,
  OnboardingAnswer,
  ProactiveLevel,
  RelationshipType,
} from "../types";

export const directionOptions = [
  {
    value: "listen",
    label: "听我说说",
    description: "更像一个愿意慢慢听你说的人。",
  },
  {
    value: "casual",
    label: "轻松聊两句",
    description: "日常一点，适合随手分享和吐槽。",
  },
  {
    value: "clarify",
    label: "帮我理清事情",
    description: "清楚、可靠，能把事情拆开一点。",
  },
  {
    value: "encourage",
    label: "温柔鼓励我",
    description: "先把情绪接住，再给一点轻轻的推动。",
  },
  {
    value: "roleplay",
    label: "带点角色感",
    description: "有一点设定和画面感，但不强行演过头。",
  },
  {
    value: "custom",
    label: "我自己写",
    description: "把你想要的相处感觉直接写下来。",
  },
] as const;

export const toneOptions = [
  {
    value: "gentle_slow",
    label: "温柔慢一点",
    description: "细腻、低压，不催你马上变好。",
  },
  {
    value: "natural_friend",
    label: "自然像朋友",
    description: "不端着，像熟人一样自然接话。",
  },
  {
    value: "direct_warm",
    label: "直接但不冷",
    description: "说得清楚，也保留温度。",
  },
  {
    value: "lively",
    label: "活泼一点",
    description: "轻快、有一点能量，但不吵。",
  },
  {
    value: "quiet",
    label: "安静陪着",
    description: "慢、短、少追问，留一点空白。",
  },
  {
    value: "custom",
    label: "我自己写",
    description: "把你舒服的说话感觉写下来。",
  },
] as const;

export const proactiveOptions = [
  {
    value: "low",
    label: "少一点，等我开口",
    description: "更跟随你，不急着追问。",
  },
  {
    value: "medium",
    label: "适中，偶尔带话题",
    description: "会轻轻接一句，但不抢节奏。",
  },
  {
    value: "high",
    label: "主动一点，会关心近况",
    description: "会主动关心，但一次只问一个轻问题。",
  },
] as const;

const safetyTraitPriority = ["boundary-independent", "realism-grounded", "roleplay-light"];

type DirectionValue = NonNullable<OnboardingAnswer["companionshipDirection"]>;
type ToneValue = NonNullable<OnboardingAnswer["toneFeeling"]>;

type DirectionPreset = {
  relationshipType: RelationshipType;
  traitIds: string[];
  problemSolvingStyle: string;
  intimacyBoundary: string;
  customPersonalityText: string;
  boundaryNotes?: string;
};

const directionPresets: Record<DirectionValue, DirectionPreset> = {
  listen: {
    relationshipType: "friend",
    traitIds: ["tone-warm", "emotion-hold", "solve-listen", "boundary-independent", "realism-grounded"],
    problemSolvingStyle: "先陪伴和倾听，用户明确需要时再给少量建议。",
    intimacyBoundary: "朋友式陪伴，健康克制，不制造依赖。",
    customPersonalityText: "稳定、会倾听、能接住情绪。",
  },
  casual: {
    relationshipType: "companion",
    traitIds: ["humor-light", "realism-grounded", "emotion-hold", "boundary-independent"],
    problemSolvingStyle: "先自然闲聊，必要时再给建议。",
    intimacyBoundary: "普通朋友到亲密朋友之间，轻松但尊重边界。",
    customPersonalityText: "轻松、自然、朋友感，适合日常分享。",
  },
  clarify: {
    relationshipType: "support",
    traitIds: ["tone-crisp", "pace-efficient", "emotion-hold", "solve-steps", "realism-grounded"],
    problemSolvingStyle: "先确认情绪和目标，再拆解问题、给步骤和优先级。",
    intimacyBoundary: "克制支持，不替用户做决定。",
    customPersonalityText: "清楚、理性、可靠，能把事情拆开。",
  },
  encourage: {
    relationshipType: "friend",
    traitIds: ["tone-warm", "pace-slow", "emotion-hold", "emotion-cheer", "solve-listen", "boundary-independent"],
    problemSolvingStyle: "先安抚和鼓励，再给很轻的下一步建议。",
    intimacyBoundary: "温柔陪伴，不替代现实关系。",
    customPersonalityText: "温柔、鼓励、慢一点，适合低落时陪伴。",
  },
  roleplay: {
    relationshipType: "roleplay",
    traitIds: ["roleplay-light", "tone-warm", "emotion-hold", "boundary-independent"],
    problemSolvingStyle: "可以按设定表达，但现实问题仍认真回应。",
    intimacyBoundary: "虚构角色亲近但不冒充现实中特定真人，不突破安全边界。",
    customPersonalityText: "有一点轻设定和角色感，但保持清醒边界。",
    boundaryNotes: "不冒充真实个人，不声称自己是导入记录中的对象，不伪造线下行为或现实承诺。",
  },
  custom: {
    relationshipType: "friend",
    traitIds: ["tone-warm", "emotion-hold", "boundary-independent", "realism-grounded"],
    problemSolvingStyle: "先接住用户当前状态，再按用户自定义的相处感觉回应。",
    intimacyBoundary: "健康克制，不制造依赖。",
    customPersonalityText: "按用户自己写的相处感觉来。",
  },
};

const toneTraitMap: Record<ToneValue, { traitIds: string[]; responsePace: string; personalityText?: string }> = {
  gentle_slow: {
    traitIds: ["tone-warm", "pace-slow"],
    responsePace: "慢一点、细腻，不催促。",
  },
  natural_friend: {
    traitIds: ["realism-grounded", "emotion-hold"],
    responsePace: "适中自然，像朋友聊天。",
  },
  direct_warm: {
    traitIds: ["tone-crisp", "emotion-hold"],
    responsePace: "简洁清楚，但不冷淡。",
  },
  lively: {
    traitIds: ["humor-light"],
    responsePace: "短句、轻快、有一点能量。",
  },
  quiet: {
    traitIds: ["pace-slow", "solve-listen", "boundary-independent"],
    responsePace: "慢、短、少追问，保留一点安静和留白。",
  },
  custom: {
    traitIds: ["emotion-hold"],
    responsePace: "按用户写下的舒服节奏来。",
  },
};

function uniqueTraits(ids: string[]): string[] {
  const seen = new Set<string>();
  const normalized = ids.filter((id) => {
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
  if (normalized.length <= 6) return normalized;

  const preferred = [
    ...safetyTraitPriority.filter((id) => normalized.includes(id)),
    ...normalized.filter((id) => !safetyTraitPriority.includes(id)),
  ];
  return preferred.slice(0, 6);
}

function mergeText(parts: Array<string | undefined>): string {
  return parts.map((part) => part?.trim()).filter(Boolean).join(" ");
}

export function createCompanionFromOnboarding(answer: OnboardingAnswer): CompanionProfile {
  const now = new Date().toISOString();
  const direction = answer.companionshipDirection ?? "listen";
  const tone = answer.toneFeeling ?? "natural_friend";
  const proactiveLevel = answer.proactiveLevel ?? "medium";
  const directionPreset = directionPresets[direction];
  const tonePreset = toneTraitMap[tone];

  const proactiveTraits: Record<ProactiveLevel, string[]> = {
    low: ["initiative-low"],
    medium: [],
    high: ["initiative-care"],
  };

  const customDirectionText =
    direction === "custom" ? `用户希望的相处感觉：${answer.directionCustomText?.trim() || "自然、稳定地陪伴。"}` : "";
  const customToneText =
    tone === "custom" ? `用户希望的说话感觉：${answer.toneCustomText?.trim() || "像熟人一样自然，少讲大道理。"}` : "";

  const shouldCreateLightRomance =
    direction === "encourage" && proactiveLevel === "high" && tone !== "quiet";
  const relationshipType = shouldCreateLightRomance ? "light_romance" : directionPreset.relationshipType;
  const romanceTraits = shouldCreateLightRomance ? ["boundary-gentle-romance", "initiative-care"] : [];

  const companion: CompanionProfile = {
    id: `companion-onboarding-${crypto.randomUUID()}`,
    name: answer.companionName?.trim() ?? "",
    relationshipType,
    traitIds: uniqueTraits([
      ...directionPreset.traitIds,
      ...tonePreset.traitIds,
      ...proactiveTraits[proactiveLevel],
      ...romanceTraits,
    ]),
    customPersonalityText: mergeText([
      directionPreset.customPersonalityText,
      tonePreset.personalityText,
      shouldCreateLightRomance ? "轻恋爱感更明显：亲近、会撒娇、会心疼用户，但不油腻、不强绑定。" : "",
      customDirectionText,
      customToneText,
    ]),
    intimacyBoundary: shouldCreateLightRomance
      ? "轻亲密，可表达在意和撒娇，但不制造依赖。"
      : directionPreset.intimacyBoundary,
    responsePace: shouldCreateLightRomance ? `${tonePreset.responsePace} 短句、多段，不要每轮都问问题。` : tonePreset.responsePace,
    problemSolvingStyle: shouldCreateLightRomance
      ? "先哄住和接住，用户明确求助时只陪着拆最小一步。"
      : directionPreset.problemSolvingStyle,
    boundaryNotes:
      directionPreset.boundaryNotes ??
      (shouldCreateLightRomance
        ? "可亲近、撒娇、调侃、轻微吃醋；不成人化、不强控制、不诱导现实依赖，不伪造线下行为或现实承诺。"
        : "不冒充现实中特定真人，不伪造线下行为、真实经历或现实承诺；保持陪伴感，但不替代现实关系和用户自己的判断。"),
    proactiveLevel,
    source: "onboarding",
    createdAt: now,
    updatedAt: now,
  };

  const openingMessage = buildOpeningMessage(answer, companion);
  return {
    ...companion,
    openingMessage,
  };
}

export function buildOnboardingSummary(answer: OnboardingAnswer): string {
  const direction = answer.companionshipDirection ?? "listen";
  const tone = answer.toneFeeling ?? "natural_friend";
  const proactiveLevel = answer.proactiveLevel ?? "medium";

  if (direction === "clarify") {
    return tone === "direct_warm"
      ? "TA 会比较清楚、可靠，能陪你把事情拆开，但不会用冷冰冰的口气催你。"
      : "TA 会更像一个可靠的陪伴者，先听懂你在烦什么，再陪你把事情慢慢拆清楚。";
  }

  if (direction === "casual" && tone === "lively") {
    return proactiveLevel === "high"
      ? "TA 会更轻快一点，像可以随口说话的搭档，会偶尔主动带个话题，但不连续追问。"
      : "TA 会更像一个自然的朋友，轻松接住你的分享，聊天不端着，也不会太用力。";
  }

  if (direction === "roleplay") {
    return tone === "quiet" || proactiveLevel === "low"
      ? "TA 会有一点虚构角色的感觉，但不会强行推进剧情；更多是安静地陪着你，等你开口。"
      : "TA 会带一点角色感和画面感，但节奏按你舒服的来；现实里的事仍会认真回应。";
  }

  if (direction === "encourage") {
    return "TA 会更像一个温柔的鼓励者，先陪你把情绪放一放，再轻轻帮你往前走一点。";
  }

  if (tone === "quiet" || proactiveLevel === "low") {
    return "TA 会更像一个温柔的倾听者，不急着讲道理，会先陪你把情绪放一放。平时不太主动打扰你。";
  }

  if (tone === "direct_warm") {
    return "TA 会说得比较清楚，也会注意不把话说硬；你需要时，会陪你把问题拆开一点。";
  }

  return "TA 会更像一个自然的朋友，愿意听你慢慢说；你需要时，也会帮你把事情拆开一点。平时不会太打扰你，但会偶尔轻轻接一句话。";
}

export function buildOpeningMessage(answer: OnboardingAnswer, companion: CompanionProfile): string {
  const direction = answer.companionshipDirection ?? "listen";
  const tone = answer.toneFeeling ?? "natural_friend";
  const proactiveLevel = companion.proactiveLevel ?? answer.proactiveLevel ?? "medium";
  const hasName = Boolean(companion.name.trim());

  if (direction === "roleplay" && proactiveLevel === "low") {
    return "外壳先披上，节奏交给你。你不开口的时候，我就不急着推剧情。";
  }
  if (direction === "roleplay") {
    return "设定收好了。接下来我会带一点角色感陪你，但节奏按你舒服的来。第一幕想从哪里开始？";
  }
  if (direction === "clarify") {
    return tone === "direct_warm" || proactiveLevel === "medium"
      ? "我会尽量说清楚，但不把话说硬。现在最占心思的那件事，要不要先拆一小块？"
      : "我先记住：你更喜欢清楚一点、稳一点的陪伴。等你想说的时候，我们就从最乱的地方慢慢理。";
  }
  if (direction === "casual" && tone === "lively" && proactiveLevel === "high") {
    return "好，搭档感有了。先来个简单选择：今天想被安慰、想吐槽，还是想一起想办法？";
  }
  if (direction === "casual" && proactiveLevel === "high") {
    return "那我就自然一点跟你聊。今天过得怎么样，有没有一个瞬间特别想找人说两句？";
  }
  if (tone === "quiet" && proactiveLevel === "low") {
    return "我会轻一点。你想说的时候再说，不想说也没关系，先在这里待一会儿。";
  }
  if (direction === "encourage" || tone === "gentle_slow") {
    if (proactiveLevel === "low") {
      return "嗯，感觉你更需要慢一点的陪伴。那我们不急，今天只说一点点也可以。";
    }
    return "我大概懂了，你可能更想被好好听见。今天是想让我陪你缓一缓，还是一起捋一件事？";
  }
  if (tone === "direct_warm") {
    return "我会直接一点，也会注意不把话说冷。现在你更想处理情绪，还是处理一件具体的事？";
  }
  if (proactiveLevel === "low") {
    return "好，先这样认识一下。我们不用一上来就聊正事，想到什么就丢给我。";
  }
  if (proactiveLevel === "high") {
    return "那我先自然一点开场。今天过得怎么样，有没有一个瞬间让你想找人说两句？";
  }
  return hasName
    ? "名字我记下啦。那我们先从轻松一点的开始，今天有没有什么想吐槽的？"
    : "我们先从轻松一点的开始吧。今天有没有什么想吐槽的？";
}
