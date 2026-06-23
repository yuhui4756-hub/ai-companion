import type { ChatMessage, CompanionProfile, ModelProviderConfig, UserMemory } from "../types";
import { selectRelevantMemories } from "../memory/memory";
import { requestChatCompletion } from "../model-provider/openai";
import { buildChatMessages } from "./prompt";

export async function sendCompanionMessage(params: {
  config: ModelProviderConfig;
  companion: CompanionProfile;
  memories: UserMemory[];
  history: ChatMessage[];
  userInput: string;
}): Promise<string> {
  const relevantMemories = selectRelevantMemories(params.memories, params.userInput);
  const messages = buildChatMessages(params.companion, relevantMemories, params.history, params.userInput);
  return requestChatCompletion(params.config, messages);
}
