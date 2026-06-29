import type { ChannelAdapter } from "./types";

export const qqAdapterPlaceholder: ChannelAdapter = {
  kind: "qq-official-bot",
  name: "qq-placeholder",
  normalizeIncoming(input) {
    return {
      content: input.trim(),
    };
  },
};
