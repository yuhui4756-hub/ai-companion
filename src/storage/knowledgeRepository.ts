import type { KnowledgeRepository } from "../knowledge/knowledge";
import {
  loadKnowledgeChunks,
  loadKnowledgeSources,
  saveKnowledgeChunks,
  saveKnowledgeSources,
} from "./localStorage";

export const localKnowledgeRepository: KnowledgeRepository = {
  loadSources: loadKnowledgeSources,
  saveSources: saveKnowledgeSources,
  loadChunks: loadKnowledgeChunks,
  saveChunks: saveKnowledgeChunks,
};
