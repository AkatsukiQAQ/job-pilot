# 技术栈与本地优先架构

> **AI 调研附录**（生成于 2026-09-16，英文）。内容由并行调研 agent 对照官方页面整理，verified/unverified 标注以原文为准；实现前需再次核对。相关更正见 japan-critique.md 与 proposal-judgments.md。

# Tech stack and architecture for a local-first, single-user job-hunting workbench (JobPilot) on Windows 11

## Summary
Everything the user wants is feasible with a single Python process serving a browser UI on http://127.0.0.1, with no job queue and no desktop shell. The decisive requirements are browser-native ones: microphone capture (getUserMedia / Web Speech API only work in a secure context such as http://localhost or http://127.0.0.1), token-streaming chat (SSE), and server-pushed realtime updates (SSE), which favor a real browser SPA (FastAPI + React/Vite 8) over Python-only UI frameworks; Streamlit is disqualified outright because its rerun model kills an in-progress st.write_stream the moment the user touches any widget, and its st.audio_input is record-then-submit only. Among Python-only options, NiceGUI 3.16 (built on FastAPI + Socket.IO, mountable on your own FastAPI app via ui.run_with) is the credible fallback: realtime and streaming are trivial, but microphone capture needs a custom Vue component or run_javascript plus a POST route. Backend: FastAPI 0.141 + SQLite via SQLAlchemy 2.0.54 typed declarative + Alembic 1.20 with render_as_batch=True (SQLite cannot ALTER constraints); SQLModel 0.0.42 works but is still 0.0.x, pins SQLAlchemy <2.1, and complicates FTS5/sqlite-vec virtual tables. Scheduling: APScheduler 3.11.3 AsyncIOScheduler started in the FastAPI lifespan; APScheduler 4 is still alpha (4.0.0a6, April 2025) and its own docs say do not use in production; Windows Task Scheduler is only useful for auto-starting the app at logon. Gmail is read-only by scope (gmail.readonly, a Google "restricted" scope) and synced by polling users.history.list (2 quota units per call; push notifications need Pub/Sub and a public endpoint, so they are out for local-first); the OAuth loopback flow on a Desktop-app client remains supported, but a consent screen in "Testing" status issues refresh tokens that expire every 7 days. LinkedIn has no official read API for individuals outside the EU (the DMA Member Data Portability API is EU-only), so the ToS-safe v1 sources are the official "Download your data" archive (Job Applications, Saved Jobs, Messages) plus LinkedIn notification emails already in Gmail. Secrets: keyring 25.7 (Windows Credential Manager) for short API keys only, because CredWrite fails on blobs observed as small as ~700 chars; store the Google token JSON as a DPAPI-encrypted file (pywin32 win32crypt). The LLM layer should be pydantic-ai 2.x (Agent("anthropic:claude-opus-5") vs Agent("openai:gpt-5.6-terra"), switchable by string, tools = plain Python functions over the service layer); Claude's Messages API accepts text/images/PDF but not audio, so voice must be transcribed first (browser Web Speech API for free, or MediaRecorder -> gpt-4o-mini-transcribe / local faster-whisper). Tooling: uv 0.12 packaged src layout with uv_build, ruff 0.16.7, pyright in CI (ty 0.0.81 is still beta), pytest + anyio, prek or pre-commit; one command (uv run jobpilot dev) runs uvicorn --reload plus the Vite dev server, and uv run jobpilot serves the built frontend from FastAPI StaticFiles.

## Hard constraints
  - Read-only guarantee must be structural: Gmail requests use only https://www.googleapis.com/auth/gmail.readonly (or gmail.metadata) - never gmail.modify/gmail.send/gmail.labels; if IMAP is used, only SELECT/EXAMINE, SEARCH, FETCH ... BODY.PEEK[] and IDLE (EXAMINE opens read-only); LLM tools registered with the agent must be limited to local DB reads/writes and UI commands - no connector exposes a write method at all.
  - LinkedIn: no official read API for individuals outside the EU; the DMA Member Data Portability API (scope r_dma_portability_self_serve) is EU-only; Voyager/scraping violates LinkedIn's User Agreement. v1 must rely on the official data archive and Gmail notifications.
  - Gmail realtime is polling-only in a local-first app: users.watch push notifications require Google Cloud Pub/Sub and a public endpoint. Use users.history.list(startHistoryId) (2 quota units) every 2-5 minutes; on HTTP 404 fall back to a full sync; historyIds are valid ~1 week.
  - Google OAuth for a personal desktop app: client type must be 'Desktop app'; redirect is http://127.0.0.1:{port} (loopback flow remains supported for Desktop clients; OOB removed); an external consent screen in 'Testing' status issues refresh tokens that expire in 7 days; max 100 refresh tokens per Google account per client ID; gmail.readonly is a 'restricted' scope.
  - Windows Credential Manager (keyring WinVaultKeyring) cannot reliably hold OAuth token JSON: documented cap 2560 UTF-16 chars, CredWrite failures observed at ~700 chars on Windows 11. Store large blobs DPAPI-encrypted on disk; catch pywintypes.error instead of silently falling back to plaintext.
  - Browser microphone requires a secure context: serve the UI at http://localhost or http://127.0.0.1 (both count as secure); a LAN IP over plain HTTP leaves navigator.mediaDevices undefined; recording must start from a user gesture. Web Speech API SpeechRecognition exists in Chrome/Edge (cloud-processed by default; Chrome 139+ can run on-device with processLocally=true after install()); Firefox lacks it.
  - Claude Messages API accepts text, images and PDFs - no audio input - so voice must be transcribed (browser Web Speech API, OpenAI gpt-4o-mini-transcribe/gpt-transcribe, or local faster-whisper) before reaching the chat agent.
  - APScheduler 4.x is pre-release (4.0.0a6, April 2025) with explicit 'do NOT use in production' warning; use APScheduler 3.11.3 (from apscheduler.schedulers.asyncio import AsyncIOScheduler).
  - SQLite ALTER TABLE only supports add/rename column; Alembic must run with render_as_batch=True (batch_alter_table copy-and-move) and a MetaData naming_convention so constraints are named.
  - Streamlit's rerun model terminates in-progress streams/background work on any widget interaction (issue #14524) - unsuitable for a chat + realtime tracker.
  - Python is pinned to 3.12: fine for every library here (faster-whisper/CTranslate2 does not yet support 3.13, so do not bump if local STT is planned).
  - Single user, single process: no job queue, no Redis; SQLite must run with PRAGMA journal_mode=WAL, busy_timeout=5000, foreign_keys=ON and connect_args={'check_same_thread': False} because uvicorn's threadpool and scheduler threads share the file.
  - sse-starlette EventSourceResponse does not work behind GZipMiddleware - do not add gzip globally.
  - uv 0.12+ makes the packaged src/ layout the default; the existing uv 0.10.7 scaffold has no [build-system] and must be converted (uv self update, add uv_build) before console scripts like `jobpilot` can work.

