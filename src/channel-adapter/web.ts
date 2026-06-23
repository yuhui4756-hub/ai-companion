import type { ChannelAdapter } from "./types";

export const webAdapter: ChannelAdapter = {
  name: "web",
  normalizeIncoming(input) {
    return {
      role: "user",
      content: input.trim(),
    };
  },
};
