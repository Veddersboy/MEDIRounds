# MEDIRounds — Codebase Source of Truth

> **Last updated:** 2026-11-06
>
> This document maps every file in the MEDIRounds project, explains what each module does, and provides a practical guide for implementing new features — particularly adding an **"Experience Level"** setting that prepends a system prompt to the AI API call.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Tree](#directory-tree)
3. [Root-Level Files](#root-level-files)
4. [Backend (FastAPI / Python)](#backend-fastapi--python)
   - [Entry Point — main.py](#entry-point--mainpy)
   - [Database — database.py](#database--databasepy)
   - [ORM Models — models.py](#orm-models--modelspy)
   - [Pydantic Schemas — schemas.py](#pydantic-schemas--schemaspy)
   - [Auth — auth.py](#auth--authpy)
   - [Ownership Guards — ownership.py](#ownership-guards--ownershippy)
   - [Chat Router — routers/chats.py](#chat-router--routerschatspy)
   - [Alembic Migrations](#alembic-migrations)
   - [Tests](#backend-tests)
5. [Frontend (Next.js / TypeScript)](#frontend-nextjs--typescript)
   - [Types — lib/types.ts](#types--libtypests)
   - [Repository — lib/repository.ts](#repository--librepositoryts)
   - [App Context — components/app-provider.tsx](#app-context--componentsapp-providertsx)
   - [Shell / Sidebar — components/shell.tsx](#shell--sidebar--componentsshelltsx)
   - [Chat View — components/chat-view.tsx](#chat-view--componentschat-viewtsx)
   - [Auth Form — components/auth-form.tsx](#auth-form--componentsauth-formtsx)
   - [Settings Page — src/app/(app)/settings/page.tsx](#settings-page--srcappappsettingspagetsx)
   - [Timeline Page — src/app/(app)/timeline/page.tsx](#timeline-page--srcappapptimelinepagetsx)
   - [Routing & Layouts](#routing--layouts)
   - [Auth Library Files](#auth-library-files)
   - [Styling — globals.css](#styling--globalscss)
6. [Docker & Environment](#docker--environment)
7. [Data Flow: Sending a Message](#data-flow-sending-a-message)
8. [Data Flow: Settings Save/Load](#data-flow-settings-saveload)
9. [Implementation Guide — Adding "Experience Level"](#implementation-guide--adding-experience-level)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────┐  ┌─────────┐ │
│  │  Frontend    │   │  Backend    │   │ Postgres │  │ Mailpit │ │
│  │  Next.js     │──▶│  FastAPI    │──▶│  DB      │  │ (SMTP)  │ │
│  │  :3000       │   │  :8000      │   │  :5432   │  │ :8025   │ │
│  └──────┬───────┘   └──────┬──────┘   └──────────┘  └─────────┘ │
│         │                  │                                     │
│         │ Better Auth      │ Proxies to external                 │
│         │ (email+password) │ RAG / Chatbot API                   │
│         ▼                  ▼                                     │
│  ┌─────────────┐   ┌──────────────┐                             │
│  │  pgAdmin    │   │ External RAG │                             │
│  │  :5050      │   │ Service      │                             │
│  └─────────────┘   └──────────────┘                             │
└──────────────────────────────────────────────────────────────────┘
```

**MEDIRounds** is a medical research chat assistant focused on Type 2 Diabetes. It has:

- **Frontend**: Next.js 15 app with Better Auth for sign-in/sign-up, a sidebar shell, chat UI, timeline, and settings page.
- **Backend**: FastAPI app that authenticates via Better Auth session cookies, then proxies chat requests to an external RAG (Retrieval-Augmented Generation) chatbot service.
- **Database**: PostgreSQL shared by both frontend (Better Auth tables) and backend (chat sessions, messages, citations, user settings).
- **Two data modes**: The frontend can run in `mock` mode (localStorage only, no backend needed) or `api` mode (hits the FastAPI backend). Controlled by `NEXT_PUBLIC_DATA_MODE`.

---

## Directory Tree

```
MEDIRounds/
├── .env                              # Root env vars (Docker Compose)
├── .env.example                      # Template for .env
├── docker-compose.yml                # All services
├── README.md
├── guide.MD                          # ← THIS FILE
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini                   # Alembic config
│   ├── alembic/
│   │   ├── env.py                    # Migration runner (async + sync)
│   │   ├── script.py.mako            # Migration template
│   │   └── versions/
│   │       ├── 0001_initial_medirounds.py
│   │       └── 0002_better_auth.py
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── database.py               # Engine, session factory, Settings
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── auth.py                   # Cookie-based session auth
│   │   ├── ownership.py              # Row-level ownership guards
│   │   └── routers/
│   │       └── chats.py              # /api/v1/chats endpoints (RAG proxy)
│   └── tests/
│       ├── test_auth.py
│       ├── test_database_migration.py
│       ├── test_query_ownership.py
│       └── test_schema_validation.py
│
└── frontend/
    ├── Dockerfile
    ├── .env                          # Frontend-specific env vars
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── eslint.config.mjs
    ├── postcss.config.mjs
    ├── AGENTS.md / CLAUDE.md
    │
    ├── components/                   # Shared React components
    │   ├── app-provider.tsx          # Global context (user, sessions, settings)
    │   ├── auth-form.tsx             # Sign-in / sign-up form
    │   ├── chat-view.tsx             # Main chat UI
    │   └── shell.tsx                 # Sidebar + layout shell
    │
    ├── lib/                          # Shared library code
    │   ├── types.ts                  # TypeScript interfaces & defaults
    │   └── repository.ts            # Data access (mock + API adapters)
    │
    ├── src/
    │   ├── proxy.ts                  # Next.js middleware (cookie guard)
    │   ├── app/
    │   │   ├── layout.tsx            # Root HTML layout
    │   │   ├── globals.css           # All styles (~19KB)
    │   │   ├── favicon.ico
    │   │   │
    │   │   ├── (auth)/               # Auth route group (no sidebar)
    │   │   │   ├── layout.tsx        # Centered layout, redirects if signed in
    │   │   │   ├── sign-in/page.tsx
    │   │   │   └── sign-up/page.tsx
    │   │   │
    │   │   ├── (app)/                # App route group (sidebar + provider)
    │   │   │   ├── layout.tsx        # Gets session, wraps in AppProvider + Shell
    │   │   │   ├── page.tsx          # / → ChatView (new conversation)
    │   │   │   ├── chat/[id]/page.tsx  # /chat/:id → ChatView with ID
    │   │   │   ├── settings/page.tsx # /settings → SettingsPage
    │   │   │   └── timeline/page.tsx # /timeline → Timeline
    │   │   │
    │   │   └── api/auth/[...all]/route.ts  # Better Auth API handler
    │   │
    │   └── lib/
    │       ├── auth.ts               # Better Auth server instance
    │       ├── auth-client.ts        # Better Auth client instance
    │       └── auth-validation.mjs   # Client-side form validation
    │
    ├── public/                       # Static assets (logos, icons)
    └── tests/
        └── autb-validation.test.mjs
```

---

## Root-Level Files

### `.env` / `.env.example`
**Location:** `MEDIRounds/.env`, `MEDIRounds/.env.example`

All environment variables for Docker Compose. Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Backend DB connection (postgresql+asyncpg://) |
| `AUTH_DATABASE_URL` | Frontend DB connection (plain postgresql://) |
| `BETTER_AUTH_SECRET` | Shared secret for session cookie signing |
| `CHATBOT_API_URL` | External RAG service endpoint |
| `CHATBOT_API_KEY` | API key for the RAG service |
| `NEXT_PUBLIC_DATA_MODE` | `mock` or `api` — controls frontend data source |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL when in API mode |

### `docker-compose.yml`
**Location:** `MEDIRounds/docker-compose.yml`

Defines 5 services: `frontend`, `backend`, `postgres`, `pgadmin`, `mailpit`. The frontend depends on the backend and postgres; the backend depends on postgres and mailpit.

---

## Backend (FastAPI / Python)

### Entry Point — `main.py`
**Location:** [`backend/app/main.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/main.py)

Creates the FastAPI `app` instance and configures CORS for `localhost:3000`. Mounts the chats router.

| Endpoint | Function | Purpose |
|---|---|---|
| `GET /` | `root()` | Health ping — returns `"MediRounds app backend is running"` |
| `GET /health` | `health()` | Simple health check |
| `GET /health/db` | `database_health()` | Tests DB connectivity |
| `GET /db-test` | `db_test()` | Returns `SELECT 1` result |
| `GET /api/v1/me` | `me()` | Returns the currently authenticated user (requires auth) |

---

### Database — `database.py`
**Location:** [`backend/app/database.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/database.py)

| Symbol | Purpose |
|---|---|
| `Settings` (class) | Pydantic `BaseSettings` — loads `DATABASE_URL`, `BETTER_AUTH_SECRET`, `FRONTEND_ORIGIN`, `CHATBOT_API_URL`, `CHATBOT_API_KEY` from `.env` |
| `settings` | Singleton `Settings` instance |
| `engine` | Async SQLAlchemy engine |
| `AsyncSessionLocal` | Session factory |
| `get_db()` | FastAPI dependency — yields an async DB session |

**To change configuration variables:** Add them to the `Settings` class and set them in `.env`.

---

### ORM Models — `models.py`
**Location:** [`backend/app/models.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/models.py)

| Model | Table | Purpose |
|---|---|---|
| `Base` | — | SQLAlchemy declarative base |
| `AuthUser` | `user` | Better Auth user (id, name, email, image, timestamps). Has relationships to `ChatSession` and `UserSettings` |
| `AuthSession` | `session` | Better Auth login sessions (token, expiry, IP, user agent) |
| `AuthAccount` | `account` | Better Auth OAuth/credential accounts |
| `AuthVerification` | `verification` | Better Auth email verification tokens |
| `ChatSession` | `chat_sessions` | A conversation — belongs to a user, has many messages |
| `Message` | `messages` | A single chat message (role: user/assistant, content, metadata). Belongs to a ChatSession |
| `Citation` | `citations` | A source citation attached to a message |
| `UserSettings` | `user_settings` | Per-user preferences. **Current columns: `theme`, `clinician_name`, `specialty`, `show_disclaimer`, `enter_to_send`** |

Helper functions:
- `utcnow()` — Returns current UTC datetime
- `make_id()` — Generates a UUID4 string

---

### Pydantic Schemas — `schemas.py`
**Location:** [`backend/app/schemas.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/schemas.py)

| Schema | Purpose |
|---|---|
| `CitationSchema` | Validate/serialize citations (title, url, detail) |
| `MessageCreate` | Validate incoming message body (`content: NonBlank`) |
| `MessageSchema` | Serialize a message for API response |
| `ChatSessionSchema` | Serialize a full conversation with messages |
| `ChatTitleUpdate` | Validate rename request |
| `UserSettingsSchema` | **Validate/serialize user settings. Current fields: `theme`, `clinicianName`, `specialty`, `showDisclaimer`, `enterToSend`** |
| `CurrentUserSchema` | Serialize the `/api/v1/me` response (id, name, email) |

---

### Auth — `auth.py`
**Location:** [`backend/app/auth.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/auth.py)

| Symbol | Purpose |
|---|---|
| `COOKIE_NAMES` | Tuple of Better Auth cookie names to look for |
| `read_session_token(cookie_value, secret)` | Validates HMAC signature on the session cookie, returns the token if valid |
| `get_current_user(request, db)` | **FastAPI dependency** — extracts session cookie, verifies it, looks up the user in the DB. Returns `AuthUser` or raises `401` |

---

### Ownership Guards — `ownership.py`
**Location:** [`backend/app/ownership.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/ownership.py)

Row-level security helpers. Each function queries for a resource **only if it belongs to the authenticated user**, raising `404` otherwise.

| Function | Returns |
|---|---|
| `get_owned_chat(chat_id, user_id, db)` | `ChatSession` |
| `get_owned_message(message_id, user_id, db)` | `Message` |
| `get_owned_citation(citation_id, user_id, db)` | `Citation` |
| `get_owned_settings(user_id, db)` | `UserSettings` |

---

### Chat Router — `routers/chats.py`
**Location:** [`backend/app/routers/chats.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/app/routers/chats.py)

**This is where all chat API logic lives.** It acts as a **proxy** to an external RAG service (configured via `CHATBOT_API_URL`). All endpoints require authentication.

| Endpoint | Function | What It Does |
|---|---|---|
| `GET /api/v1/chats` | `list_chats()` | Lists all conversations from the RAG service for the user |
| `POST /api/v1/chats` | `create_chat()` | Creates a new conversation on the RAG service |
| `GET /api/v1/chats/{id}` | `get_chat()` | Gets a single conversation + its messages |
| `POST /api/v1/chats/{id}/messages` | `send_message()` | **Sends a user message to the RAG service** — this is the function that calls the external AI |

Key internal functions:

| Function | Purpose |
|---|---|
| `require_chatbot_url()` | Validates `CHATBOT_API_URL` is configured |
| `rag_request(method, path, user_id, payload)` | **Makes HTTP requests to the external RAG service.** Passes `X-User-ID` header and optional Bearer token. This is where the actual AI call happens. |
| `map_message(record)` | Transforms RAG response into frontend-compatible format |
| `map_conversation(record, messages)` | Transforms RAG conversation into frontend format |
| `list_rag_conversations(user_id)` | Fetches all conversations from RAG API |
| `list_rag_messages(conversation_id, user_id)` | Fetches messages for a conversation from RAG API |

> **🔑 CRITICAL:** The `rag_request()` function and `send_message()` endpoint are where the payload is built before being sent to the AI. **This is where you would inject a system prompt prefix based on experience level.**

---

### Alembic Migrations

**Location:** `backend/alembic/`

| File | Purpose |
|---|---|
| [`alembic.ini`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/alembic.ini) | Alembic configuration |
| [`env.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/alembic/env.py) | Migration runner — supports async (PostgreSQL) and sync (SQLite for tests) |
| [`0001_initial_medirounds.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/alembic/versions/0001_initial_medirounds.py) | Creates initial tables: `users`, `chat_sessions`, `messages`, `citations`, `user_settings` |
| [`0002_better_auth.py`](file:///C:/Users/LM728/Desktop/MEDIRounds/backend/alembic/versions/0002_better_auth.py) | Adds Better Auth tables (`user`, `session`, `account`, `verification`), migrates foreign keys from old `users` table to new `user` table |

**To add a new column to `user_settings`:** You need a new Alembic migration (e.g., `0003_add_experience.py`).

---

### Backend Tests

**Location:** `backend/tests/`

| File | What It Tests |
|---|---|
| `test_auth.py` | `read_session_token()` — HMAC verification, cookie parsing |
| `test_database_migration.py` | Runs Alembic upgrade/downgrade on SQLite |
| `test_query_ownership.py` | Row-level ownership guards |
| `test_schema_validation.py` | Pydantic schema validation |

---

## Frontend (Next.js / TypeScript)

### Types — `lib/types.ts`
**Location:** [`frontend/lib/types.ts`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/lib/types.ts)

Defines all shared TypeScript interfaces:

| Type | Fields | Purpose |
|---|---|---|
| `Role` | `"user" \| "assistant"` | Message sender |
| `Citation` | `title, url?, detail?` | Source reference |
| `Message` | `id, role, content, createdAt, citations?` | Chat message |
| `ChatSession` | `id, title, createdAt, updatedAt, messages, archived?` | Conversation |
| **`Settings`** | **`theme, specialty, showDisclaimer, enterToSend`** | **User preferences — ADD `experience` HERE** |
| `TimelineItem` | `id, sessionId, kind, title, description, at` | Timeline entry |
| `ChatRepository` | Interface with 8 methods | Data access contract |
| **`defaultSettings`** | **`{ theme: "light", specialty: "Endocrinology", showDisclaimer: true, enterToSend: true }`** | **Default values — ADD `experience` default HERE** |

---

### Repository — `lib/repository.ts`
**Location:** [`frontend/lib/repository.ts`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/lib/repository.ts)

Contains **two implementations** of the `ChatRepository` interface:

#### `mockRepository` (localStorage-based)
Used when `NEXT_PUBLIC_DATA_MODE !== "api"`. All data lives in `localStorage`. Provides sample conversations for demo purposes.

| Method | What It Does |
|---|---|
| `listSessions()` | Reads sessions from localStorage, filters out archived, sorts by updatedAt |
| `getSession(id)` | Finds a session by ID |
| `createSession()` | Creates a new empty conversation |
| `renameSession(id, title)` | Updates session title |
| `deleteSession(id)` | Removes session from storage |
| `sendMessage(id, content)` | Appends user message + mock assistant response |
| `getSettings()` | Reads settings from localStorage (`rounds.demo.settings.v1` key) |
| `saveSettings(settings)` | Writes settings to localStorage |

#### `apiRepository` (FastAPI-backed)
Used when `NEXT_PUBLIC_DATA_MODE === "api"`. Calls the FastAPI backend with cookies.

| Method | What It Does |
|---|---|
| `listSessions()` | `GET /api/v1/chats` |
| `getSession(id)` | `GET /api/v1/chats/:id` |
| `createSession()` | `POST /api/v1/chats` |
| `sendMessage(id, content)` | `POST /api/v1/chats/:id/messages` |
| `getSettings()` | Falls back to `mockRepository.getSettings()` (localStorage) |
| `saveSettings()` | Falls back to `mockRepository.saveSettings()` (localStorage) |

> **Note:** Even in API mode, settings are currently stored in localStorage, not on the server. The backend has the schema and model for server-side settings (`UserSettings`, `UserSettingsSchema`) but no router endpoints for them yet.

#### `repository` (exported)
**Line 330-333:** The exported `repository` is chosen based on `NEXT_PUBLIC_DATA_MODE`:
```ts
export const repository: ChatRepository =
  process.env.NEXT_PUBLIC_DATA_MODE === "api"
    ? apiRepository
    : mockRepository;
```

---

### App Context — `components/app-provider.tsx`
**Location:** [`frontend/components/app-provider.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/components/app-provider.tsx)

Creates a React context (`AppContext`) that provides:

| Value | Type | Description |
|---|---|---|
| `user` | `SessionUser` | Current signed-in user `{ id, name, email }` |
| `sessions` | `ChatSession[]` | All conversations |
| `settings` | `Settings` | Current user settings |
| `loading` | `boolean` | Whether initial data is loading |
| `error` | `string \| null` | Any load errors |
| `refresh()` | `() => Promise<void>` | Reloads conversations from repository |
| `setSettings(s)` | `(s: Settings) => Promise<void>` | Saves settings via repository and updates state |

**Key behaviors:**
- On mount, loads conversations (`repository.listSessions()`) and settings (`repository.getSettings()`)
- Applies theme (light/dark/system) via `document.documentElement.dataset.theme`
- `useApp()` hook provides access to the context

---

### Shell / Sidebar — `components/shell.tsx`
**Location:** [`frontend/components/shell.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/components/shell.tsx)

The main application layout with collapsible sidebar. Wraps all `(app)` pages.

**Key functions:**

| Function | Purpose |
|---|---|
| `groupLabel(date)` | Groups conversations into "Today", "Yesterday", "Earlier" |
| `toggleSidebar()` | Collapses/expands sidebar, persists to localStorage |
| `handleSignOut()` | Signs out via Better Auth client, redirects to sign-in |
| `create()` | Creates new conversation via repository, navigates to it |
| `remove(id)` | Deletes conversation with confirmation |

**Sidebar sections:**
- Brand name
- Navigation links (Chat, Timeline, Settings)
- "New chat" button
- Search conversations input
- Conversation list grouped by date
- User profile (avatar, name, specialty, sign-out button)

> **Line 324:** The sidebar displays `settings.specialty` under the user name.

---

### Chat View — `components/chat-view.tsx`
**Location:** [`frontend/components/chat-view.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/components/chat-view.tsx)

The main chat interface. Accepts an optional `id` prop (existing conversation) or starts a new one.

**Key functions:**

| Function | Purpose |
|---|---|
| `send(text)` | Core message-sending function. If no conversation exists, creates one. Optimistically adds the user message to UI, calls `repository.sendMessage()`, reloads conversation |
| `exportChat()` | Exports conversation as a downloadable Markdown file |
| `copy(m)` | Copies assistant message to clipboard |

**Features:**
- Welcome screen with suggested prompts when no messages
- Markdown rendering of assistant responses via `react-markdown` + `remark-gfm`
- Citation links on assistant messages
- Copy-to-clipboard on assistant messages
- Scroll-to-bottom button
- Loading indicator ("Searching research...")
- Enter-to-send behavior controlled by `settings.enterToSend`
- Clinical disclaimer controlled by `settings.showDisclaimer`

> **Line 124:** `repository.sendMessage(target!, content)` — This is the frontend call that triggers the AI. The `content` is the raw user message. **To add experience-based system prompt, you would either prepend here or (better) on the backend.**

---

### Auth Form — `components/auth-form.tsx`
**Location:** [`frontend/components/auth-form.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/components/auth-form.tsx)

Dual-mode form for sign-in and sign-up. Uses `better-auth/react` client. On success, redirects to `/timeline`.

**Fields:**
- Sign-in: email, password
- Sign-up: name, email, password, confirm password

Uses `validateSignIn()` / `validateSignUp()` from `auth-validation.mjs` before submission.

---

### Settings Page — `src/app/(app)/settings/page.tsx`
**Location:** [`frontend/src/app/(app)/settings/page.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/(app)/settings/page.tsx)

**This is the main file to edit when adding the experience level UI.**

**Current sections:**

1. **Profile** — Display name (read-only from account), Clinical focus (editable `specialty`)
2. **Appearance** — Theme selector (Light / Dark / Follow system)
3. **Chat behavior** — "Enter to send" toggle, "Show clinical disclaimer" toggle

**Key mechanics:**
- Maintains a local `draft: Settings` state for unsaved changes
- `update<K>(key, value)` — Generic setter that updates one key of the draft
- `save()` — Calls `setSettings(draft)` from AppProvider, which writes to repository
- Shows "Preferences saved" status message on success

> **To add experience level:** Add a new `<section>` or a `<label className="field">` inside the Profile section with a `<select>` dropdown. Wire it to `update("experience", value)`.

---

### Timeline Page — `src/app/(app)/timeline/page.tsx`
**Location:** [`frontend/src/app/(app)/timeline/page.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/(app)/timeline/page.tsx)

Flattens all messages from all sessions into a chronological feed. Each event links back to its conversation.

---

### Routing & Layouts

| File | Route | Purpose |
|---|---|---|
| [`src/app/layout.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/layout.tsx) | Root `<html>` | Sets up HTML, loads `globals.css` |
| [`src/app/(auth)/layout.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/(auth)/layout.tsx) | `/sign-in`, `/sign-up` | Centered layout, redirects to `/` if already signed in |
| [`src/app/(app)/layout.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/(app)/layout.tsx) | All app pages | **Gets Better Auth session, redirects to `/sign-in` if not authenticated.** Wraps children in `AppProvider` + `Shell` |
| [`src/app/(app)/page.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/(app)/page.tsx) | `/` | Renders `ChatView` (new conversation) |
| [`src/app/(app)/chat/[id]/page.tsx`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/(app)/chat/[id]/page.tsx) | `/chat/:id` | Renders `ChatView` with conversation ID |
| [`src/app/api/auth/[...all]/route.ts`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/api/auth/[...all]/route.ts) | `/api/auth/*` | Better Auth API handler (sign-in, sign-up, sign-out, session) |

---

### Auth Library Files

| File | Purpose |
|---|---|
| [`src/lib/auth.ts`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/lib/auth.ts) | **Server-side** Better Auth instance. Connects to PostgreSQL via `pg` Pool. Enables email+password auth. Reuses pool across Next.js hot reloads |
| [`src/lib/auth-client.ts`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/lib/auth-client.ts) | **Client-side** Better Auth instance. Exports `authClient` used for `signIn.email()`, `signUp.email()`, `signOut()` |
| [`src/lib/auth-validation.mjs`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/lib/auth-validation.mjs) | Pure JS validation functions: `validateSignIn()`, `validateSignUp()`, `isValidEmail()`. Used client-side before calling auth |
| [`src/proxy.ts`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/proxy.ts) | Next.js middleware — redirects to `/sign-in` if no session cookie exists (lightweight guard before the full server-side check) |

---

### Styling — `globals.css`
**Location:** [`frontend/src/app/globals.css`](file:///C:/Users/LM728/Desktop/MEDIRounds/frontend/src/app/globals.css)

~19KB CSS file with all application styles. Uses CSS custom properties for theming (`[data-theme="dark"]`). Key class prefixes:
- `.app-shell`, `.sidebar`, `.main-area` — Layout
- `.chat-page`, `.messages`, `.message`, `.composer` — Chat UI
- `.settings-page`, `.settings-section`, `.setting-toggle`, `.field` — Settings
- `.content-page`, `.timeline-*` — Timeline
- `.auth-*` — Auth forms

---

## Docker & Environment

### `docker-compose.yml`
**Location:** [`docker-compose.yml`](file:///C:/Users/LM728/Desktop/MEDIRounds/docker-compose.yml)

| Service | Container Name | Port | Notes |
|---|---|---|---|
| `frontend` | `medirounds-frontend` | 3000 | Next.js dev server. Mounts `./frontend` as volume |
| `backend` | `medirounds-backend` | 8000 | FastAPI with uvicorn. Mounts `./backend` as volume |
| `postgres` | `medirounds-postgres` | 5432 | PostgreSQL 18, persistent volume `postgres_data` |
| `pgadmin` | `medirounds-pgadmin` | 5050 | Database GUI |
| `mailpit` | `medirounds-mailpit` | 1025 (SMTP), 8025 (Web) | Local email testing |

---

## Data Flow: Sending a Message

```
User types message → ChatView.send(text)
                      │
                      ├─ (If new conversation) repository.createSession()
                      │   → POST /api/v1/chats → rag_request("POST", "/conversations")
                      │
                      ├─ Optimistically renders user message in UI
                      │
                      ├─ repository.sendMessage(id, content)
                      │   → POST /api/v1/chats/:id/messages
                      │      → chats.py send_message()
                      │         → Verifies conversation ownership via RAG
                      │         → rag_request("POST", "/chat", payload={conversation_id, message})
                      │            → httpx call to CHATBOT_API_URL/chat
                      │            → External RAG processes, stores, returns response
                      │         → Fetches latest messages from RAG
                      │         → Returns last assistant message
                      │
                      └─ Reloads conversation, refreshes sidebar
```

---

## Data Flow: Settings Save/Load

```
LOAD:
  AppProvider mount → repository.getSettings()
    → (mock) localStorage.getItem("rounds.demo.settings.v1")
    → (api) also localStorage (API mode hasn't wired server settings yet)
  → setLocalSettings(savedSettings)
  → Theme applied to document.documentElement.dataset.theme

SAVE:
  SettingsPage → save() → setSettings(draft)
    → AppProvider.save() → repository.saveSettings(settings)
      → (mock/api) localStorage.setItem("rounds.demo.settings.v1", JSON)
    → setLocalSettings(s)
    → Theme re-applied via useEffect
```

---

## Implementation Guide — Adding "Experience Level"

Your plan: Add a new "experience" setting in the Profile section that prepends a system prompt to the API call based on the user's experience level.

### Files to Change (Checklist)

Below is every file you need to touch, in the recommended order:

---

#### 1. Frontend Type — `frontend/lib/types.ts`

**What to do:** Add `experience` to the `Settings` interface and `defaultSettings`.

```ts
// In the Settings interface, add:
experience: "student" | "resident" | "fellow" | "attending" | "advanced";

// In defaultSettings, add:
experience: "resident",
```

---

#### 2. Frontend Settings UI — `frontend/src/app/(app)/settings/page.tsx`

**What to do:** Add a `<select>` dropdown in the Profile section (after "Clinical focus"), wired to `update("experience", ...)`.

Place it around **line 84** (after the `specialty` input, before `</section>`).

---

#### 3. Backend ORM Model — `backend/app/models.py`

**What to do:** Add an `experience` column to the `UserSettings` class (around **line 130**):

```python
experience: Mapped[str] = mapped_column(String(32), default="resident", nullable=False)
```

---

#### 4. Backend Pydantic Schema — `backend/app/schemas.py`

**What to do:** Add `experience` to `UserSettingsSchema` (around **line 50**):

```python
experience: Literal["student", "resident", "fellow", "attending", "advanced"] = "resident"
```

---

#### 5. Alembic Migration — `backend/alembic/versions/0003_add_experience.py` (new file)

**What to do:** Create a migration that adds the `experience` column to `user_settings`:

```python
op.add_column("user_settings", sa.Column("experience", sa.String(32), nullable=False, server_default="resident"))
```

---

#### 6. Backend Chat Router — `backend/app/routers/chats.py`

**What to do:** This is the **most important change**. In the `send_message()` endpoint (around **line 243**):

1. Load the user's settings (from DB or accept from the frontend payload)
2. Build a system prompt prefix based on the experience level
3. Include it in the `rag_request()` payload

**Where specifically to look:**
- **Line 263-271** — The `rag_request("POST", "/chat", ...)` call. The `payload` dict currently has `conversation_id` and `message`. You would add a `system_prompt` or `context` field here based on the experience level.

Example mapping:
```python
EXPERIENCE_PROMPTS = {
    "student": "Explain concepts thoroughly with foundational context. Define medical terminology.",
    "resident": "Provide evidence-based clinical reasoning. Cite guidelines when relevant.",
    "fellow": "Focus on nuanced clinical decision-making and subspecialty considerations.",
    "attending": "Be concise and direct. Emphasize latest evidence and guideline updates.",
    "advanced": "Provide expert-level detail. Include study methodology and statistical context.",
}
```

---

#### 7. Frontend Repository — `frontend/lib/repository.ts`

**What to do:** If you want the frontend to **send** the experience level as part of the message payload (instead of the backend reading it from the DB), update `sendMessage()` in both `mockRepository` and `apiRepository` to accept and pass the experience level.

**However**, the cleaner approach is to have the **backend** read the user's settings from the DB when processing a message, so the frontend doesn't need to change here.

---

#### 8. Frontend App Provider — `frontend/components/app-provider.tsx`

**No changes needed** — it already handles arbitrary `Settings` keys via the generic type.

---

#### 9. Frontend Chat View — `frontend/components/chat-view.tsx`

**Likely no changes needed** — unless you want to display the experience level somewhere in the chat UI.

---

### Implementation Decision Tree

```
Q: Should the backend read experience from DB or should the frontend send it?

Option A: Backend reads from DB (Recommended)
  ├── Pro: Single source of truth, can't be spoofed by client
  ├── Pro: No frontend repository changes needed
  ├── Con: Need server-side settings endpoints (GET/PUT /api/v1/settings)
  └── Files: models.py, schemas.py, migration, chats.py, settings page, types.ts

Option B: Frontend sends experience in message payload
  ├── Pro: Works immediately with localStorage settings
  ├── Con: Client can send arbitrary experience level
  ├── Con: Need to update repository.ts, ChatRepository interface
  └── Files: types.ts, repository.ts, chats.py, settings page
```

### Quick Reference — Where Things Connect

| Concept | Frontend File | Backend File |
|---|---|---|
| Settings type/shape | `lib/types.ts` → `Settings` | `schemas.py` → `UserSettingsSchema` |
| Settings storage | `lib/repository.ts` → `getSettings/saveSettings` | `models.py` → `UserSettings` |
| Settings UI | `settings/page.tsx` | — |
| Settings in context | `app-provider.tsx` → `settings` state | — |
| Message send flow | `chat-view.tsx` → `send()` → `repository.sendMessage()` | `routers/chats.py` → `send_message()` → `rag_request()` |
| AI prompt construction | — | `routers/chats.py` → `rag_request()` payload |
| Database columns | — | `models.py` + Alembic migration |
