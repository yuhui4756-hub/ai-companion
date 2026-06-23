import type { ChatMessage, CompanionProfile, ModelProviderConfig, StyleSummary, UserMemory } from "../types";
import { selectRelevantMemories } from "../memory/memory";
import { requestChatCompletion } from "../model-provider/openai";
import { buildChatMessages } from "./prompt";

export async function sendCompanionMessage(params: {
  config: ModelProviderConfig;
  companion: CompanionProfile;
  styleSummary?: StyleSummary;
  memories: UserMemory[];
  history: ChatMessage[];
  userInput: string;
}): Promise<string> {
  const relevantMemories = selectRelevantMemories(params.memories, params.userInput, params.companion.id);
  const messages = buildChatMessages(
    params.companion,
    params.styleSummary,
    relevantMemories,
    params.history,
    params.userInput,
  );
  return requestChatCompletion(params.config, messages);
}
