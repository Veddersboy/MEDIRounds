"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { repository } from "@/lib/repository";
import { defaultSuggestions } from "@/lib/types";

// Show the default prompts if suggestions take longer than this
const TIMEOUT_MS = 4000;

export function SuggestedPrompts({
  onSelect,
}: {
  onSelect: (prompt: string) => void;
}) {
  const [prompts, setPrompts] = useState<string[] | null>(null);

  useEffect(() => {
    let settled = false;

    // Only the first result is shown: clicking a prompt sends it right away,
    // so prompts must not change under the user's cursor.
    const show = (suggestions: string[]) => {
      if (settled) return;

      settled = true;
      setPrompts(
        suggestions.length ? suggestions : defaultSuggestions
      );
    };

    const timer = setTimeout(
      () => show(defaultSuggestions),
      TIMEOUT_MS
    );

    repository
      .getSuggestions()
      .then(show)
      .catch(() => show(defaultSuggestions));

    return () => {
      settled = true;
      clearTimeout(timer);
    };
  }, []);

  return (
    <div className="prompts" aria-busy={prompts === null}>
      {prompts === null
        ? defaultSuggestions.map((p) => (
            <div
              className="prompt-placeholder"
              aria-hidden="true"
              key={p}
            />
          ))
        : prompts.map((p) => (
            <button key={p} onClick={() => onSelect(p)}>
              {p}
              <Plus size={15} />
            </button>
          ))}
    </div>
  );
}
