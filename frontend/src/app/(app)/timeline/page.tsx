"use client";

import Link from "next/link";
import {
  Clock3,
  MessageSquare,
  MoveUpRight,
} from "lucide-react";

import { useApp } from "@/components/app-provider";

export default function Timeline() {
  const { sessions, loading } = useApp();

  const events = sessions
    .flatMap((session) =>
      session.messages.map((message) => ({
        id: message.id,
        sessionId: session.id,
        title: session.title,
        kind: message.role,
        description: message.content,
        at: message.createdAt,
      }))
    )
    .sort((a, b) => b.at.localeCompare(a.at));

  return (
    <div className="content-page">
      <header className="content-header">
        <span className="eyebrow">WORKSPACE</span>

        <h1>Activity timeline</h1>

        <p>
          Review conversations and research questions in
          chronological order.
        </p>
      </header>

      {loading ? (
        <p>Loading activity…</p>
      ) : !events.length ? (
        <div className="empty-state">
          <Clock3 size={26} />

          <h2>No activity yet</h2>

          <p>
            Your chat history will appear here after you
            begin a conversation.
          </p>

          <Link href="/">
            Start a chat
            <MoveUpRight size={14} />
          </Link>
        </div>
      ) : (
        <div className="timeline-list">
          {events.map((event, index) => (
            <div
              className="timeline-event"
              key={event.id}
            >
              <div className="timeline-track">
                <span>
                  <MessageSquare size={15} />
                </span>

                {index !== events.length - 1 && (
                  <div className="timeline-line" />
                )}
              </div>

              <div className="timeline-event-body">
                <div className="timeline-date">
                  {new Date(event.at).toLocaleDateString(
                    [],
                    {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    }
                  )}
                  {" · "}
                  {new Date(event.at).toLocaleTimeString(
                    [],
                    {
                      hour: "numeric",
                      minute: "2-digit",
                    }
                  )}
                </div>

                <Link
                  href={`/chat/${event.sessionId}`}
                  className="timeline-title"
                >
                  {event.title}
                  <MoveUpRight size={15} />
                </Link>

                <p className="timeline-description">
                  <b>
                    {event.kind === "user"
                      ? "You"
                      : "Rounds"}
                    :
                  </b>{" "}
                  {event.description.slice(0, 240)}
                  {event.description.length > 240
                    ? "…"
                    : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}