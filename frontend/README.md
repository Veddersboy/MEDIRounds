# MediRounds — frontend implementation

## Feature set

- Create a new conversation and view old conversations from the sidebar.
- Search saved conversations by title or message text.
- Reopen and delete individual conversations.
- Separate `/timeline` activity page displaying past user/assistant messages.
- Separate `/settings` page for user display, specialty, theme, send-key behavior, and disclaimer.
- Enter-to-send or Shift+Enter newline; configurable preference.
- Export each conversation as Markdown and copy individual AI responses.
- Responsive mobile navigation, loading states, and error states.
- **Mock mode (default):** fully functional local demo, using browser `localStorage` with illustrative assistant responses. The demonstration does **not** perform AI inference or RAG.
- **API mode:** replace mock persistence with FastAPI calls via a typed repository adapter.

## Existing repo relationship

The public repository contains `backend/`, `frontend/`, `docker-compose.yml`, `.gitignore`, and a root `README.md`. The delivered package intentionally affects only `frontend/` and this standalone documentation. No Python code, database schema, RAG endpoint, or authentication has been added.

## Directory hierarchy

```text
rounds-deliverable/
├── README.md                        # This full integration guide
└── frontend/                        
    ├── .env.example                 # Frontend environment variables
    ├── package.json                 
    ├── postcss.config.mjs           
    ├── tsconfig.json                
    ├── next-env.d.ts                
    ├── app/
    │   ├── layout.tsx               # Root metadata, global state, app shell
    │   ├── globals.css              
    │   ├── page.tsx                 # new chat start
    │   ├── chat/
    │   │   └── [id]/page.tsx        # /chat/:id — saved conversation
    │   ├── timeline/page.tsx        # /timeline — historical activity
    │   └── settings/page.tsx        # /settings — preferences
    ├── components/
    │   ├── app-provider.tsx         # Shared sessions/settings, loading, refresh
    │   ├── shell.tsx                # Sidebar, search, links, deletion, account
    │   └── chat-view.tsx            # Chat messages, composer, export, copy
    └── lib/
        ├── types.ts                 # Typed chats, messages, citations, settings
        └── repository.ts            # MockRepository + FastAPI repository adapter
```

### Responsibilities and dependencies

```text
app/layout.tsx
  └── AppProvider (shared data state)
       └── Shell (navigation and previous sessions)
            └── current app route
                 ├── ChatView
                 ├── Timeline
                 └── Settings

View components → lib/repository.ts → (mock browser storage | FastAPI HTTP)
                                    ↳ lib/types.ts
```

The UI never directly opens a database connection. `ChatRepository` is an interface designed to isolate the backend contract from views.

## Install and run

```bash
cd MEDIRounds/frontend
npm install
cp .env.example .env.local    # Windows PowerShell: Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. `NEXT_PUBLIC_DATA_MODE=mock` is the default even if no `.env.local` file is present. Starter history is created when the browser loads the app for the first time. Open DevTools → Application → Local Storage to clear demo data.

### Configure FastAPI

```dotenv
NEXT_PUBLIC_DATA_MODE=api
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Restart Next.js when changing `NEXT_PUBLIC_*` values. The app will attempt calls to `/api/v1/...` on your FastAPI server. Until implemented, leave the frontend in `mock` mode.

### Proposed backend endpoints

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/api/v1/chats` | — | `ChatSession[]` (with messages) |
| POST | `/api/v1/chats` | `{}` | `ChatSession` |
| GET | `/api/v1/chats/{id}` | — | `ChatSession` |
| PATCH | `/api/v1/chats/{id}` | `{ "title": "..." }` | 200 JSON or 204 |
| DELETE | `/api/v1/chats/{id}` | — | 204 |
| POST | `/api/v1/chats/{id}/messages` | `{ "content": "..." }` | `Message` for assistant reply |
| GET | `/api/v1/me/settings` | — | `Settings` |
| PUT | `/api/v1/me/settings` | `Settings` | 200 JSON or 204 |

**Field contracts** (`lib/types.ts` is the authoritative source):

```typescript
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;             
  citations?: { title: string; url?: string; detail?: string }[];
}
interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[]; // ordered oldest → newest
  archived?: boolean;
}
interface Settings {
  theme: "light" | "dark" | "system";
  clinicianName: string;
  specialty: string;
  showDisclaimer: boolean;
  enterToSend: boolean;
}
```

Sample message POST reply:

```json
{
  "id": "message-uuid",
  "role": "assistant",
  "content": "Clinically reviewed response text ...",
  "createdAt": "2026-10-13T10:00:00Z",
  "citations": [{ "title": "Study title", "url": "https://pubmed.ncbi.nlm.nih.gov/..." }]
}
```

### Backend Work

Suggested tables are `users`, `chat_sessions` (`id`, `user_id`, `title`, `created_at`, `updated_at`), `messages` (`id`, `session_id`, `role`, `content`, `created_at`, `metadata`), `citations` (`id`, `message_id`, `title`, `url`, `detail`), and `user_settings` (`user_id`, preferences). Use foreign keys, session ownership checks, UTC timestamps, indexes on `(user_id, updated_at)` and `(session_id, created_at)`, and transactionally persist both halves of a response.

For very large histories, change `GET /chats` to return **summary records** with pagination, then fetch messages only via `GET /chats/{id}`. In that case, adjust `ChatRepository.listSessions` and the timeline to use a dedicated `/events` endpoint.

### Authentication, CORS, and protected health data

- The API adapter uses `credentials: "include"`, anticipating a secure HTTP-only session cookie. Choose a CSRF strategy, proper cookie SameSite/Secure settings, and restricted CORS allowlist. FastAPI needs `allow_credentials=True` and an explicit frontend origin (not `*`) if hosts are separate.
- Enforce authenticated **per-user ownership** on all conversation and settings endpoints. Never trust a client-provided session ID without an ownership check.
- Clinical answers require server-side retrieval, citation verification, safeguards, and clinician review.

### Future streaming support

Currently `sendMessage` returns a completed assistant `Message`. To support streaming via FastAPI SSE or a streamed HTTP response, extend the repository interface with `streamMessage(id, content, onChunk)` and update `ChatView` to display incremental assistant content. Keep transport concerns inside the repository adapter; do not embed raw `fetch()` calls directly in view components.
