import { getDesktopBridge } from "../desktop/desktopBridge";
import type { ModelProviderConfig, OpenAIChatMessage } from "../types";
import {
  ModelProviderError,
  requestDirectChatCompletion,
  type ModelErrorCode,
} from "./openai";

function isModelErrorCode(value: unknown): value is ModelErrorCode {
  return (
    value === "missing-config" ||
    value === "auth" ||
    value === "quota" ||
    value === "network" ||
    value === "model" ||
    value === "invalid-response"
  );
}

export async function requestChatCompletionViaAvailableClient(
  config: ModelProviderConfig,
  messages: OpenAIChatMessage[],
): Promise<string> {
  const desktopModelProvider = getDesktopBridge()?.modelProvider;
  if (!desktopModelProvider) {
    return requestDirectChatCompletion(config, messages);
  }

  const response = await desktopModelProvider.requestChatCompletion(config, messages);
  if (response.ok) {
    return response.content;
  }

  const code = isModelErrorCode(response.error.code) ? response.error.code : "model";
  throw new ModelProviderError(code, response.error.message);
}

export const requestChatCompletion = requestChatCompletionViaAvailableClient;
