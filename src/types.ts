export type CompanionType = "friend" | "romantic" | "rational" | "healing" | "roleplay";

export type MemoryCategory =
  | "basic"
  | "preference"
  | "event"
  | "emotion"
  | "relationship"
  | "boundary";

export type MemoryImportance = 1 | 2 | 3;

export type CompanionProfile = {
  id: CompanionType;
  name: string;
  title: string;
  relationshipType: string;
  tone: string;
  emotionalStyle: string;
  problemSolvingStyle: string;
  roleplayScope: string;
  boundaries: string[];
  prompt: string;
};

export type UserMemory = {
  id: string;
  category: MemoryCategory;
  content: string;
  importance: MemoryImportance;
  createdAt: string;
  updatedAt: string;
};

export type ModelProviderConfig = {
  providerName: string;
  baseURL: string;
  apiKey: string;
  model: string;
};

export type ChatRole = "system" | "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: Exclude<ChatRole, "system">;
  content: string;
  createdAt: string;
};

export type OpenAIChatMessage = {
  role: ChatRole;
  content: string;
};

export type AppView = "chat" | "settings" | "memory";
