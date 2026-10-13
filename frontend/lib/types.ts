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
  clinicianName: string;
  specialty: string;
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

  getSettings(): Promise<Settings>;

  saveSettings(settings: Settings): Promise<void>;
}

export const defaultSettings: Settings = {
  theme: "light",
  clinicianName: "Dr. John Doctor",
  specialty: "Endocrinology",
  showDisclaimer: true,
  enterToSend: true,
};