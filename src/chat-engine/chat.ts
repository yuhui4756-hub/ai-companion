import type {
  ChatMessage,
  CompanionProfile,
  KnowledgeChunk,
  KnowledgeSource,
  ModelProviderConfig,
  StyleSummary,
  UserMemory,
} from "../types";
import { formatKnowledgeHitsForPrompt, searchKnowledge } from "../knowledge/knowledge";
import { selectRelevantMemories } from "../memory/memory";
import { requestChatCompletion } from "../model-provider/modelClient";
import { buildChatMessages } from "./prompt";

export async function sendCompanionMessage(params: {
  config: ModelProviderConfig;
  companion: CompanionProfile;
  styleSummary?: StyleSummary;
  memories: UserMemory[];
  knowledgeContext?: string;
  knowledgeSources?: KnowledgeSource[];
  knowledgeChunks?: KnowledgeChunk[];
  history: ChatMessage[];
  userInput: string;
}): Promise<string> {
  const relevantMemories = selectRelevantMemories(params.memories, params.userInput, params.companion.id);
  const knowledgeContext =
    params.knowledgeContext ??
    formatKnowledgeHitsForPrompt(
      searchKnowledge({
        sources: params.knowledgeSources ?? [],
        chunks: params.knowledgeChunks ?? [],
        query: params.userInput,
        topK: 3,
      }),
    );
  const messages = buildChatMessages(
    params.companion,
    params.styleSummary,
    relevantMemories,
    params.history,
    params.userInput,
    knowledgeContext,
  );
  return requestChatCompletion(params.config, messages);
}
