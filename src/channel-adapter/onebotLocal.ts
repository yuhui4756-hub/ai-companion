import type {
  ChannelConversationType,
  ChannelIncomingMessage,
  ChannelOutgoingMessage,
  OneBotLocalConfig,
  OneBotLocalStatus,
  OneBotLocalStatusCode,
} from "./types";
import { buildChannelConversationKey } from "./types";

export type OneBotMockEvent = {
  post_type: "message";
  message_type: "private" | "group";
  sub_type?: string;
  message_id: number | string;
  time: number;
  self_id: number | string;
  user_id: number | string;
  group_id?: number | string;
  message: string | Array<{ type: string; data?: Record<string, unknown> }>;
  raw_message?: string;
  sender?: {
    nickname?: string;
    card?: string;
    user_id?: number | string;
  };
};

export type OneBotMockScenario = "private" | "group-mention" | "group-no-mention" | "self-echo";

export type OneBotNormalizeResult = {
  incoming: ChannelIncomingMessage;
  conversationKey: string;
  reason: string;
  outgoingPreview?: ChannelOutgoingMessage;
};

export const defaultOneBotLocalConfig: OneBotLocalConfig = {
  enabled: false,
  connectionMode: "forward-websocket",
  wsUrl: "ws://127.0.0.1:3001",
  httpBaseUrl: "http://127.0.0.1:3000",
  accessToken: "",
  botSelfId: "",
  defaultCompanionId: "",
  companionExternalId: "",
  privateChatEnabled: true,
  groupPolicy: "disabled",
  wakeWords: ["所依", "小依"],
};

const statusMessages: Record<OneBotLocalStatusCode, string> = {
  "not-configured": "还没有启用或填写本机 OneBot 连接信息。",
  connecting: "正在尝试连接本机 OneBot 服务。",
  connected: "已连接本机 OneBot 服务。",
  disconnected: "本机 OneBot 连接已断开。",
  "auth-failed": "连接鉴权失败，请确认本机 OneBot access token 是否一致。",
  "incompatible-protocol": "当前服务返回不像 OneBot 协议，请确认连接地址和协议类型。",
  "napcat-not-running": "没有连上本机 OneBot/NapCat 服务，请先在本机启动它。",
  "qq-not-logged-in": "OneBot 服务可达，但 QQ 侧似乎还没有登录完成。",
  "send-failed": "消息发送失败，请检查本机 OneBot 服务和 QQ 状态。",
  "rate-limited-or-risk": "发送可能被限频或触发风控，建议降低频率或使用专门 QQ 号测试。",
};

function id(value: number | string | undefined): string {
  return value === undefined ? "" : String(value);
}

function summarizeEvent(event: OneBotMockEvent): string {
  const type = event.message_type === "group" ? `group:${id(event.group_id)}` : "private";
  return `OneBot message ${type} from user:${id(event.user_id)} message:${id(event.message_id)}`;
}

export function maskOneBotToken(token: string): string {
  const trimmed = token.trim();
  if (!trimmed) return "未填写";
  if (trimmed.length <= 6) return "***";
  return `${trimmed.slice(0, 2)}***${trimmed.slice(-2)}`;
}

export function sanitizeOneBotEndpoint(value: string): string {
  try {
    const url = new URL(value);
    ["access_token", "token", "Authorization", "authorization"].forEach((key) => {
      if (url.searchParams.has(key)) {
        url.searchParams.set(key, "***");
      }
    });
    return url.toString();
  } catch {
    return value.replace(/(token|access_token|authorization)=([^&\s]+)/gi, "$1=***");
  }
}

export function getOneBotStatusMessage(code: OneBotLocalStatusCode): OneBotLocalStatus {
  return {
    code,
    message: statusMessages[code],
  };
}

function parseOneBotMessage(event: OneBotMockEvent): {
  content: string;
  mentionedCompanion: boolean;
} {
  if (typeof event.message === "string") {
    const raw = event.raw_message ?? event.message;
    return {
      content: raw.replace(/\[CQ:at,qq=\d+\]/g, "").trim(),
      mentionedCompanion: event.message.includes(`[CQ:at,qq=${id(event.self_id)}]`),
    };
  }

  let mentionedCompanion = false;
  const text = event.message
    .map((segment) => {
      if (segment.type === "at" && String(segment.data?.qq ?? "") === id(event.self_id)) {
        mentionedCompanion = true;
        return "";
      }
      if (segment.type === "text") {
        return String(segment.data?.text ?? "");
      }
      return "";
    })
    .join("")
    .trim();

  return {
    content: text,
    mentionedCompanion,
  };
}

function hasWakeWord(content: string, wakeWords: string[]): boolean {
  return wakeWords.some((word) => {
    const trimmed = word.trim();
    return trimmed.length > 0 && content.includes(trimmed);
  });
}

function shouldRespondToEvent(params: {
  event: OneBotMockEvent;
  config: OneBotLocalConfig;
  content: string;
  mentionedCompanion: boolean;
  processedMessageIds?: ReadonlySet<string>;
}): { shouldRespond: boolean; reason: string } {
  const { event, config, content, mentionedCompanion, processedMessageIds } = params;
  if (processedMessageIds?.has(id(event.message_id))) {
    return { shouldRespond: false, reason: "这条 message_id 已处理过，跳过去重防循环。" };
  }
  if (id(event.user_id) === id(event.self_id) || event.sub_type === "echo") {
    return { shouldRespond: false, reason: "自我消息/echo，防止机器人自循环。" };
  }
  if (event.message_type === "private") {
    return config.privateChatEnabled
      ? { shouldRespond: true, reason: "私聊消息，当前配置允许触发回复。" }
      : { shouldRespond: false, reason: "私聊响应已关闭。" };
  }
  if (config.groupPolicy === "disabled") {
    return { shouldRespond: false, reason: "群聊响应默认关闭。" };
  }
  if (mentionedCompanion || hasWakeWord(content, config.wakeWords)) {
    return { shouldRespond: true, reason: "群聊中检测到 @ 或唤醒词。" };
  }
  return { shouldRespond: false, reason: "群聊未 @ 且无唤醒词，不触发模型回复。" };
}

