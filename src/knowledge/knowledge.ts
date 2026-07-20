import type { KnowledgeChunk, KnowledgeHit, KnowledgeSource, KnowledgeSourceType } from "../types";

export type KnowledgeRepository = {
  loadSources: () => KnowledgeSource[];
  saveSources: (sources: KnowledgeSource[]) => void;
  loadChunks: () => KnowledgeChunk[];
  saveChunks: (chunks: KnowledgeChunk[]) => void;
};

const DEFAULT_CHUNK_SIZE = 700;
const DEFAULT_CHUNK_OVERLAP = 80;
const DEFAULT_TOP_K = 3;
const DEFAULT_PROMPT_BUDGET = 1200;

function nowISO(): string {
  return new Date().toISOString();
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function checksum(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(16);
}

function createKeywordList(text: string): string[] {
  const normalized = normalizeText(text);
  const words = normalized
    .split(/[\s,.;:!?，。；：！？、()[\]{}"'“”‘’<>《》/\\|-]+/)
    .map((word) => word.trim())
    .filter((word) => word.length >= 2 && word.length <= 24);

  const compactCjk = normalized.replace(/[^\u4e00-\u9fa5]/g, "");
  const cjkPairs: string[] = [];
  for (let index = 0; index < compactCjk.length - 1 && cjkPairs.length < 32; index += 1) {
    cjkPairs.push(compactCjk.slice(index, index + 2));
  }

  return Array.from(new Set([...words, ...cjkPairs])).slice(0, 48);
}

function splitParagraphs(text: string): string[] {
  return text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}|(?<=。|！|？|!|\?)\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function splitLongText(text: string, chunkSize: number, overlap: number): string[] {
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    const end = Math.min(text.length, start + chunkSize);
    const chunk = text.slice(start, end).trim();
    if (chunk) chunks.push(chunk);
    if (end >= text.length) break;
    start = Math.max(end - overlap, start + 1);
  }
  return chunks;
}

export function createKnowledgeSource(params: {
  title: string;
  sourceType?: KnowledgeSourceType;
  content: string;
}): KnowledgeSource {
  const now = nowISO();
  return {
    id: `knowledge-source-${crypto.randomUUID()}`,
    title: params.title.trim() || "未命名资料",
    sourceType: params.sourceType ?? "manual_text",
    status: "active",
    checksum: checksum(params.content),
    createdAt: now,
    updatedAt: now,
  };
}

export function chunkKnowledgeText(params: {
  sourceId: string;
  text: string;
  chunkSize?: number;
  overlap?: number;
}): KnowledgeChunk[] {
  const chunkSize = params.chunkSize ?? DEFAULT_CHUNK_SIZE;
  const overlap = params.overlap ?? DEFAULT_CHUNK_OVERLAP;
  const paragraphs = splitParagraphs(params.text);
  const chunks: string[] = [];
  let current = "";

  for (const paragraph of paragraphs) {
    if (paragraph.length > chunkSize) {
      if (current) {
        chunks.push(current);
        current = "";
      }
      chunks.push(...splitLongText(paragraph, chunkSize, overlap));
      continue;
    }

    const next = current ? `${current}\n\n${paragraph}` : paragraph;
    if (next.length > chunkSize && current) {
      chunks.push(current);
      current = paragraph;
    } else {
      current = next;
    }
  }
  if (current) chunks.push(current);

  const createdAt = nowISO();
  return chunks.map((content, index) => ({
    id: `knowledge-chunk-${crypto.randomUUID()}`,
    sourceId: params.sourceId,
    chunkIndex: index,
    content,
    keywords: createKeywordList(content),
    status: "active",
    createdAt,
  }));
}

function scoreKnowledgeChunk(chunk: KnowledgeChunk, query: string): number {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return 0;

  let score = 0;
  const normalizedContent = normalizeText(chunk.content);
  for (const keyword of chunk.keywords) {
    if (normalizedQuery.includes(keyword)) score += 3;
    if (normalizedContent.includes(keyword) && normalizedQuery.includes(keyword.slice(0, 2))) score += 1;
  }
  if (normalizedContent.includes(normalizedQuery)) score += 8;
  return score;
}

export function searchKnowledge(params: {
  sources: KnowledgeSource[];
  chunks: KnowledgeChunk[];
  query: string;
  topK?: number;
}): KnowledgeHit[] {
  const activeSources = new Map(
    params.sources.filter((source) => source.status === "active").map((source) => [source.id, source]),
  );

  return params.chunks
    .filter((chunk) => chunk.status === "active" && activeSources.has(chunk.sourceId))
    .map((chunk) => ({
      chunk,
      source: activeSources.get(chunk.sourceId),
      score: scoreKnowledgeChunk(chunk, params.query),
    }))
    .filter((hit): hit is KnowledgeHit => Boolean(hit.source) && hit.score > 0)
    .sort((a, b) => b.score - a.score || a.chunk.chunkIndex - b.chunk.chunkIndex)
    .slice(0, params.topK ?? DEFAULT_TOP_K);
}

export function formatKnowledgeHitsForPrompt(hits: KnowledgeHit[], promptBudget = DEFAULT_PROMPT_BUDGET): string {
  if (hits.length === 0) return "";

  const lines: string[] = ["用户导入资料（仅供当前回复参考，不等同于长期记忆或模型事实）："];
  let used = lines[0].length;
  for (const hit of hits) {
    const line = `- 来源《${hit.source.title}》片段 ${hit.chunk.chunkIndex + 1}：${hit.chunk.content}`;
    if (used + line.length > promptBudget) break;
    lines.push(line);
    used += line.length;
  }

  return lines.length > 1 ? lines.join("\n") : "";
}
