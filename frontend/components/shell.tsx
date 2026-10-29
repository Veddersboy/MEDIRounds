"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { authClient } from "@/src/lib/auth-client";

import {
  ChevronDown,
  Clock3,
  Menu,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings2,
  Trash2,
  X,
} from "lucide-react";

import { repository } from "@/lib/repository";
import { useApp } from "./app-provider";

const SIDEBAR_KEY = "medirounds.sidebar.collapsed";

function groupLabel(date: string) {
  const d = new Date(date);
  const today = new Date();

  if (d.toDateString() === today.toDateString()) {
    return "Today";
  }

  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (d.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }

  return "Earlier";
}

export function Shell({
  children,
}: {
  children: React.ReactNode;
}) {
  const { sessions, settings, refresh, error } = useApp();

  const pathname = usePathname();
  const router = useRouter();

  const [search, setSearch] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(
        localStorage.getItem(SIDEBAR_KEY) === "true"
      );
    } catch {
      setCollapsed(false);
    }
  }, []);

  function toggleSidebar() {
    setCollapsed((previous) => {
      const next = !previous;

      try {
        localStorage.setItem(SIDEBAR_KEY, String(next));
      } catch {
        // The toggle still works if storage is unavailable.
      }

      return next;
    });
  }
  async function handleSignOut() {
    try {
      setSigningOut(true);

      const { error } = await authClient.signOut();

      if (error) {
        alert(error.message || "Could not sign out.");
        return;
      }

      router.push("/sign-in");
      router.refresh();
    } catch {
      alert("Something went wrong while signing out.");
    } finally {
      setSigningOut(false);
    }
  }
  async function create() {
    try {
      setBusy(true);

      const session = await repository.createSession();

      await refresh();

      router.push(`/chat/${session.id}`);
      setMobileOpen(false);
    } catch (e) {
      alert(
        e instanceof Error
          ? e.message
          : "Could not create conversation"
      );
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (
      !confirm(
        "Delete this conversation? This cannot be undone."
      )
    ) {
      return;
    }

    try {
      await repository.deleteSession(id);
      await refresh();

      if (pathname === `/chat/${id}`) {
        router.push("/");
      }
    } catch (e) {
      alert(
        e instanceof Error
          ? e.message
          : "Could not delete conversation"
      );
    }
  }

  const filtered = sessions.filter(
    (session) =>
      session.title
        .toLowerCase()
        .includes(search.toLowerCase()) ||
      session.messages.some((message) =>
        message.content
          .toLowerCase()
          .includes(search.toLowerCase())
      )
  );

  return (
    <div
      className={`app-shell ${collapsed ? "sidebar-collapsed" : ""
        }`}
    >
      <aside
        className={`sidebar ${mobileOpen ? "open" : ""}`}
        aria-label="Main navigation"
        id="medirounds-sidebar"
      >
        <div className="brand">
          <span className="brand-name">MediRounds</span>

          <button
            className="icon-button desktop-sidebar-toggle"
            aria-label="Collapse sidebar"
            title="Close sidebar"
            aria-controls="medirounds-sidebar"
            onClick={toggleSidebar}
          >
            <PanelLeftClose size={19} />
          </button>

          <button
            className="icon-button mobile-close"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="main-nav">
          <Link
            href="/"
            className={
              pathname === "/" ||
                pathname.startsWith("/chat")
                ? "selected"
                : ""
            }
            onClick={() => setMobileOpen(false)}
          >
            <MessageSquare size={16} />
            Chat
          </Link>

          <Link
            href="/timeline"
            className={
              pathname === "/timeline" ? "selected" : ""
            }
            onClick={() => setMobileOpen(false)}
          >
            <Clock3 size={16} />
            Timeline
          </Link>

          <Link
            href="/settings"
            className={
              pathname === "/settings" ? "selected" : ""
            }
            onClick={() => setMobileOpen(false)}
          >
            <Settings2 size={16} />
            Settings
          </Link>
        </nav>

        <button
          className="new-chat"
          disabled={busy}
          onClick={() => void create()}
        >
          <Plus size={17} />
          New chat
        </button>

        <div className="sidebar-search">
          <Search size={15} />

          <input
            aria-label="Search conversations"
            placeholder="Search conversations"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="session-scroll">
          {["Today", "Yesterday", "Earlier"].map((group) => {
            const items = filtered.filter(
              (session) =>
                groupLabel(session.updatedAt) === group
            );

            return items.length ? (
              <section key={group}>
                <h3 className="group-label">{group}</h3>

                {items.map((session) => (
                  <div
                    className={`session-row ${pathname === `/chat/${session.id}`
                        ? "active"
                        : ""
                      }`}
                    key={session.id}
                  >
                    <Link
                      href={`/chat/${session.id}`}
                      onClick={() => setMobileOpen(false)}
                    >
                      <span className="session-title">
                        {session.title}
                      </span>

                      <span className="session-meta">
                        {new Date(
                          session.updatedAt
                        ).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </Link>

                    <button
                      title="Delete conversation"
                      aria-label={`Delete ${session.title}`}
                      onClick={() =>
                        void remove(session.id)
                      }
                      className="delete-session"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </section>
            ) : null;
          })}

          {!filtered.length && (
            <p className="empty-sidebar">
              No conversations found.
            </p>
          )}
        </div>

        <div className="sidebar-bottom">
          <div className="avatar">
            {settings.clinicianName
              .split(" ")
              .filter(Boolean)
              .slice(-2)
              .map((part) => part[0])
              .join("")
              .toUpperCase()}
          </div>

          <div className="user-copy">
            <strong>{settings.clinicianName}</strong>
            <small>{settings.specialty}</small>
          </div>
          <button
            type="button"
            className="sign-out-button"
            onClick={() => void handleSignOut()}
            disabled={signingOut}
            aria-label="Sign out"
            title="Sign out"
          >
            {signingOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Dismiss menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <main className="main-area">
        <div className="desktop-sidebar-controls">
          <button
            className="icon-button"
            aria-label="Expand sidebar"
            title="Open sidebar"
            aria-controls="medirounds-sidebar"
            aria-expanded={!collapsed}
            onClick={toggleSidebar}
          >
            <PanelLeftOpen size={21} />
          </button>

          <button
            className="icon-button"
            aria-label="New chat"
            title="New chat"
            disabled={busy}
            onClick={() => void create()}
          >
            <Plus size={20} />
          </button>
        </div>

        <div className="mobile-toolbar">
          <button
            className="icon-button"
            aria-label="Open menu"
            aria-controls="medirounds-sidebar"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={21} />
          </button>

          <span>MediRounds</span>

          <button
            className="icon-button"
            aria-label="New chat"
            disabled={busy}
            onClick={() => void create()}
          >
            <Plus size={19} />
          </button>
        </div>

        {error && (
          <div role="alert" className="error-banner">
            {error}
          </div>
        )}

        {children}
      </main>
    </div>
  );
}