export function normalizeOneBotMockEvent(
  event: OneBotMockEvent,
  config: OneBotLocalConfig,
  processedMessageIds?: ReadonlySet<string>,
): OneBotNormalizeResult {
  const conversationType: ChannelConversationType = event.message_type === "group" ? "group" : "private";
  const conversationExternalId = conversationType === "group" ? id(event.group_id) : id(event.user_id);
  const { content, mentionedCompanion } = parseOneBotMessage(event);
  const decision = shouldRespondToEvent({ event, config, content, mentionedCompanion, processedMessageIds });
  const incoming: ChannelIncomingMessage = {
    id: `onebot-${id(event.message_id)}`,
    channelKind: "qq-onebot-local",
    channelUserId: id(event.user_id),
    conversationId: conversationExternalId,
    messageId: id(event.message_id),
    timestamp: event.time,
    direction: "incoming",
    conversationType,
    companionId: config.defaultCompanionId || undefined,
    companionExternalId: config.companionExternalId || id(event.self_id),
    contentSegments: [{ type: "text", text: content }],
    conversation: {
      channelKind: "qq-onebot-local",
      type: conversationType,
      externalId: conversationExternalId,
      displayName: conversationType === "group" ? `群 ${conversationExternalId}` : event.sender?.nickname,
    },
    sender: {
      channelKind: "qq-onebot-local",
      externalId: id(event.user_id),
      displayName: event.sender?.card || event.sender?.nickname,
      role: conversationType === "group" ? "group-member" : "user",
    },
    content,
    mentionedCompanion,
    wakeWords: config.wakeWords.filter((word) => word.trim() && content.includes(word.trim())),
    shouldRespond: decision.shouldRespond,
    rawEventSummary: summarizeEvent(event),
    receivedAt: new Date(event.time * 1000).toISOString(),
  };
  const conversationKey = buildChannelConversationKey({
    channelKind: incoming.channelKind,
    companionExternalId: incoming.companionExternalId,
    conversationType,
    conversationExternalId,
    userExternalId: incoming.channelUserId,
  });

  return {
    incoming,
    conversationKey,
    reason: decision.reason,
    outgoingPreview: decision.shouldRespond ? buildOneBotOutgoingPreview(incoming, "这里会放模型回复预览。") : undefined,
  };
}

export function buildOneBotOutgoingPreview(
  incoming: ChannelIncomingMessage,
  content: string,
): ChannelOutgoingMessage {
  const isGroup = incoming.conversation.type === "group";
  const action = isGroup ? "send_group_msg" : "send_private_msg";
  const targetExternalId = isGroup ? incoming.conversation.externalId : incoming.sender.externalId;
  const payloadPreview = isGroup
    ? { action, params: { group_id: targetExternalId, message: content } }
    : { action, params: { user_id: targetExternalId, message: content } };

  return {
    channelKind: "qq-onebot-local",
    channelUserId: incoming.channelUserId,
    conversationId: incoming.conversationId,
    timestamp: Math.floor(Date.now() / 1000),
    direction: "outgoing",
    conversationType: incoming.conversationType,
    companionId: incoming.companionId,
    contentSegments: [{ type: "text", text: content }],
    conversation: incoming.conversation,
    companionExternalId: incoming.companionExternalId,
    targetExternalId,
    content,
    action,
    payloadPreview,
  };
}

export function createOneBotMockEvent(scenario: OneBotMockScenario, config: OneBotLocalConfig): OneBotMockEvent {
  const botSelfId = config.botSelfId.trim() || "10001";
  const now = Math.floor(Date.now() / 1000);
  if (scenario === "group-mention") {
    return {
      post_type: "message",
      message_type: "group",
      message_id: "mock-group-at-1",
      time: now,
      self_id: botSelfId,
      user_id: "20002",
      group_id: "30003",
      message: [
        { type: "at", data: { qq: botSelfId } },
        { type: "text", data: { text: " 今天有点累，陪我说两句" } },
      ],
      raw_message: `[CQ:at,qq=${botSelfId}] 今天有点累，陪我说两句`,
      sender: { nickname: "群成员A", card: "群成员A" },
    };
  }
  if (scenario === "group-no-mention") {
    return {
      post_type: "message",
      message_type: "group",
      message_id: "mock-group-no-at-1",
      time: now,
      self_id: botSelfId,
      user_id: "20003",
      group_id: "30003",
      message: "大家今天几点开黑？",
      raw_message: "大家今天几点开黑？",
      sender: { nickname: "群成员B", card: "群成员B" },
    };
  }
  if (scenario === "self-echo") {
    return {
      post_type: "message",
      message_type: "private",
      sub_type: "echo",
      message_id: "mock-self-echo-1",
      time: now,
      self_id: botSelfId,
      user_id: botSelfId,
      message: "这是机器人自己发出的消息回显",
      raw_message: "这是机器人自己发出的消息回显",
      sender: { nickname: "所依" },
    };
  }
  return {
    post_type: "message",
    message_type: "private",
    message_id: "mock-private-1",
    time: now,
    self_id: botSelfId,
    user_id: "20001",
    message: "今天有点累，想找你说说话",
    raw_message: "今天有点累，想找你说说话",
    sender: { nickname: "测试用户" },
  };
}
