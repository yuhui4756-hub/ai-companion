import type { ChatMessage } from "../types";

export type ChannelAdapter = {
  name: string;
  normalizeIncoming(input: string): Omit<ChatMessage, "id" | "createdAt">;
};
