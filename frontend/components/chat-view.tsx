"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDown,
  ArrowUp,
  BookOpen,
  Check,
  Clipboard,
  Plus,
  Stethoscope,
} from "lucide-react";

import { useApp } from "./app-provider";
import { repository } from "@/lib/repository";
import { ChatSession, Message } from "@/lib/types";

export function ChatView({ id }: { id?: string }) {
  const router = useRouter();
  const { settings, refresh } = useApp();

  const [session, setSession] = useState<ChatSession | null>(null);
  const [loading, setLoading] = useState(Boolean(id));
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");
  const [atBottom, setAtBottom] = useState(true);

  const endRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  // Load an existing conversation
  useEffect(() => {
    let active = true;

    if (!id) {
      setSession(null);
      setLoading(false);
      setError("");
      return;
    }

    setLoading(true);

    repository
      .getSession(id)
      .then((s) => {
        if (active) {
          setSession(s);
          setError(s ? "" : "Conversation not found");
        }
      })
      .catch((e) => {
        if (active) {
          setError(
            e instanceof Error ? e.message : "Failed to load chat"
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [id]);

  // Scroll to latest message
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages.length, sending]);

  // Send a message
  const send = useCallback(
    async (text: string) => {
      const content = text.trim();

      if (!content || sending) return;

      setSending(true);
      setError("");
      setDraft("");

      let target = id;

      try {
        if (!target) {
          const created = await repository.createSession();
          target = created.id;

          router.replace(`/chat/${target}`);
        }

        const timestamp = new Date().toISOString();

        // Optimistically display the user message
        setSession((prev) => ({
          id: target!,
          title: prev?.title ?? content.slice(0, 52),
          createdAt: prev?.createdAt ?? timestamp,
          updatedAt: timestamp,
          messages: [
            ...(prev?.messages ?? []),
            {
              id: `pending-${timestamp}`,
              role: "user",
              content,
              createdAt: timestamp,
            },
          ],
        }));

        // Send to repository (mock or FastAPI adapter)
        await repository.sendMessage(target!, content);

        // Reload conversation after response
        const current = await repository.getSession(target!);

        setSession(current);
        await refresh();
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Message failed to send"
        );

        setDraft(content);

        if (target) {
          const current = await repository
            .getSession(target)
            .catch(() => null);

          setSession(current);
        }
      } finally {
        setSending(false);
        textarea.current?.focus();
      }
    },
    [id, refresh, router, sending]
  );

  // Export conversation as Markdown
  function exportChat() {
    if (!session) return;

    const body = session.messages
      .map(
        (m) =>
          `## ${m.role === "user" ? "User" : "Rounds"}\n\n${m.content}`
      )
      .join("\n\n---\n\n");

    const blob = new Blob(
      [`# ${session.title}\n\n${body}`],
      { type: "text/markdown" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `rounds-${session.id}.md`;
    link.click();

    URL.revokeObjectURL(url);
  }

  // Copy assistant response
  async function copy(m: Message) {
    await navigator.clipboard.writeText(m.content);

    setCopied(m.id);

    setTimeout(() => {
      setCopied("");
    }, 1400);
  }

  const messages = session?.messages ?? [];

  return (
    <div className="chat-page">
      {/* Header */}
      <header className="page-header">
        <div>
          <h1>{session?.title ?? "New conversation"}</h1>
          <p>Type 2 diabetes research assistant</p>
        </div>

        {session && messages.length > 0 && (
          <button
            className="outline-btn"
            onClick={exportChat}
          >
            <BookOpen size={15} />
            Export
            <ArrowDown size={14} />
          </button>
        )}
      </header>

      {/* Conversation area */}
      <div
        className="chat-scroll"
        ref={scrollRef}
        onScroll={(e) => {
          const t = e.currentTarget;

          setAtBottom(
            t.scrollHeight - t.scrollTop - t.clientHeight < 100
          );
        }}
      >
        {loading ? (
          <div className="page-center muted">
            Loading conversation…
          </div>
        ) : messages.length === 0 ? (
          // Empty conversation
          <div className="welcome">
            <div className="welcome-mark">
              <Image
                className="welcome-logo-light"
                src="/medirounds-logo-light.svg"
                alt="MediRounds logo"
                width={120}
                height={120}
                priority
              />

              <Image
                className="welcome-logo-dark"
                src="/medirounds-logo-dark.svg"
                alt="MediRounds logo"
                width={120}
                height={120}
                priority
              />
            </div>

            <h2>What can MediRounds help you research?</h2>

            <p>
              Explore evidence-based questions about type 2 diabetes,
              clinical guidelines, and treatment considerations.
            </p>

            <div className="prompts">
              {[
                "Compare major classes of type 2 diabetes medications",
                "What should be considered when interpreting HbA1c?",
                "Summarize approaches to managing diabetes with CKD",
              ].map((p) => (
                <button
                  key={p}
                  onClick={() => void send(p)}
                >
                  {p}
                  <Plus size={15} />
                </button>
              ))}
            </div>
          </div>
        ) : (
          // Existing messages
          <div className="messages">
            {messages.map((m) => (
              <article
                className={`message ${m.role}`}
                key={m.id}
              >
                {m.role === "assistant" && (
                  <div className="speaker">
                    <span className="assistant-dot">
                      <Stethoscope size={13} />
                    </span>
                    Rounds
                  </div>
                )}

                <div className="message-content">
                  {m.content}
                </div>

                {/* Citations */}
                {m.citations?.length ? (
                  <div className="citations">
                    {m.citations.map((c, i) => (
                      <a
                        href={c.url || "#"}
                        target="_blank"
                        rel="noreferrer"
                        key={`${c.title}-${i}`}
                      >
                        {c.title}
                      </a>
                    ))}
                  </div>
                ) : null}

                {/* Copy assistant answer */}
                {m.role === "assistant" && (
                  <button
                    className="copy-button"
                    onClick={() => void copy(m)}
                    title="Copy answer"
                  >
                    {copied === m.id ? (
                      <Check size={14} />
                    ) : (
                      <Clipboard size={14} />
                    )}

                    {copied === m.id ? "Copied" : "Copy"}
                  </button>
                )}
              </article>
            ))}

            {/* Response loading indicator */}
            {sending && (
              <div className="responding">
                <span className="assistant-dot">
                  <Stethoscope size={13} />
                </span>

                <span className="dots">
                  Searching research<span>...</span>
                </span>
              </div>
            )}

            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Scroll to bottom */}
      {!atBottom && (
        <button
          className="scroll-down"
          onClick={() =>
            endRef.current?.scrollIntoView({
              behavior: "smooth",
            })
          }
        >
          <ArrowDown size={16} />
        </button>
      )}

      {/* Message composer */}
      <div className="composer-wrap">
        {error && (
          <div
            className="composer-error"
            role="alert"
          >
            {error}
          </div>
        )}

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send(draft);
          }}
        >
          <textarea
            ref={textarea}
            rows={1}
            aria-label="Message Rounds"
            placeholder="Ask a diabetes research question..."
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);

              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(
                e.target.scrollHeight,
                160
              )}px`;
            }}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                settings.enterToSend
              ) {
                e.preventDefault();
                void send(draft);
              }
            }}
            disabled={sending}
          />

          <button
            type="submit"
            disabled={!draft.trim() || sending}
            aria-label="Send message"
          >
            <ArrowUp size={18} />
          </button>
        </form>

        {settings.showDisclaimer && (
          <p className="disclaimer">
            Research support only — confirm findings against
            clinical guidelines and professional judgment.
          </p>
        )}
      </div>
    </div>
  );
}