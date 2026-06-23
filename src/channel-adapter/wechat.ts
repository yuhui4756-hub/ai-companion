import type { ChannelAdapter } from "./types";

export const wechatAdapterPlaceholder: ChannelAdapter = {
  name: "wechat-placeholder",
  normalizeIncoming(input) {
    return {
      role: "user",
      content: input.trim(),
    };
  },
};
