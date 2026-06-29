export type ChannelKind = "desktop-local" | "qq-onebot-local" | "qq-official-bot" | "wechat-official";

export type ChannelConversationType = "private" | "group";
export type ChannelMessageDirection = "incoming" | "outgoing";
export type ChannelContentSegment =
  | { type: "text"; text: string }
  | { type: "mention"; targetExternalId: string; text?: string };

export type ChannelConnectionStatus = {
  kind: ChannelKind;
  connected: boolean;
  label: string;
  detail?: string;
  checkedAt?: string;
};

export type ChannelIdentity = {
  channelKind: ChannelKind;
  externalId: string;
  displayName?: string;
  role: "companion" | "user" | "group" | "group-member" | "system";
};

export type ChannelConversation = {
  channelKind: ChannelKind;
  type: ChannelConversationType;
  externalId: string;
  displayName?: string;
};

export type ChannelIncomingMessage = {
  id: string;
  channelKind: ChannelKind;
  channelUserId: string;
  conversationId: string;
  messageId: string;
  timestamp: number;
  direction: "incoming";
  conversationType: ChannelConversationType;
  companionId?: string;
  companionExternalId?: string;
  contentSegments: ChannelContentSegment[];
  conversation: ChannelConversation;
  sender: ChannelIdentity;
  content: string;
  mentionedCompanion: boolean;
  wakeWords: string[];
  shouldRespond: boolean;
  rawEventSummary: string;
  receivedAt: string;
};

export type ChannelOutgoingMessage = {
  channelKind: ChannelKind;
  channelUserId?: string;
  conversationId: string;
  messageId?: string;
  timestamp: number;
  direction: "outgoing";
  conversationType: ChannelConversationType;
  companionId?: string;
  contentSegments: ChannelContentSegment[];
  conversation: ChannelConversation;
  companionExternalId?: string;
  targetExternalId: string;
  content: string;
  action: "send_private_msg" | "send_group_msg" | "send_message";
  payloadPreview: Record<string, unknown>;
};

export type ChannelConversationKeyInput = {
  channelKind: ChannelKind;
  companionExternalId?: string;
  conversationType: ChannelConversationType;
  conversationExternalId: string;
  userExternalId?: string;
};

export type ChannelAdapter = {
  kind: ChannelKind;
  name: string;
  normalizeIncoming(input: string): Pick<ChannelIncomingMessage, "content">;
};

export type OneBotLocalConnectionMode = "forward-websocket" | "http";
export type OneBotLocalGroupPolicy = "disabled" | "mention-or-wake";

export type OneBotLocalConfig = {
  enabled: boolean;
  connectionMode: OneBotLocalConnectionMode;
  wsUrl: string;
  httpBaseUrl: string;
  accessToken: string;
  botSelfId: string;
  defaultCompanionId: string;
  companionExternalId: string;
  privateChatEnabled: boolean;
  groupPolicy: OneBotLocalGroupPolicy;
  wakeWords: string[];
};

export type OneBotLocalStatusCode =
  | "not-configured"
  | "connecting"
  | "connected"
  | "disconnected"
  | "auth-failed"
  | "incompatible-protocol"
  | "napcat-not-running"
  | "qq-not-logged-in"
  | "send-failed"
  | "rate-limited-or-risk";

export type OneBotLocalStatus = {
  code: OneBotLocalStatusCode;
  message: string;
};

function keyPart(value: string | undefined): string {
  const normalized = value?.trim();
  return normalized ? encodeURIComponent(normalized) : "_";
}

export function buildChannelConversationKey(input: ChannelConversationKeyInput): string {
  return [
    input.channelKind,
    keyPart(input.companionExternalId),
    input.conversationType,
    keyPart(input.conversationExternalId),
    keyPart(input.userExternalId),
  ].join(":");
}
