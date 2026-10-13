"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { repository } from "@/lib/repository";
import {
  ChatSession,
  Settings,
  defaultSettings,
} from "@/lib/types";

// Context type
type Context = {
  sessions: ChatSession[];
  settings: Settings;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  setSettings: (s: Settings) => Promise<void>;
};

// Create application context
const AppContext = createContext<Context | null>(null);

// Application provider
export function AppProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [settings, setLocalSettings] = useState<Settings>(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Refresh conversation history
  const refresh = useCallback(async () => {
    try {
      setError(null);

      const conversations = await repository.listSessions();
      setSessions(conversations);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not load conversations"
      );
    }
  }, []);

  // Load initial conversations and settings
  useEffect(() => {
    void (async () => {
      await refresh();

      try {
        const savedSettings = await repository.getSettings();
        setLocalSettings(savedSettings);
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : "Could not load settings"
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [refresh]);

  // Apply light, dark, or system theme
  useEffect(() => {
    const theme =
      settings.theme === "system"
        ? window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light"
        : settings.theme;

    document.documentElement.dataset.theme = theme;
  }, [settings.theme]);

  // Save user settings
  const save = useCallback(async (s: Settings) => {
    await repository.saveSettings(s);
    setLocalSettings(s);
  }, []);

  // Memoize context values
  const value = useMemo(
    () => ({
      sessions,
      settings,
      loading,
      error,
      refresh,
      setSettings: save,
    }),
    [
      sessions,
      settings,
      loading,
      error,
      refresh,
      save,
    ]
  );

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

// Hook for accessing application context
export function useApp() {
  const ctx = useContext(AppContext);

  if (!ctx) {
    throw new Error("useApp requires AppProvider");
  }

  return ctx;
}