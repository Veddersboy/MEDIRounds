export type Role = "user" | "assistant";

export interface Citation {
  title: string;
  url?: string;
  detail?: string;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  citations?: Citation[];
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
  archived?: boolean;
}

export interface Settings {
  theme: "light" | "dark" | "system";
  specialty: string;
  experience: string;
  showDisclaimer: boolean;
  enterToSend: boolean;
}

export interface TimelineItem {
  id: string;
  sessionId: string;
  kind: "chat";
  title: string;
  description: string;
  at: string;
}

export interface ChatRepository {
  listSessions(): Promise<ChatSession[]>;

  getSession(id: string): Promise<ChatSession | null>;

  createSession(): Promise<ChatSession>;

  renameSession(id: string, title: string): Promise<void>;

  deleteSession(id: string): Promise<void>;

  sendMessage(id: string, content: string): Promise<Message>;

  getSuggestions(): Promise<string[]>;

  getSettings(): Promise<Settings>;

  saveSettings(settings: Settings): Promise<void>;
}

export const defaultSuggestions = [
  "Compare major classes of type 2 diabetes medications",
  "What should be considered when interpreting HbA1c?",
  "Summarize approaches to managing diabetes with CKD",
];

export const defaultSettings: Settings = {
  theme: "light",
  specialty: "Endocrinology",
  experience: "",
  showDisclaimer: true,
  enterToSend: true,
};