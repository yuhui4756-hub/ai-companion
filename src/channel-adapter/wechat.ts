import type { ChannelAdapter } from "./types";

export const wechatAdapterPlaceholder: ChannelAdapter = {
  kind: "wechat-official",
  name: "wechat-placeholder",
  normalizeIncoming(input) {
    return {
      content: input.trim(),
    };
  },
};
