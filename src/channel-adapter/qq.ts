import type { ChannelAdapter } from "./types";

export const qqAdapterPlaceholder: ChannelAdapter = {
  name: "qq-placeholder",
  normalizeIncoming(input) {
    return {
      role: "user",
      content: input.trim(),
    };
  },
};