## Recommendation
v1 stack: uv 0.12 packaged project (src/jobpilot, uv_build backend, [project.scripts] jobpilot = "jobpilot.cli:main"); FastAPI 0.141 + uvicorn on 127.0.0.1:8765 with a lifespan that opens the SQLite engine, runs Alembic upgrade head, starts APScheduler 3.11.3 AsyncIOScheduler and an asyncio event broadcaster; SQLite (WAL) via SQLAlchemy 2.0.54 typed declarative + Alembic 1.20 (render_as_batch=True) with FTS5 for full-text over emails/postings/memory; pydantic-settings for config; Gmail connector = google-api-python-client 2.200 + google-auth-oauthlib 1.4.1 (Desktop client, run_local_server(host='127.0.0.1', port=0), scope gmail.readonly, incremental history.list sync every 3 min, token stored DPAPI-encrypted, API keys in keyring); LinkedIn connector = archive ZIP importer (Job Applications / Saved Jobs / Messages CSV) + Gmail notification-email parser; LLM = pydantic-ai 2.x Agent with model string from settings ('anthropic:claude-opus-5' default, 'openai:gpt-5.6-terra' alternate; use claude-haiku-4-5 / gpt-5.6-luna for bulk email classification), tools = query_pipeline, get_application, search_jobs_local, remember_fact, recall, and ui_command(navigate/filter/open) which the frontend executes; streaming over SSE (sse-starlette 3.4.11); UI = React 19 + TypeScript + Vite 8 + TanStack Query 5 (+ streamedQuery) + Tailwind 4 in frontend/, with a pipeline board/table, application detail with linked emails, and a chat panel whose push-to-talk button uses the Web Speech API (lang 'ja-JP'/'en-US' toggle) to fill the chat input, so voice commands are just chat messages that trigger tools. Memory v1 = memory_item table (kind: profile|preference|outcome|fact, text, source_chat_message_id, confidence) searchable via FTS5 and injected into the system prompt; job search v1 = local re-ranking of stored postings against memory + application history. One command: `uv run jobpilot dev` (spawns `npm run dev` with /api proxy and uvicorn --reload), `uv run jobpilot` for production (serves frontend/dist). Tooling: ruff 0.16.7 (check --fix + format), pyright in prek/pre-commit and CI, pytest + anyio + httpx ASGITransport, ty as optional editor checker. Defer to v2+: sqlite-vec 0.1.8 embeddings for memory/job relevance (hybrid FTS5+vec RRF), server-side STT fallback (MediaRecorder -> /api/voice/transcribe -> gpt-4o-mini-transcribe or faster-whisper) for browsers without Web Speech API or for offline use, external job-board connectors, auto-start at logon via schtasks and an Edge/Chrome --app= shortcut, IMAP IDLE as an alternative Gmail transport, and any desktop shell (Tauri/pywebview) only if a real installer is ever needed. Fallback: if the React toolchain slows you down in the first two weeks, mount NiceGUI 3.16 on the same FastAPI app with ui.run_with(app) and add a small custom Vue recorder component - the backend, DB, scheduler, connectors and agent are unchanged because all logic lives in jobpilot/services and is exposed through routers, not UI code.

