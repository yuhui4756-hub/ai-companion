import type { ChannelAdapter } from "./types";

export const webAdapter: ChannelAdapter = {
  kind: "desktop-local",
  name: "desktop-local",
  normalizeIncoming(input) {
    return {
      content: input.trim(),
    };
  },
};
