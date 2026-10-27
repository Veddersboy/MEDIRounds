import {
  ChatRepository,
  ChatSession,
  Message,
  Settings,
  defaultSettings,
} from "./types";

const SESSIONS_KEY = "rounds.demo.sessions.v1";
const SETTINGS_KEY = "rounds.demo.settings.v1";

// Generate unique IDs
const uid = () =>
  globalThis.crypto?.randomUUID?.() ??
  `${Date.now()}-${Math.random().toString(36).slice(2)}`;

// Current ISO timestamp
const now = () => new Date().toISOString();

// Sample Conversations
const sample: ChatSession[] = [
  {
    id: "sample-a1c",
    title: "HbA1c treatment options",
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    updatedAt: new Date(Date.now() - 3600000).toISOString(),
    messages: [
      {
        id: "m1",
        role: "user",
        content:
          "For adults with type 2 diabetes, what factors guide therapy after metformin?",
        createdAt: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "Treatment selection depends on HbA1c, comorbid ASCVD, heart failure, chronic kidney disease, weight goals, hypoglycemia risk, cost, and preferences. Consider contemporary clinical guidelines and individual patient factors before choosing an agent. This is an illustrative response, not live clinical evidence.",
        createdAt: new Date(Date.now() - 3500000).toISOString(),
      },
    ],
  },
  {
    id: "sample-cgm",
    title: "CGM and glucose patterns",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    messages: [
      {
        id: "m3",
        role: "user",
        content:
          "What patterns are useful to review in a continuous glucose monitoring report?",
        createdAt: new Date(Date.now() - 86400000).toISOString(),
      },
    ],
  },
];

// ============================================================
// Local Storage Helpers
// ============================================================

// Retrieve conversations from localStorage
function readSessions(): ChatSession[] {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = localStorage.getItem(SESSIONS_KEY);

  // Initialize mock data if no conversations exist
  if (!raw) {
    localStorage.setItem(
      SESSIONS_KEY,
      JSON.stringify(sample)
    );

    return sample;
  }

  try {
    return JSON.parse(raw) as ChatSession[];
  } catch {
    return [];
  }
}

// Save conversations to localStorage
function writeSessions(sessions: ChatSession[]) {
  localStorage.setItem(
    SESSIONS_KEY,
    JSON.stringify(sessions)
  );
}

// Simulate network latency
const wait = () =>
  new Promise<void>((resolve) => setTimeout(resolve, 250));

// Mock Assistant Response
const demoResponse =
  "This is a frontend demonstration. No clinical literature retrieval or AI model is connected yet. Once FastAPI is configured, this message will be replaced by a response from the diabetes-focused research assistant. Verify all clinical decisions against current guidelines and your professional judgment.";

// Mock Repository

export const mockRepository: ChatRepository = {
  // Retrieve all non-archived conversations
  async listSessions() {
    await wait();

    return readSessions()
      .filter((session) => !session.archived)
      .sort((a, b) =>
        b.updatedAt.localeCompare(a.updatedAt)
      );
  },

  // Retrieve a specific conversation
  async getSession(id) {
    return (
      readSessions().find((session) => session.id === id) ??
      null
    );
  },

  // Create a new conversation
  async createSession() {
    const session: ChatSession = {
      id: uid(),
      title: "New conversation",
      createdAt: now(),
      updatedAt: now(),
      messages: [],
    };

    writeSessions([
      session,
      ...readSessions(),
    ]);

    return session;
  },

  // Rename an existing conversation
  async renameSession(id, title) {
    const sessions = readSessions().map((session) =>
      session.id === id
        ? {
            ...session,
            title: title.trim() || session.title,
            updatedAt: now(),
          }
        : session
    );

    writeSessions(sessions);
  },

  // Delete an existing conversation
  async deleteSession(id) {
    const sessions = readSessions().filter(
      (session) => session.id !== id
    );

    writeSessions(sessions);
  },

  // Send a message and simulate an assistant response
  async sendMessage(id, content) {
    const sessions = readSessions();

    const chat = sessions.find(
      (session) => session.id === id
    );

    if (!chat) {
      throw new Error("Conversation not found");
    }

    // Create user message
    const user: Message = {
      id: uid(),
      role: "user",
      content,
      createdAt: now(),
    };

    chat.messages.push(user);

    // Automatically title new conversations
    if (chat.title === "New conversation") {
      chat.title =
        content.trim().slice(0, 52) +
        (content.trim().length > 52 ? "…" : "");
    }

    chat.updatedAt = now();

    // Persist user message
    writeSessions(sessions);

    await wait();

    // Generate mock assistant response
    const assistant: Message = {
      id: uid(),
      role: "assistant",
      content: demoResponse,
      createdAt: now(),
    };

    chat.messages.push(assistant);
    chat.updatedAt = now();

    // Persist assistant response
    writeSessions(sessions);

    return assistant;
  },

  // Retrieve user settings
  async getSettings() {
    try {
      return {
        ...defaultSettings,
        ...JSON.parse(
          localStorage.getItem(SETTINGS_KEY) || "{}"
        ),
      } as Settings;
    } catch {
      return defaultSettings;
    }
  },

  // Save user settings
  async saveSettings(settings) {
    localStorage.setItem(
      SETTINGS_KEY,
      JSON.stringify(settings)
    );
  },
};

// FastAPI Configuration

const base =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

// HTTP Request Helper

// Generic request function for FastAPI endpoints
async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,

    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },

    credentials: "include",
    cache: "no-store",
  });

  // Handle unsuccessful HTTP responses
  if (!response.ok) {
    throw new Error(
      `API ${response.status}: ${await response.text()}`
    );
  }

  // Handle successful responses without a body
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// FastAPI Repository

export const apiRepository: ChatRepository = {
  // GET /api/v1/chats
  // Retrieve all conversations
  listSessions: () =>
    request("/api/v1/chats"),

  // GET /api/v1/chats/:id
  // Retrieve a specific conversation
  getSession: (id) =>
    request(
      `/api/v1/chats/${encodeURIComponent(id)}`
    ),

  // POST /api/v1/chats
  // Create a conversation
  createSession: () =>
    request("/api/v1/chats", {
      method: "POST",
      body: "{}",
    }),

  // PATCH /api/v1/chats/:id
  // Rename a conversation
  renameSession: (id, title) =>
    request(
      `/api/v1/chats/${encodeURIComponent(id)}`,
      {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }
    ),

  // DELETE /api/v1/chats/:id
  // Delete a conversation
  deleteSession: (id) =>
    request(
      `/api/v1/chats/${encodeURIComponent(id)}`,
      {
        method: "DELETE",
      }
    ),

  // POST /api/v1/chats/:id/messages
  // Send a message to the assistant
  sendMessage: (id, content) =>
    request(
      `/api/v1/chats/${encodeURIComponent(id)}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      }
    ),

  // GET /api/v1/me/settings
  // Retrieve user settings
  getSettings: () =>
    request("/api/v1/me/settings"),

  // PUT /api/v1/me/settings
  // Update user settings
  saveSettings: (settings) =>
    request("/api/v1/me/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
};

// Repository Selection

// Use the FastAPI repository when NEXT_PUBLIC_DATA_MODE="api".
// Otherwise, default to the mock implementation.

export const repository: ChatRepository =
  process.env.NEXT_PUBLIC_DATA_MODE === "api"
    ? apiRepository
    : mockRepository;