## Options
### UI (a): FastAPI backend + React 19 / Vite 8 / TypeScript SPA (RECOMMENDED v1) [read_only_ok=True, cost=$0 (all OSS), effort=days, risk=none]
Single uvicorn process serves /api/* routers, /api/events (SSE), /api/chat (SSE token stream) and, in production, the built frontend from frontend/dist via StaticFiles(html=True). Dev: Vite dev server on :5173 proxies /api to :8765. Browser APIs (getUserMedia, MediaRecorder, SpeechRecognition, EventSource, fetch ReadableStream) are used directly from TypeScript.
Pros:
  - Best microphone/voice story: Web Speech API and MediaRecorder work natively at http://localhost / http://127.0.0.1 with no bridging
  - Chat streaming via sse-starlette 3.4.11 EventSourceResponse or fetch ReadableStream; TanStack Query 5 has experimental_streamedQuery for exactly this
  - The API layer is shared by UI, LLM tool-calls and CLI, so 'operate the app by voice' is just tools calling the same service functions
  - Largest component/ecosystem and LLM-assisted-coding coverage; Vite 8 ships React Compiler templates (react-compiler-ts); @vitejs/plugin-react v6
  - Backend stays UI-agnostic: NiceGUI can be mounted later on the same FastAPI app without touching services
Cons:
  - Two toolchains (uv + npm) and two languages to maintain alone
  - More initial boilerplate than NiceGUI (routing, query hooks, forms)
  - Vite 8 requires Node 20.19+/22.12+ (you have 22.17, OK)
### UI (b1): NiceGUI 3.16 mounted on the same FastAPI app (FALLBACK) [read_only_ok=True, cost=$0, effort=days, risk=none]
Python-only UI: Vue/Quasar frontend driven over Socket.IO (WebSocket, long-poll fallback), single uvicorn worker. ui.run_with(app) mounts it onto your FastAPI app so REST routers coexist. Requires fastapi!=0.123.5,>=0.109.1, starlette>=1.3.1, Python 3.10+.
Pros:
  - Zero JavaScript for dashboards, tables, chat bubbles; server can push element updates from background tasks at any time (realtime for free)
  - Streaming an LLM reply is a loop that appends to a ui.markdown
  - Same process, same FastAPI app, same SQLite; very high solo velocity for internal-tool style UIs
  - Optional native window via the 'native' extra (pywebview<7)
Cons:
  - No built-in microphone recorder: needs ui.run_javascript(getUserMedia+MediaRecorder) plus POSTing the Blob to a FastAPI route, or a custom Vue component (esm) - ~100 lines but bespoke
  - UI state lives server-side per connected client; UI unit-testing and layout control weaker than React
  - Quasar look-and-feel, fewer third-party components; FastAPI incompatibility incidents have happened (0.123.5 excluded)
  - Migrating away later means rewriting the UI layer
### UI (b2): Streamlit 1.63 [read_only_ok=True, cost=$0, effort=hours, risk=none]
Script-rerun model: the whole file reruns on every widget interaction.
Pros:
  - Fastest possible first dashboard
  - st.chat_message / st.write_stream / st.audio_input exist
Cons:
  - st.write_stream blocks the script thread and is killed if the user touches any widget mid-stream (open issue #14524, March 2026); workaround is disabling the UI while streaming
  - st.audio_input is record-then-submit and its value persists across reruns (issue #9600) - must guard re-processing; live mic needs streamlit-webrtc + STUN
  - Background sync + realtime board updates fight the rerun model; not suited to a long-lived tracker with voice commands
### UI (b3): Gradio 6.27 [read_only_ok=True, cost=$0, effort=days, risk=none]
Blocks API with gr.Chatbot, gr.Audio(sources='microphone', streaming=True) and .stream()/.stop_recording() events.
Pros:
  - Best out-of-the-box microphone streaming of any Python UI
  - Generator-based output streaming; HLS media streaming
Cons:
  - Demo/ML-app oriented; multi-view pipeline board, tables, filters and navigation are awkward
  - Queue/session semantics designed for shared demos, not a personal long-running workbench
  - Breaking changes across 5 -> 6 (allow_tags default, removed params)
### UI (b4): Reflex 0.9.x [read_only_ok=True, cost=$0, effort=days, risk=none]
Python State classes compile to a Next.js/React frontend + FastAPI backend; events/state diffs over WebSocket.
Pros:
  - Pure Python authoring with a real React output
  - Realtime state push is built in
Cons:
  - Needs Node at build time anyway, so you pay the toolchain cost without owning the React code
  - Every interaction round-trips over WebSocket; in-memory state manager (Redis recommended in prod)
  - Younger ecosystem, package split (reflex-base, components-core, enterprise) and frequent API churn
### UI (b5): Flet 0.86.5 (Flutter desktop) [read_only_ok=True, cost=$0, effort=days, risk=none]
Native Windows window rendered by Flutter; flet-audio-recorder service records from the mic (PCM16 streaming supported on all platforms); 1.0.0.dev0 preview exists.
Pros:
  - Real desktop app feel without a browser; mic recording works on Windows via flet-audio-recorder
  - Realtime updates trivial (page.update())
Cons:
  - Not a browser: no Web Speech API, so STT must be server/API side from day one
  - 1.0 is a moving target (dev preview Sept 2026); smaller component set for tables/charts
  - Harder to mix with FastAPI routers and to test
### UI (c): Textual 8.2.8 TUI [read_only_ok=True, cost=$0, effort=days, risk=none]
Terminal UI (also serveable in a browser via textual-serve).
Pros:
  - Very fast to build, testable, keyboard-driven
  - Chat streaming and live-updating tables are easy
Cons:
  - No microphone in a terminal: needs sounddevice + server-side STT
  - No rich rendering of emails/job pages; voice-driven navigation of a TUI is a poor fit
  - Would end up as a secondary client at best
### UI (d): Tauri 2 / pywebview 6.2 / Electron desktop shell around the web UI [read_only_ok=True, cost=$0, effort=weeks, risk=none]
Wrap the SPA in a WebView2 window; Python runs as a PyInstaller sidecar (Tauri) or in-process (pywebview, pytauri).
Pros:
  - Installer, tray icon, single-window feel
  - Tauri: small binary; pytauri avoids Rust; pywebview is Python-only
Cons:
  - WebView2 microphone permission is a known pain point: PermissionRequested may not fire for Microphone (WebView2Feedback #1462), a persisted Deny silences future prompts, so you must handle CoreWebView2.PermissionRequested (Rust/C#/pythonnet) for MICROPHONE
  - PyInstaller spec files, target-triple sidecar naming, child-PID kill issues for one-file exes
  - Zero functional gain for a single local user; a browser tab or Edge/Chrome --app=http://127.0.0.1:8765 gives a chromeless window for free
### DB layer: SQLAlchemy 2.0.54 typed declarative + Alembic 1.20 (RECOMMENDED) vs SQLModel 0.0.42 [read_only_ok=True, cost=$0, effort=hours, risk=none]
Plain SQLAlchemy Mapped[]/mapped_column models plus separate Pydantic v2 schemas; Alembic env.py with render_as_batch=True and a MetaData naming_convention. SQLModel merges model+schema in one class.
Pros:
  - SQLAlchemy 2.0: first-class JSON columns, FTS5/sqlite-vec virtual tables via raw DDL, mature Alembic autogenerate, no version ceiling
  - SQLModel: less boilerplate for simple CRUD, FastAPI-native docs
Cons:
  - SQLModel is 0.0.x, pins SQLAlchemy <2.1.0, needs 'import sqlmodel.sql.sqltypes' in script.py.mako for autogenerate, and gets in the way once models diverge from API schemas
  - SQLite needs Alembic batch mode (copy-and-move) for anything beyond add-column
### Scheduling: APScheduler 3.11.3 AsyncIOScheduler in the FastAPI lifespan (RECOMMENDED); no job queue [read_only_ok=True, cost=$0, effort=hours, risk=none]
Interval/cron jobs: gmail_incremental_sync every 2-5 min, linkedin_archive_watch (watch a drop folder), job_search_refresh hourly, memory_embed_backfill nightly. Sync google-api-python-client calls run via asyncio.to_thread or APScheduler's thread executor. Progress/results are published to an in-process asyncio broadcaster that feeds /api/events SSE.
Pros:
  - Single process, single user: no Redis/Celery/RQ needed
  - Misfire handling, coalescing, cron triggers; ZoneInfo timezones since 3.11
  - Plain asyncio.create_task loop is an acceptable even-simpler alternative for 2-3 jobs
Cons:
  - APScheduler 4 (AsyncScheduler API) is still 4.0.0a6 from April 2025 - do not use; tutorials mixing 3.x/4.x APIs are common
  - Jobs die with the process; use Windows Task Scheduler (schtasks /Create /SC ONLOGON) or the Startup folder only to auto-launch the server at logon, not for per-job scheduling
### Secrets: keyring (Windows Credential Manager) for API keys + DPAPI-encrypted file for OAuth token JSON (RECOMMENDED) [read_only_ok=True, cost=$0, effort=hours, risk=none]
keyring 25.7.0 WinVaultKeyring (pywin32-ctypes) for ANTHROPIC_API_KEY / OPENAI_API_KEY (short strings). Google token.json (access+refresh token, scopes) encrypted with win32crypt.CryptProtectData (pywin32 312) and written to %LOCALAPPDATA%\JobPilot\google_token.dpapi. .env (pydantic-settings) only for non-secret config.
Pros:
  - Per-user OS protection with no master password or key management
  - DPAPI has no size cap, unlike Credential Manager
  - Never silently falls back to plaintext if you catch pywintypes.error explicitly
Cons:
  - Credential Manager blob limit: documented 2560 UTF-16 chars, CredWrite observed failing at ~700 chars on Windows 11 - OAuth token blobs do not fit
  - pywin32 is Windows-only; wrap in a SecretStore protocol with an env/.env fallback for tests/CI
  - Alternative (envelope encryption: Fernet key in keyring, token file encrypted with it) is portable but more code
### Secrets: .env only (python-dotenv / pydantic-settings) [read_only_ok=True, cost=$0, effort=hours, risk=low]
Everything in a gitignored .env file.
Pros:
  - Simplest; fine for the first week
Cons:
  - Plaintext refresh token to a restricted-scope Gmail account on disk
  - Easy to leak via backups/screenshots/sync folders
### LLM layer: pydantic-ai 2.x with provider switch (RECOMMENDED) vs direct anthropic 1.6 / openai 3.14 SDKs [read_only_ok=True, cost=Usage-based: Claude Opus 5 $5/$25 per MTok, Sonnet 5 $2/$10, Haiku 4.5 $1/$5; OpenAI GPT-6 Astra $10/$50, GPT-5.6 Terra/Luna cheaper (verify live pricing), effort=days, risk=none]
Agent(model_string, tools=[...]) where model_string is 'anthropic:claude-opus-5' or 'openai:gpt-5.6-terra' (or gpt-6-astra); streaming via agent.run_stream; tools are typed Python functions over the service layer. pydantic-ai wraps the official SDKs underneath.
Pros:
  - Provider switch is a config string; one tool schema for both vendors
  - Streaming, tool loops, structured outputs, OTel tracing handled
  - Read-only guarantee is structural: the only tools registered are DB queries, UI commands and 'remember_fact'
Cons:
  - Extra abstraction; vendor-specific betas (Anthropic adaptive thinking/effort, fast mode) exposed via provider settings rather than natively
  - Direct SDKs give exact control (anthropic 1.x uses httpx2; adaptive thinking; SSE streaming helpers) at the cost of writing the tool loop twice
### Gmail access: Gmail REST API with OAuth Desktop client + loopback redirect (RECOMMENDED) [read_only_ok=True, cost=$0 (Gmail API free under the 80M units/day threshold), effort=days, risk=none]
google-auth-oauthlib 1.4.1 InstalledAppFlow.from_client_secrets_file(path, scopes=['https://www.googleapis.com/auth/gmail.readonly']).run_local_server(host='127.0.0.1', port=0). Full sync once (messages.list with q filter), then users.history.list(startHistoryId=...) every few minutes; 404 => full resync.
Pros:
  - Scope-enforced read-only (gmail.readonly or gmail.metadata; never gmail.modify)
  - history.list is 2 quota units; limits are 6,000 units/min/user and 1.2M/min/project - a single user cannot approach them
  - Loopback flow explicitly remains supported for Desktop app clients; OOB is gone
Cons:
  - gmail.readonly is a Google 'restricted' scope; consent screen in Testing status => refresh token expires every 7 days (re-consent) unless published
  - Push notifications (users.watch, Pub/Sub) need a public HTTPS endpoint - not local-first, so polling
  - Client secret of a Desktop client is not truly secret but must still stay out of git
### Gmail access alternative: IMAP with an App Password (imap.gmail.com:993) [read_only_ok=True, cost=$0, effort=days, risk=low]
Python imaplib/aioimaplib; Gmail IMAP extensions X-GM-RAW (Gmail search syntax), X-GM-THRID, X-GM-MSGID, X-GM-LABELS; IMAP IDLE for near-realtime. Read-only only if you fetch with BODY.PEEK[] (plain BODY[] sets \Seen) and never issue STORE/COPY/APPEND/EXPUNGE.
Pros:
  - No OAuth consent screen, no 7-day token expiry, no Cloud project; 16-char app password fits in Credential Manager
  - IDLE gives push-like latency without Pub/Sub
Cons:
  - Requires 2-Step Verification and App Passwords enabled (Workspace admins can disable them)
  - Read-only is by discipline, not by scope; mistakes (BODY[] instead of BODY.PEEK[]) mutate flags
  - No historyId; you track UIDVALIDITY/UIDs yourself
### LinkedIn v1 source: official 'Download your data' archive + LinkedIn notification emails in Gmail [read_only_ok=True, cost=$0, effort=hours, risk=none]
Import the ZIP's Job Applications (applied date, company, title, posting URL), Saved Jobs, Job Seeker Preferences, Saved Job Alerts and Messages (available within 10 min / 48 h). Watch a drop folder and re-import; dedupe by posting URL + date. Parse LinkedIn 'application sent' / recruiter emails from Gmail for near-realtime.
Pros:
  - 100% ToS-compliant and read-only
  - Archive can be requested as often as you like; job data arrives in ~10 minutes
  - Covers applied, saved and messaging history in one go
Cons:
  - Manual step (request + download) - not realtime; automation of the download itself would mean browser automation against LinkedIn (ToS risk)
  - Only what LinkedIn exports; no pipeline stage beyond 'applied'
### LinkedIn alternative: Member Data Portability (Member) API - EU accounts only [read_only_ok=True, cost=$0, effort=days, risk=low]
OAuth scope r_dma_portability_self_serve; Member Snapshot API (domains incl. job applications, saved jobs, messages) and Member Changelog API (28-day window). Available only to members registered in the EU under the DMA.
Pros:
  - Official, programmatic, read-only
Cons:
  - Not available to non-EU accounts (user appears Japan-based); no official self-serve API otherwise
  - Unofficial Voyager clients/scrapers violate the User Agreement and get accounts banned - excluded

## Concrete details
  - Pinned current versions (verified on PyPI 2026-09-16): fastapi 0.141.1 (starlette>=0.46, pydantic>=2.9), uvicorn[standard], sqlalchemy 2.0.54, alembic 1.20.0, sqlmodel 0.0.42 (sqlalchemy<2.1, pydantic>=2.11), sse-starlette 3.4.11, apscheduler 3.11.3 (4.0.0a6 alpha - avoid), nicegui 3.16.0 (fastapi!=0.123.5,>=0.109.1; starlette>=1.3.1), gradio 6.27.0, streamlit 1.63.0, textual 8.2.8, flet 0.86.5 (+flet-audio-recorder 1.0.0.dev0), pywebview 6.2.1, anthropic 1.6.0 (depends on httpx2, not httpx), openai 3.14.1, pydantic-ai 2.32.x, keyring 25.7.0 (pywin32-ctypes on win32), pywin32 312, google-api-python-client 2.200.0, google-auth-oauthlib 1.4.1 (repo archived, now maintained in google-cloud-python; Python>=3.10), sqlite-vec 0.1.8, ruff 0.16.7, ty 0.0.81 (beta), uv 0.12.15, Vite 8 (Node 20.19+/22.12+), @vitejs/plugin-react v6.
  - uv conversion of the existing scaffold: `uv self update`; add to pyproject.toml: [build-system] requires = ["uv_build>=0.12.15,<0.13"] build-backend = "uv_build"; [project.scripts] jobpilot = "jobpilot.cli:main"; create src/jobpilot/__init__.py; [dependency-groups] dev = ["pytest","anyio","httpx","ruff","pyright","respx"]; `uv add fastapi uvicorn[standard] sqlalchemy alembic pydantic-settings sse-starlette apscheduler platformdirs keyring pywin32 google-api-python-client google-auth-oauthlib pydantic-ai-slim[anthropic,openai]`.
  - Repo layout: JobPilot/ pyproject.toml, uv.lock, alembic.ini, .env.example, .pre-commit-config.yaml (or prek.toml), src/jobpilot/{cli.py, app.py (create_app + lifespan), settings.py, db/{engine.py, base.py (MetaData naming_convention), models.py, migrations/ (alembic env.py with render_as_batch=True)}, api/{applications.py, jobs.py, emails.py, chat.py, events.py, voice.py, memory.py, sync.py}, services/{pipeline.py, gmail/{auth.py, sync.py, classify.py}, linkedin/archive.py, llm/{agent.py, tools.py, providers.py}, memory/{store.py, fts.py}, search/rank.py, events.py (broadcaster), scheduler.py}, secrets/{store.py (Protocol), windows.py (keyring+DPAPI), env.py}}, frontend/{package.json, vite.config.ts (server.proxy '/api' -> http://127.0.0.1:8765), src/}, tests/.
  - Runtime paths: data dir via platformdirs.user_data_dir('JobPilot') => %LOCALAPPDATA%\JobPilot\ with jobpilot.db, google_token.dpapi, client_secret.json, imports/ (LinkedIn ZIP drop folder).
  - SQLite engine: create_engine('sqlite:///.../jobpilot.db', connect_args={'check_same_thread': False}) + event listener executing PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON. Verify extension support once: hasattr(sqlite3.Connection, 'enable_load_extension') and `SELECT sqlite_version()` / `PRAGMA compile_options` includes ENABLE_FTS5 (python.org Windows builds normally do).
  - Schema suggestion (SQLAlchemy models): company(id, name, domain, notes); job_posting(id, source ENUM[linkedin_archive,gmail,manual,search], external_id, url UNIQUE, title, company_id FK, location, remote_type, salary_min, salary_max, currency, description_text, posted_at, fetched_at, hash); application(id, job_posting_id FK, stage ENUM[potential,saved,applied,screening,interview,offer,rejected,withdrawn,accepted], applied_at, last_activity_at, outcome, outcome_reason, notes, created_at, updated_at); application_event(id, application_id FK, kind ENUM[email,status_change,note,interview,archive_import], occurred_at, summary, email_message_id FK NULL, payload JSON); email_message(id TEXT PK (Gmail id), thread_id, history_id INTEGER, internal_date, from_addr, to_addr, subject, snippet, body_text, labels JSON, classified_kind, application_id FK NULL, fetched_at); sync_state(source PK TEXT, cursor TEXT (Gmail historyId / archive file hash), last_success_at, last_error, status); memory_item(id, kind ENUM[profile,preference,outcome,fact,constraint], text, structured JSON, source_chat_message_id FK NULL, confidence REAL, created_at, superseded_by FK NULL); chat_session(id, created_at, model, title); chat_message(id, session_id FK, role, content, tool_calls JSON, created_at, input_mode ENUM[text,voice]); search_query(id, query_text, filters JSON, executed_at, provider); search_result(id, search_query_id FK, job_posting_id FK, rank, score, seen, dismissed). Virtual tables: email_fts USING fts5(subject, body_text, content='email_message', content_rowid='rowid') with sync triggers; memory_fts likewise; v2: memory_vec USING vec0(embedding float[768]) keyed by memory_item rowid.
  - API surface: GET /api/applications?stage=, GET /api/applications/{id}, PATCH /api/applications/{id} (local only), GET /api/jobs, POST /api/imports/linkedin (multipart ZIP), POST /api/sync/gmail (trigger now), GET /api/sync/state, GET /api/events (SSE: event types sync.progress, application.updated, email.new, ui.command), POST /api/chat/{session_id}/messages -> SSE stream (event types token, tool_call, tool_result, ui_command, done), POST /api/voice/transcribe (multipart webm/opus -> {text}), GET/POST /api/memory, GET /api/settings/llm (provider/model switch), POST /api/auth/google/start (runs loopback flow in a thread, returns when done).
  - Gmail: scope https://www.googleapis.com/auth/gmail.readonly (restricted) or https://www.googleapis.com/auth/gmail.metadata (restricted, headers/labels only, no q= search on messages.list). Endpoints: GET /gmail/v1/users/me/messages?q=newer_than:180d (full sync), GET /gmail/v1/users/me/messages/{id}?format=full (20 units), GET /gmail/v1/users/me/history?startHistoryId=X&historyTypes=messageAdded (2 units; 404 => full sync). Quotas: 6,000 units/min/user/project, 1,200,000 units/min/project, 80M units/day free threshold. Python: InstalledAppFlow.from_client_secrets_file(path, scopes).run_local_server(host='127.0.0.1', port=0, open_browser=True, timeout_seconds=300) - port=0 picks a free port and the redirect URI is built from it; Desktop-app clients accept loopback redirects without registering the URI.
  - Google Cloud setup: create project, enable Gmail API, OAuth consent screen External + Testing with your own account as test user (7-day refresh expiry; re-run the flow when invalid_grant), create 'Desktop app' OAuth client, download client_secret.json into %LOCALAPPDATA%\JobPilot.
  - Secrets code path: keyring.set_password('jobpilot', 'anthropic_api_key', key) / get_password; token blob: win32crypt.CryptProtectData(json_bytes, 'jobpilot-google-token', None, None, None, 0) -> write; CryptUnprotectData(blob, None, None, None, 0)[1] -> read. Wrap in SecretStore Protocol with EnvSecretStore fallback (JOBPILOT_SECRETS_BACKEND=env) for tests.
  - LinkedIn archive: Settings & Privacy -> Data privacy -> Get a copy of your data -> select 'Job Applications', 'Saved Jobs', 'Job Seeker Preferences', 'Saved Job Alerts', 'Messages' (or full archive); job files ready in ~10 min, messages within 48 h; download link valid 72 h. Job Applications fields: application date, company name, job title, LinkedIn job posting URL. Dedupe on posting URL.
  - LLM: pydantic-ai Agent(settings.llm_model, system_prompt=..., tools=[...]); model strings 'anthropic:claude-opus-5', 'anthropic:claude-sonnet-5', 'anthropic:claude-haiku-4-5', 'openai:gpt-6-astra', 'openai:gpt-5.6-sol', 'openai:gpt-5.6-terra', 'openai:gpt-5.6-luna'. If using the anthropic SDK directly: client.messages.stream(model='claude-opus-5', max_tokens=64000, thinking={'type':'adaptive'}, ...). Anthropic list prices: Opus 5 $5/$25 per MTok, Sonnet 5 $2/$10, Haiku 4.5 $1/$5.
  - Voice: browser const R = window.SpeechRecognition || window.webkitSpeechRecognition; r.lang='ja-JP'|'en-US'; r.interimResults=true; optional on-device: await SpeechRecognition.available({langs:['en-US'], processLocally:true}) then install(); result text -> POST /api/chat. Fallback path: navigator.mediaDevices.getUserMedia({audio:true}) -> MediaRecorder(mimeType 'audio/webm;codecs=opus') -> POST /api/voice/transcribe -> OpenAI audio.transcriptions.create(model='gpt-4o-mini-transcribe' | 'gpt-transcribe' | 'gpt-4o-transcribe' | 'whisper-1') (approx $0.003 / $0.0045 / $0.006 per minute - verify at platform.openai.com/pricing) or local faster-whisper (CTranslate2, needs ffmpeg; Python 3.10-3.12).
  - Realtime: sse-starlette EventSourceResponse(async_gen()) at /api/events with ping every 15 s; frontend new EventSource('/api/events'); Vite proxy passes SSE through (no compression). Use WebSocket only if barge-in (interrupting generation) is later required.
  - One-command run: cli.py (typer or argparse) with subcommands `serve` (uvicorn.run(app, host='127.0.0.1', port=8765) + webbrowser.open), `dev` (subprocess.Popen(['npm','run','dev'], cwd='frontend', shell=True on Windows) + uvicorn reload=True), `sync gmail`, `import linkedin <zip>`, `db upgrade`. Production: FastAPI app.mount('/', StaticFiles(directory='frontend/dist', html=True)) registered after API routers. Auto-start: schtasks /Create /SC ONLOGON /TN JobPilot /TR "<repo>\.venv\Scripts\jobpilot.exe serve"; chromeless window: msedge --app=http://127.0.0.1:8765.
  - Tooling config: [tool.ruff] line-length=100, target-version='py312'; [tool.ruff.lint] select=['E','F','I','UP','B','SIM','ASYNC'] (Ruff 0.16 enables 413 rules by default - set select explicitly); [tool.pyright] venvPath='.', venv='.venv', pythonVersion='3.12', typeCheckingMode='standard'; [tool.pytest.ini_options] testpaths=['tests'], anyio_mode or asyncio_mode='auto'; pre-commit/prek repos: astral-sh/ruff-pre-commit (ruff-check --fix, ruff-format), local hook `uv run pyright`; install prek with `uv tool install prek` (drop-in for .pre-commit-config.yaml, builds Python hook envs with uv).
  - Frontend deps: react 19, react-dom, typescript, vite 8, @vitejs/plugin-react 6, @tanstack/react-query 5 (experimental_streamedQuery), react-router or @tanstack/react-router, tailwindcss 4, optional shadcn/ui; create with `npm create vite@latest frontend -- --template react-ts`.

## Open questions
  - Which Gmail account receives job mail: a personal gmail.com account (App Passwords possible; consent screen must be External) or a Google Workspace account (Internal consent screen avoids verification and the 7-day Testing expiry, but admins may block restricted scopes and App Passwords)?
  - Is the user willing to re-authorize Google every 7 days (Testing status), or should the consent screen be published to production (unverified restricted-scope app: warning screen, still usable for the owner) - confirm current Google policy for gmail.readonly on an unverified single-user app?
  - Is the LinkedIn account registered in the EU? If not, the DMA Member Data Portability API is unavailable and the archive-import approach is the only official path.
  - Primary browser: Chrome or Edge (Web Speech API works; Edge has reported reliability issues) vs Firefox (no SpeechRecognition => server-side STT required from v1)?
  - Language mix: Japanese and English emails/postings/voice? Affects SpeechRecognition lang, STT model choice, FTS5 tokenizer (trigram for CJK) and the embedding model for v2 (multilingual-e5 or provider embeddings).
  - Is a GPU available for local faster-whisper, or is cloud STT (OpenAI) acceptable given audio leaves the machine?
  - Does the python.org 3.12 interpreter in .venv expose sqlite3 enable_load_extension and FTS5 (one-line check) - required for sqlite-vec in v2?
  - Monthly LLM budget and preferred default provider (Claude Opus 5 vs Sonnet 5 vs GPT-5.6 Terra) - affects which model handles bulk email classification vs chat.
  - Should the app auto-start at logon and run persistently (Task Scheduler), or be launched on demand?
  - Which job boards/sources should the v2 job search cover (LinkedIn job search has no official API; Indeed/Wantedly/company ATS pages have varying ToS) - separate research item.
  - React SPA (recommended) or NiceGUI fallback for v1 - the user's appetite for maintaining a TypeScript frontend alone decides this.

## Sources
- NiceGUI on PyPI (3.16.0, dependency pins): https://pypi.org/project/nicegui/
- NiceGUI - Technological Foundations (FastAPI, Socket.IO, ui.run_with): https://nicegui.io/documentation/section_foundations
- NiceGUI discussion #569 - recording microphone audio via run_javascript: https://github.com/zauberzeug/nicegui/discussions/569
- Streamlit issue #14524 - rerun-resilient st.write_stream: https://github.com/streamlit/streamlit/issues/14524
- Streamlit st.audio_input docs: https://docs.streamlit.io/develop/api-reference/widgets/st.audio_input
- Gradio Audio component docs (sources, streaming): https://gradio.app/docs/gradio/audio
- Gradio on PyPI (6.27.0): https://pypi.org/project/gradio/
- Reflex - How Reflex Works: https://reflex.dev/docs/advanced-onboarding/how-reflex-works/
- Flet AudioRecorder service docs: https://flet.dev/docs/services/audiorecorder/
- flet-audio-recorder on PyPI: https://pypi.org/project/flet-audio-recorder/1.0.0.dev0/
- Textual on PyPI (8.2.8): https://pypi.org/project/textual/
- Tauri v2 + Python FastAPI sidecar example: https://github.com/dieharders/example-tauri-v2-python-server-sidecar
- PyTauri: https://github.com/pytauri/pytauri
- WebView2Feedback #1462 - PermissionRequested not fired for Microphone: https://github.com/MicrosoftEdge/WebView2Feedback/issues/1462
- pywebview on PyPI (6.2.1): https://pypi.org/project/pywebview/
- MDN - MediaDevices.getUserMedia (secure context): https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- MDN - Web Speech API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
- MDN - SpeechRecognition.processLocally: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/processLocally
- sse-starlette on PyPI (3.4.11): https://pypi.org/project/sse-starlette
- FastAPI on PyPI (0.141.1): https://pypi.org/project/fastapi/
- FastAPI release notes: https://fastapi.tiangolo.com/release-notes/
- SQLModel on PyPI (0.0.42): https://pypi.org/project/sqlmodel/
- SQLAlchemy on PyPI (2.0.54): https://pypi.org/project/sqlalchemy/
- Alembic - Running Batch Migrations for SQLite: https://alembic.sqlalchemy.org/en/latest/batch.html
- Alembic on PyPI (1.20.0): https://pypi.org/project/alembic/
- APScheduler on PyPI (3.11.3 stable; 4.0.0a6 pre-release): https://pypi.org/project/APScheduler/
- APScheduler - Migrating from previous versions (4.x warning): https://apscheduler.readthedocs.io/en/master/migration.html
- keyring Windows backend source (WinVaultKeyring): https://github.com/jaraco/keyring/blob/main/keyring/backends/Windows.py
- keyring on PyPI (25.7.0): https://pypi.org/project/keyring/
- Credential Manager blob-size failures with keyring (CredWrite ~700 chars) - issue report: https://github.com/robcerda/monarch-mcp-server/issues/80
- pywin32 on PyPI (312): https://pypi.org/project/pywin32/
- Google - OAuth 2.0 for iOS & Desktop Apps (loopback, PKCE): https://developers.google.com/identity/protocols/oauth2/native-app
- Google - Loopback IP address flow migration guide (Desktop clients still supported): https://developers.google.com/identity/protocols/oauth2/resources/loopback-migration
- Google - Using OAuth 2.0 (refresh token expiration, Testing = 7 days, 100-token limit): https://developers.google.com/identity/protocols/oauth2
- Gmail API scopes (gmail.readonly / gmail.metadata are restricted): https://developers.google.com/workspace/gmail/api/auth/scopes
- Gmail API - Synchronize clients (history.list, 404 => full sync): https://developers.google.com/workspace/gmail/api/guides/sync
- Gmail API - users.history.list reference: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list
- Gmail API - Usage limits: https://developers.google.com/workspace/gmail/api/reference/quota
- Gmail IMAP extensions (X-GM-RAW, X-GM-THRID, X-GM-LABELS): https://developers.google.com/workspace/gmail/imap/imap-extensions
- google-auth-oauthlib flow reference (run_local_server parameters): https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html
- google-auth-oauthlib on PyPI (1.4.1): https://pypi.org/project/google-auth-oauthlib/
- google-api-python-client on PyPI (2.200.0): https://pypi.org/project/google-api-python-client/
- LinkedIn Member Data Portability (Member) API - Microsoft Learn: https://learn.microsoft.com/en-us/linkedin/dma/member-data-portability/member-data-portability-member/
- LinkedIn Help - Download your account data (archive categories): https://www.linkedin.com/help/linkedin/answer/a1339364
- uv - Creating projects (packaged src layout default): https://docs.astral.sh/uv/concepts/projects/init/
- uv - The uv build backend: https://docs.astral.sh/uv/concepts/build-backend/
- uv on PyPI (0.12.15): https://pypi.org/project/uv/
- Ruff on PyPI (0.16.7): https://pypi.org/project/ruff/
- Astral - Ruff v0.16.0 (413 default rules): https://astral.sh/blog/ruff-v0.16.0
- ty releases (0.0.81, beta): https://github.com/astral-sh/ty/releases
- Astral - ty announcement/roadmap: https://astral.sh/blog/ty
- prek - Rust pre-commit replacement: https://github.com/j178/prek
- ruff-pre-commit (prek.toml example): https://github.com/astral-sh/ruff-pre-commit
- Vite 8.0 announcement: https://vite.dev/blog/announcing-vite8
- TanStack Query - streamedQuery: https://tanstack.com/query/v5/docs/reference/streamedQuery
- Pydantic AI docs: https://ai.pydantic.dev/
- Pydantic AI releases (2.32.x): https://github.com/pydantic/pydantic-ai/releases
- anthropic on PyPI (1.6.0, httpx2): https://pypi.org/project/anthropic/
- openai on PyPI (3.14.1): https://pypi.org/project/openai/
- OpenAI API models (gpt-6-astra, gpt-5.6-*, transcription models): https://developers.openai.com/api/docs/models
- sqlite-vec hybrid search with FTS5 (Alex Garcia): https://alexgarcia.xyz/blog/2024/sqlite-vec-hybrid-search/index.html
- sqlite-vec repository: https://github.com/asg017/sqlite-vec
