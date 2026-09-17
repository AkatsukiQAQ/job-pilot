# 对话、语音与 LLM 统一层

> **AI 调研附录**（生成于 2026-09-16，英文）。内容由并行调研 agent 对照官方页面整理，verified/unverified 标注以原文为准；实现前需再次核对。相关更正见 japan-critique.md 与 proposal-judgments.md。

# Chat + voice layer for JobPilot: switchable Claude/GPT chat box that answers job questions from the local DB and executes app operations by voice, with mandatory confirmation for local mutations and a by-construction block on external writes

## Summary
Everything requested is feasible, and the cheapest reliable v1 requires no custom chat UI: package JobPilot's tracker/memory/search as a local stdio MCP server (official `mcp` Python SDK 2.2.0, Python 3.10+) and use existing desktop clients as the chat surface. Claude Desktop for Windows spawns local stdio servers from `%APPDATA%\Claude\claude_desktop_config.json`, Claude Code adds them with `claude mcp add --transport stdio <name> -- <cmd>` (Windows needs `cmd /c` for npx), and OpenAI's Codex CLI/desktop adds them with `codex mcp add <name> -- <cmd>` (config.toml `[mcp_servers.<name>]`), so "Claude or GPT, switchable" is achieved in v1 simply by opening a different host against the same server. ChatGPT itself cannot launch local stdio servers: it needs a public HTTPS Streamable-HTTP endpoint or OpenAI's Secure MCP Tunnel (tunnel-client, `--mcp-command` for stdio) in Developer mode, which OpenAI documents as web-only and tied to Platform-org tunnel permissions, so treat ChatGPT as an optional v1b. Voice in v1 is also zero-code: Claude Desktop voice mode is available on desktop on all plans and can use connected tools, Windows 11 Win+H voice typing (Azure online, zh-CN/zh-TW/ja/en) dictates into any text box including Claude Desktop, and Claude Code `/voice` push-to-talk works on native Windows (Japanese supported, Chinese is not in its dictation list; requires claude.ai login, audio goes to Anthropic). The read-only constraint must be enforced structurally, not by prompt: the connectors package exposes only fetch functions, the MCP/LLM tool registry is a static allowlist with no network-write code path, and local-state changes go through a two-phase `propose_*` -> `confirm_action(action_id)` protocol backed by a `pending_actions` table, with the host's per-tool approval prompt (Claude Desktop/Claude Code/Codex all have one) as a second gate. For v2 (custom UI with in-app provider switching), Pydantic AI 2.43.0 is the best fit among the abstractions compared: `Agent('anthropic:claude-sonnet-5')` / `agent.run_sync(prompt, model='openai:<id>')` for switching, `@agent.tool(requires_approval=True)` + `DeferredToolRequests`/`DeferredToolResults(approvals={call_id: True|ToolDenied(...)})` for a real pause-and-confirm loop, tool-mode structured output that works identically on both providers, Anthropic cache control via `AnthropicModelSettings(anthropic_cache_instructions=..., anthropic_cache_tool_definitions=...)`, and native MCP client support so the v1 server is reused. A thin adapter over the official SDKs (anthropic 1.6.0 on httpx2, openai 3.14.1 Responses API) is the runner-up if you want zero framework dependency; LiteLLM, LangChain/LangGraph and the OpenAI Agents SDK add weight or lose provider-native features for a one-user app. For v2 speech, start with browser push-to-talk via the Web Speech API in Chrome (free, cloud-based by default, supports zh/ja/en tags, requires HTTPS or localhost; on-device mode needs Chrome 142+ and per-language packs, and Edge's on-device model is Canary/Dev-only with no zh/ja yet), upgrade to OpenAI `gpt-transcribe` ($0.0045/min, `POST /v1/audio/transcriptions`, `languages` hint) when accuracy matters, and use local faster-whisper 1.2.1 (CPU int8) only if offline/privacy is required. Wake words are not recommended (openWakeWord's pretrained models are English-only and CC BY-NC-SA; custom training needed) and always-on realtime STT (`gpt-live-transcribe` $0.017/min) is unnecessary for command-style usage. TTS is optional: browser `speechSynthesis`/Windows SAPI via pyttsx3 is free and offline, OpenAI `gpt-4o-mini-tts` is $12/1M chars, and Kokoro (82M params, Apache-2.0, ja + zh) is the local upgrade.

## Hard constraints
  - External read-only must hold by construction: the `jobpilot.connectors.*` package exposes only fetch/list/get functions (Gmail scope `https://www.googleapis.com/auth/gmail.readonly`); the LLM/MCP tool registry is a static allowlist built from `jobpilot.tools.readonly` and `jobpilot.tools.local_mutations`; no registered tool imports any network client with write methods; a unit test asserts every tool's declared `side_effect` is `none` or `local_db` and that connectors expose no send/post/label/delete/apply/message symbols.
  - Any tool that mutates local state must be two-phase: `propose_*` writes a row to `pending_actions` and returns `{action_id, summary, diff}`; only `confirm_action(action_id)` applies it; proposals expire (e.g. 10 min) and confirmation must come from outside the LLM in v2 (UI click or a deterministic keyword match on the transcript), with Pydantic AI `requires_approval=True` -> `DeferredToolRequests` as the implementation; in v1 the host's per-tool approval prompt is the outer gate.
  - Grounding: the model never receives the whole DB. Answers come from bounded retrieval tools (`search_applications(query, status, company, since, limit<=20)`, `get_application(id)`, `search_memory(query, kind, limit<=10)`, `get_profile()`) that return compact JSON with stable ids; the system prompt instructs the model to cite ids and to answer 'not in the tracker' when tools return nothing.
  - ChatGPT cannot spawn local stdio MCP servers; it needs a public HTTPS Streamable-HTTP `/mcp` endpoint or OpenAI Secure MCP Tunnel, and Developer mode is documented as web-only ('Available to Pro, Plus, Business, Enterprise, and Education accounts on the web') with tunnel permissions tied to an OpenAI Platform organization.
  - Claude Desktop (Windows) loads stdio servers only from `%APPDATA%\Claude\claude_desktop_config.json` (`mcpServers.<name>.command/args/env`), requires a full app restart after edits, needs absolute paths, and logs to `%APPDATA%\Claude\logs\mcp.log` and `mcp-server-<NAME>.log`; on Windows, npx-based servers may need `cmd /c` (Claude Code) or an explicit `APPDATA` env entry.
  - Claude Code `/voice` dictation requires a claude.ai login (not an API key), streams audio to Anthropic, supports Japanese (`ja`) but Chinese is absent from its supported-language list; it is dictation only (no spoken replies).
  - Browser Web Speech API: only works in a secure context (HTTPS or http://localhost); Chrome's default engine sends audio to Google's servers; the constructor is `webkitSpeechRecognition` in Chrome; on-device (`processLocally=true`) needs Chrome 142+ (139 shipped, disabled in 140-141) and a downloaded language pack per language; Edge's on-device model exists only in Canary/Dev 150.0.4076+ behind an `edge://flags` entry and supports en/de/it/pt/es/ko only.
  - Windows 11 Win+H voice typing uses online Azure speech (needs internet), supports Chinese Simplified/Traditional, Japanese, and English, and types into any focused text box; it is a legitimate zero-code v1 voice input for Claude Desktop/Codex.
  - Anthropic API specifics the adapter must respect: always `json`-parse `tool_use.input`; Claude Fable 5.1 returns 400 on `tool_choice` `any`/`tool` (use `auto` + `strict: true`); prompt caching minimum cacheable prefix is model-dependent (512 tokens Opus 5/Fable 5.1, 1024 Sonnet 5, 4096 Haiku 4.5) and is silently skipped below the minimum; `anthropic` 1.x depends on `httpx2`, not `httpx`, so passing `httpx.Client`/`httpx.Timeout` objects fails.
  - OpenAI API specifics: use the Responses API (`client.responses.create/parse`) for new code; Chat Completions remains supported but the Assistants API was sunset on 2026-08-26 and must not be targeted; function tools are flat (`{type:'function', name, parameters, strict}`), calls arrive as `function_call` items with `call_id` and JSON-string `arguments`, results return as `function_call_output`; prompt caching is automatic with a 1,024-token minimum and `usage.input_tokens_details.cached_tokens` reporting.
  - Model IDs must come from config, not code, and be taken from official pages: Claude `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`, `claude-fable-5-1` (platform.claude.com models overview, 2026-09); OpenAI `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-6-astra` (developers.openai.com/api/docs/models, 2026-09); STT `gpt-transcribe`, `gpt-live-transcribe`, `whisper-1`; TTS `gpt-4o-mini-tts`.
  - MCP: implement with the official `mcp` Python SDK 2.x rather than hand-rolled JSON-RPC; the current spec revision 2026-07-28 removed the initialize handshake and sessions, added `server/discover`, deprecated Roots/Sampling/Logging, and asks servers to return `tools/list` in deterministic order (prompt-cache friendly). Tool annotations (`readOnlyHint`, `destructiveHint`) are hints only and are treated as untrusted by hosts; they do not replace the propose/confirm design.
  - Push-to-talk, not wake word, for v1/v2: openWakeWord's pretrained models are English-only and CC BY-NC-SA 4.0; an always-on microphone is out of scope.

## Recommendation
v1 (days): Build `jobpilot` as a uv-managed Python package with a SQLite DB and a `jobpilot-mcp` console script using the official `mcp` SDK 2.2.0 over stdio. Expose read-only tools (`search_applications`, `get_application`, `list_pipeline(status)`, `search_memory`, `get_profile`, `search_jobs(query, filters)`, `get_sync_status`) and two-phase mutation tools (`propose_status_update`, `propose_memory_fact`, `propose_profile_update`, `confirm_action(action_id)`, `cancel_action(action_id)`, `list_pending_actions`). Register the server in Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`), Claude Code (`claude mcp add --transport stdio jobpilot -- uv run --directory D:\Personal_Projects\JobPilot jobpilot-mcp`, scope user), and Codex (`codex mcp add jobpilot -- uv run --directory D:\Personal_Projects\JobPilot jobpilot-mcp`, `default_tools_approval_mode = "prompt"`). This gives Claude and GPT chat UIs immediately and provider switching by choosing the host. Voice in v1: Claude Desktop voice mode (test whether it calls the local MCP tools), Win+H dictation into Claude Desktop/Codex (covers zh/ja/en), and Claude Code `/voice` for ja/en. Do not write any LLM SDK code, STT code, or UI in v1. Also ship an MCP prompt (`@mcp.prompt jobpilot_briefing`) that instructs the model to answer only from tool results and to cite application ids.

v2 (weeks, incremental): Add a local web UI (Gradio first; FastAPI + small JS page if you need a custom PTT widget) backed by Pydantic AI 2.43 (`pydantic-ai-slim[openai,anthropic,mcp]`). Register the same Python functions in a `FunctionToolset`; mark mutating functions `requires_approval=True`; set `output_type=[str, DeferredToolRequests]`; render pending approvals as confirm cards and resume with `DeferredToolResults(approvals=...)`. Provider dropdown maps to `model='anthropic:claude-sonnet-5'` (default, cheapest good Claude) / `'anthropic:claude-opus-5'` / `'openai:<gpt id from config>'`; enable `AnthropicModelSettings(anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True)`. Persist `message_history` per session in SQLite. Voice: browser push-to-talk via `webkitSpeechRecognition` in Chrome as the default (free), with an OpenAI `gpt-transcribe` clip fallback toggle ($0.0045/min) and `keywords` seeded from company names in the DB; TTS off by default, browser `speechSynthesis` for confirmations. Add a memory-extraction step after each assistant turn that proposes `memory_facts` (never auto-commits) so the memory system also flows through confirm. Defer to v3+: local faster-whisper/Kokoro for offline mode, ChatGPT via Secure MCP Tunnel, wake word, realtime streaming STT, LangGraph-style multi-agent orchestration.

## Options
### v1: Local stdio MCP server + Claude Desktop / Claude Code / Codex as the chat UI [read_only_ok=True, cost=$0 beyond existing Claude/ChatGPT/Codex subscriptions; local compute only, effort=days, risk=none]
Implement JobPilot core as a Python package (SQLite DB) and expose it with the official `mcp` SDK (FastMCP-style `@mcp.tool` decorators, `mcp.run(transport='stdio')`). Register the server in Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json` -> `mcpServers.jobpilot.command='uv'`, `args=['run','--directory','D:\Personal_Projects\JobPilot','jobpilot-mcp']`), in Claude Code (`claude mcp add --transport stdio jobpilot -- uv run --directory D:\Personal_Projects\JobPilot jobpilot-mcp`), and in Codex (`codex mcp add jobpilot -- uv run ...`). Claude-vs-GPT switching = choosing the host. Voice = Claude Desktop voice mode, Win+H dictation, or Claude Code `/voice`.
Pros:
  - No chat UI, no LLM SDK, no API keys or token billing in your own code (uses the host's subscription)
  - Provider switching for free: same server, three hosts (Claude Desktop, Claude Code, Codex CLI/desktop)
  - Every host already prompts the user per tool call, giving a second confirmation gate on top of propose/confirm
  - The MCP server is reused unchanged in v2 (Pydantic AI, Anthropic tool runner `anthropic.lib.tools.mcp`, and OpenAI Agents SDK `MCPServerStdio` all consume stdio servers)
  - Claude Desktop stores sensitive config values in Windows Credential Manager; logs at `%APPDATA%\Claude\logs\mcp-server-jobpilot.log`
Cons:
  - No control over the system prompt or model settings beyond tool descriptions and MCP prompts
  - Voice-to-tool path in Claude Desktop voice mode is documented for 'connected tools' (Gmail, Calendar, etc.); invocation of local stdio MCP tools from voice mode is not explicitly documented and must be tested
  - Claude Desktop must be fully restarted after config edits; MCP in Desktop has historically been labeled beta
  - Claude Code dictation supports ja but not zh; Win+H requires internet (Azure) and is dictation only, no spoken replies
  - No custom memory-extraction pipeline unless you implement it inside the MCP server (e.g. a `memory_remember` tool the model calls, gated by confirm)
### v1b: Same MCP server reachable from ChatGPT (Developer mode) via Secure MCP Tunnel or public HTTPS [read_only_ok=True, cost=$0 (tunnel) or ngrok/Cloudflare tunnel fees; ChatGPT Plus/Pro required for Developer mode, effort=days, risk=low]
Run the server with `transport='streamable-http'` behind OpenAI's `tunnel-client` (`tunnel-client init --sample sample_mcp_stdio_local --mcp-command "uv run jobpilot-mcp"`) or expose it publicly (ngrok/Cloudflare) and add it as a connector in ChatGPT Settings -> Security and login -> Developer mode.
Pros:
  - Lets ChatGPT be the GPT-side chat UI with the same tools
  - Secure MCP Tunnel keeps the server off the public internet and supports stdio servers directly
Cons:
  - ChatGPT has no local stdio support; Developer mode is documented as web-only and 'availability can depend on account and workspace policy'
  - Secure MCP Tunnel requires an OpenAI Platform organization with Tunnels Read+Use/Manage permissions plus a separate ChatGPT developer-mode entitlement (the documented common blocker)
  - Public HTTPS exposure of a tool server holding your job-search data is a real attack surface; OAuth setup is your problem
  - Codex already gives a GPT-backed local stdio client, making this largely redundant
### v2: Custom chat UI (Gradio or FastAPI + browser page) with in-app provider switch [read_only_ok=True, cost=API usage: e.g. Sonnet 5 $2/$10 per MTok, Opus 5 $5/$25, Haiku 4.5 $1/$5 (platform.claude.com); GPT per-model on developers.openai.com/api/docs/pricing; STT $0.0045/min if using gpt-transcribe, effort=weeks, risk=none]
Local web UI served from the Python app: chat pane with streaming, a provider/model dropdown, a push-to-talk mic button (`gr.Audio(sources=['microphone'], type='filepath')` or a browser `webkitSpeechRecognition` widget), confirmation cards for pending actions, and optional TTS playback. Backed by Pydantic AI (option below) over the same JobPilot tool functions.
Pros:
  - Full control of system prompt, model, effort/thinking, memory extraction, confirmation UX and voice UX
  - Confirmation becomes a UI click/deterministic keyword outside the LLM, which is stronger than a model-issued confirm tool call
  - Streaming text plus streamed tool-call arguments in both providers
Cons:
  - You now pay API tokens and manage keys, retries, caching, and history storage
  - Browser STT quality/availability varies by browser (Chrome good, Edge inconsistent); you own mic permissions and HTTPS/localhost constraints
  - Several weeks of incremental work to reach parity with Claude Desktop's polish
### LLM abstraction (a): thin adapter over the official `anthropic` and `openai` SDKs [read_only_ok=True, cost=API tokens only, effort=days, risk=none]
One `LLMProvider` protocol with `chat(messages, tools, stream=True)` implemented twice. Anthropic: `client.messages.stream(...)` or beta `client.beta.messages.tool_runner` with `@beta_tool`; tools use `input_schema`, calls arrive as `tool_use` blocks (`input` already parsed), results go back as `tool_result` blocks (`tool_use_id`) in a user message. OpenAI: `client.responses.create(input=..., tools=[{type:'function', name, parameters, strict:true}])`; calls arrive as `function_call` output items (`call_id`, `arguments` JSON string), results go back as `function_call_output` items; multi-turn via `previous_response_id` or resending items.
Pros:
  - Zero framework lock-in; direct access to provider-native features (Anthropic adaptive thinking/effort, `output_config.format`, explicit `cache_control` breakpoints, `eager_input_streaming`; OpenAI `text.format` json_schema, `prompt_cache_key`, hosted tools)
  - Smallest dependency surface (anthropic 1.6.0, openai 3.14.1)
  - Easy to unit test the normalization layer
Cons:
  - You write and maintain the normalization: tool schema key (`input_schema` vs `parameters`), call shape (`tool_use.input` object vs `function_call.arguments` string), result shape (`tool_result` in user message vs `function_call_output` item), streaming events (`content_block_start`/`input_json_delta`/`content_block_stop` vs `response.function_call_arguments.delta`/`.done`), and history storage format
  - Structured output differs (`messages.parse(output_format=Model)` vs `responses.parse(text_format=Model)`); caching model differs (explicit breakpoints with model-dependent minimums 512/1024/4096 tokens vs automatic with 1024-token minimum)
  - Claude Fable 5.1 rejects forced `tool_choice` any/tool (400) while Opus 5/Sonnet 5 accept it, so the adapter must standardize on `auto` + `strict: true`
  - You must build the approval pause yourself (inspect pending tool calls before executing)
### LLM abstraction (b): LiteLLM (`litellm.completion`, model='anthropic/claude-sonnet-5' | 'openai/<id>') [read_only_ok=True, cost=API tokens only (library is MIT/free), effort=days, risk=none]
OpenAI Chat Completions-shaped unified call; LiteLLM 1.101.0 translates `tools`, `tool_choice`, `parallel_tool_calls`, `response_format` (-> Anthropic structured output), `reasoning_effort` (-> thinking), and passes `cache_control` content-block markers and `extra_headers` betas through to Anthropic.
Pros:
  - Single message/tool format; switching is a model-string change
  - Reports Anthropic cache usage as `prompt_tokens_details.cached_tokens` + `cache_creation_input_tokens`
  - `cache_control_injection_points` can auto-inject cache markers
Cons:
  - Lowest-common-denominator Chat Completions shape: OpenAI Responses-only features (previous_response_id, hosted tools, reasoning items) are not the primary path
  - Anthropic-native features (adaptive thinking display, effort, eager input streaming, strict tools) lag or need passthrough; prompt-caching minimums are silently skipped with no error
  - Large dependency footprint for a one-user app; no built-in approval/pause primitive; frequent releases
### LLM abstraction (c): Pydantic AI 2.43.0 (`pydantic-ai-slim[openai,anthropic,mcp]`) [read_only_ok=True, cost=API tokens only, effort=days, risk=none]
`Agent(model='anthropic:claude-sonnet-5', deps_type=AppDeps, output_type=[str, DeferredToolRequests], toolsets=[jobpilot_toolset])`; switch with `agent.run_sync(prompt, model='openai:<id>')`. Tools via `@agent.tool` (RunContext deps) or `FunctionToolset`; mutating tools marked `requires_approval=True` (or raise `ApprovalRequired`) so the run returns `DeferredToolRequests`; UI shows a confirm card; resume with `agent.run_sync(message_history=msgs, deferred_tool_results=DeferredToolResults(approvals={call_id: True | ToolDenied('user declined')}))`. Streaming via `run_stream()`/`stream_text()`; `UsageLimits(tool_calls_limit=..., cost_limit=...)`; Anthropic caching via `AnthropicModelSettings(anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True)` or `CachePoint()`.
Pros:
  - Built-in human-in-the-loop that maps exactly to the mandatory-confirmation requirement, provider-agnostic
  - Provider switch is a string; both `OpenAIResponsesModel` and `OpenAIChatModel` available; `FallbackModel` for outage fallback
  - Tool-mode structured output works identically on Claude and GPT (Anthropic has no native JSON mode in Pydantic AI, so tool mode is the portable default)
  - MCP client built in: can consume the v1 JobPilot MCP server or call the Python functions directly
  - Typed deps, Pydantic-validated tool args, usage/cost limits, docstring-derived schemas
Cons:
  - Framework abstraction: newest provider features (e.g. Anthropic `eager_input_streaming`, mid-conversation system messages, OpenAI `prompt_cache_key`) may need `model_settings` passthrough or wait for a release
  - Runs use fresh run_ids on resume; you must persist `message_history` yourself (JSON via `ModelMessagesTypeAdapter`)
  - Confirm that pydantic-ai's anthropic extra is compatible with anthropic 1.x (httpx2-based) in your lockfile
### LLM abstraction (d): LangChain v1 (`init_chat_model('anthropic:...')`, `bind_tools`, `with_structured_output`) + LangGraph `interrupt()` [read_only_ok=True, cost=API tokens only, effort=weeks, risk=none]
LangChain provider packages (`langchain-anthropic`, `langchain-openai`) with configurable model fields; LangGraph graph with a checkpointer (`SqliteSaver`) and `interrupt()` inside mutating tools, resumed via `Command(resume={'action':'approve'})`. `AnthropicPromptCachingMiddleware` for cache breakpoints.
Pros:
  - Mature, documented HITL via interrupt/checkpointer with durable state
  - Configurable model switching at invoke time (`configurable_fields`)
  - Large ecosystem
Cons:
  - Heaviest dependency graph of the five; graph/checkpointer machinery is overkill for a single-user chat box
  - Provider-native features arrive through wrappers; debugging goes through several abstraction layers
  - Structured-output method differs per provider (`json_schema` vs `function_calling`) and must be chosen explicitly
### LLM abstraction (e): OpenAI Agents SDK 0.22.2 with LiteLLM adapter for Claude [read_only_ok=True, cost=API tokens only, effort=days, risk=none]
`Agent(model='litellm/anthropic/claude-sonnet-5')` via `openai-agents[litellm]`; `@function_tool(needs_approval=True)` pauses with `result.interruptions`, resume via `result.to_state()` -> `state.approve()/reject()`; local MCP via `MCPServerStdio(params={'command':..., 'args':[...]})` with `require_approval` per tool.
Pros:
  - Good approval primitives and MCP stdio support out of the box
  - First-class OpenAI Responses features (hosted tools, ToolSearchTool) when on GPT
Cons:
  - Claude only via LiteLLM/Chat-Completions path; docs warn non-OpenAI providers lack Responses support, may lack JSON-schema output, and tracing needs `set_tracing_disabled(True)` or an OpenAI key
  - OpenAI-centric defaults (default model `gpt-5.6-luna`); recommends a single model shape per workflow, which conflicts with hot-switching providers
  - Second-class Anthropic support (caching, thinking/effort) compared with Pydantic AI or the raw SDK
### STT (v2 baseline): browser Web Speech API push-to-talk (Chrome; Edge with caveats) [read_only_ok=True, cost=$0, effort=hours, risk=none]
`const r = new (window.SpeechRecognition||window.webkitSpeechRecognition)(); r.lang='ja-JP'|'zh-CN'|'en-US'; r.interimResults=true; r.continuous=false;` start on mousedown/keydown, stop on release; post final transcript to the backend. Optional on-device: `SpeechRecognition.available({langs:[lang], processLocally:true})` -> `install()` -> `r.processLocally=true`.
Pros:
  - Zero cost, zero backend code, ~instant results; supports zh/ja/en language tags on Chrome's default engine
  - Push-to-talk is natural in a browser button
  - On-device mode (Chrome 139+, reliably 142+) keeps audio local once a language pack is installed
Cons:
  - Chrome's default engine is server-based (audio sent to Google), needs HTTPS or http://localhost, and API is `webkit`-prefixed; not Baseline (Firefox off by default)
  - Edge: caniuse marks unsupported; Microsoft says its implementation uses Azure and there are 2024 reports of silent no-result failures; Edge on-device model is Canary/Dev 150+ only and supports en/de/it/pt/es/ko, not zh/ja
  - On-device packs in Chrome are per-language; zh/ja availability must be probed at runtime with `available()`
  - No control over accuracy or domain vocabulary beyond `phrases` biasing
### STT (v2 upgrade): OpenAI transcription API [read_only_ok=True, cost=$0.0045/min (gpt-transcribe), $0.003/min (gpt-4o-mini-transcribe), $0.006/min (whisper-1), $0.017/min (gpt-live-transcribe), effort=hours, risk=none]
Record a clip in the browser (MediaRecorder -> webm) and POST to your backend, which calls `client.audio.transcriptions.create(model='gpt-transcribe', file=..., languages=['ja','zh','en'], keywords=[company names], stream=True)` at `/v1/audio/transcriptions`. For live captions use a Realtime transcription session (`session.type='transcription'`, `audio.input.transcription.model='gpt-live-transcribe'`, `audio.input.transcription.delay='low'`, events `conversation.item.input_audio_transcription.delta/.completed`; browser via WebRTC needs a server-minted ephemeral secret from `POST /v1/realtime/client_secrets`, SDP via `/v1/realtime/calls`).
Pros:
  - High accuracy incl. zh (`zh-cn`/`zh-tw`/`zh-hk`, `cmn`, `yue`), ja, en; `keywords`/`prompt` bias toward company and role names
  - Clip mode is trivial and cheap: $0.0045/min gpt-transcribe (25 MB limit; mp3/mp4/mpeg/mpga/m4a/wav/webm); `stream=true` gives `transcript.text.delta` events
  - `whisper-1` still available for word timestamps; `gpt-4o-transcribe-diarize` for speaker labels
Cons:
  - Audio leaves the machine; requires OpenAI API key and billing
  - Realtime `gpt-live-transcribe` is $0.017/min and adds WebRTC/WebSocket plumbing that a push-to-talk command UI does not need
  - Clip round trip adds ~1-3 s latency vs in-browser recognition
### STT (offline/private): local faster-whisper 1.2.1 or whisper.cpp [read_only_ok=True, cost=$0; local CPU/GPU, effort=days, risk=none]
`pip install faster-whisper`; `WhisperModel('small'|'turbo'|'large-v3', device='cpu', compute_type='int8')` or `device='cuda'` (requires CUDA 12 + cuDNN 9 libs); `model.transcribe(path, language='ja', vad_filter=True)`. whisper.cpp offers CUDA/Vulkan/OpenVINO builds and a `whisper-stream` real-time tool; model RAM: tiny ~273 MB, base ~388 MB, small ~852 MB, medium ~2.1 GB, large ~3.9 GB.
Pros:
  - Fully offline, no per-minute cost, audio never leaves the PC
  - Whisper family covers zh/ja/en; CPU int8 `small` ran 13 min of audio in 1m42s on an i7 (~7.6x realtime), so a 5-10 s command transcribes in roughly 1-2 s on CPU
  - GPU large-v3 batched: 13 min in ~16-17 s on an RTX 3070 Ti
Cons:
  - Windows CUDA setup (CUDA 12 + cuDNN 9 DLLs on PATH) is fiddly; CPU-only `large-v3` is too slow for interactive use
  - Lower accuracy than gpt-transcribe/Nova-3 for short noisy commands, esp. small models on Chinese/Japanese
  - Adds ~1-3 GB of models and a heavy dependency (ctranslate2/torch-free but still large)
### STT (other cloud): Deepgram Nova-3 or Azure Speech [read_only_ok=True, cost=Deepgram: $200 free credit then $0.0048/min mono, $0.0058/min multilingual streaming; Azure F0 free 5 h/month, effort=days, risk=none]
Deepgram `nova-3` streaming/pre-recorded with real-time multilingual code-switching (zh Mandarin/Cantonese, ja, en); Azure Speech SDK real-time recognition for zh-CN, zh-TW, ja-JP, en-US plus Fast Transcription REST.
Pros:
  - Deepgram: $200 free credit, no card; Nova-3 multilingual code-switching in one stream is the best fit if you mix zh/ja/en mid-sentence; Flux model adds turn detection
  - Azure: F0 tier gives 5 audio hours/month STT and 0.5 M neural TTS chars/month free; strong zh/ja voices
Cons:
  - Another vendor/API key each; Azure SDK setup is heavier than a REST call
  - Deepgram streaming $0.0048-0.0058/min after credit; Azure standard pricing not shown on the page (needs calculator)
  - Neither is needed unless Web Speech/OpenAI prove inadequate
### Voice trigger: push-to-talk (recommended) vs wake word (openWakeWord / Picovoice Porcupine) [read_only_ok=True, cost=$0, effort=hours, risk=low]
Push-to-talk: a held key/button (browser mousedown, or a global hotkey via `keyboard`/`pynput` in a tray app) starts recording; release stops. Wake word: openWakeWord (80 ms frames, ONNX on Windows, 6 pretrained English models; custom words trained via Colab) or Porcupine (commercial, AccessKey).
Pros:
  - Push-to-talk needs no always-on microphone, no VAD tuning, no false accepts, and works in every STT option above
  - Silero VAD (`pip install silero-vad`, ~2 MB, <1 ms/chunk, 8/16 kHz, MIT) can auto-end an utterance if you want tap-to-start
Cons:
  - Wake word: openWakeWord pretrained models are CC BY-NC-SA 4.0 and English-only ('hey jarvis' etc.); a custom zh/ja wake word requires synthetic-data training; always-on mic is a privacy and CPU cost
  - Porcupine free-tier terms could not be verified from its pricing page in this research
### TTS (free/offline): browser `speechSynthesis` or Windows SAPI via pyttsx3 2.99 [read_only_ok=True, cost=$0, effort=hours, risk=none]
Browser: `speechSynthesis.speak(new SpeechSynthesisUtterance(text))` after `voiceschanged`; pick a `lang`-matching voice. Python: `pyttsx3.init('sapi5')` uses installed Windows voices offline.
Pros:
  - Zero cost, offline, no keys; adequate for reading back confirmations and short answers
  - Windows ships zh-CN/ja-JP neural-ish voices when the language packs are installed
Cons:
  - Voice quality and availability depend on installed Windows language packs; robotic vs cloud voices
  - Long answers read aloud are tedious; consider TTS only for confirmations and summaries
### TTS (cloud): OpenAI `gpt-4o-mini-tts`; (unofficial) edge-tts [read_only_ok=True, cost=OpenAI $12/1M chars (gpt-4o-mini-tts), $15 (tts-1), $30 (tts-1-hd); edge-tts $0, effort=hours, risk=medium]
OpenAI `POST /v1/audio/speech` with `model='gpt-4o-mini-tts'`, `voice='marin'|'cedar'` (recommended), `response_format='pcm'|'wav'` for lowest latency, chunked streaming, `instructions` for tone; follows Whisper language coverage (zh/ja/en) though voices are English-optimized. edge-tts (`pip install edge-tts`) calls Microsoft Edge's online neural voices without a key.
Pros:
  - gpt-4o-mini-tts: natural voices, streaming, tone control, 13 voices
  - edge-tts: free, hundreds of neural voices incl. zh-CN/ja-JP, no account
Cons:
  - OpenAI TTS $12/1M chars and audio goes to the cloud
  - edge-tts uses Edge's internal service unofficially; Microsoft already restricts SSML to what Edge itself emits and could block it; not suitable as a dependency you rely on
### TTS (local high quality): Kokoro 82M [read_only_ok=True, cost=$0, effort=hours, risk=none]
`pip install kokoro>=0.9.4 soundfile` (+ `misaki[ja]`, `misaki[zh]`, espeak-ng); `KPipeline(lang_code='j'|'z'|'a')` generates 24 kHz audio locally.
Pros:
  - Apache-2.0 open weights; supports Japanese, Mandarin Chinese, American/British English
  - Small model, fast on CPU, no cloud
Cons:
  - PyTorch dependency and espeak-ng install on Windows; per-language G2P extras
  - Quality below cloud TTS for expressive speech

## Concrete details
  - Claude Desktop config (Windows): `%APPDATA%\Claude\claude_desktop_config.json` -> {"mcpServers": {"jobpilot": {"command": "uv", "args": ["run", "--directory", "D:\\Personal_Projects\\JobPilot", "jobpilot-mcp"], "env": {"JOBPILOT_DB": "D:\\Personal_Projects\\JobPilot\\data\\jobpilot.sqlite"}}}}; restart app; verify under 'Add files, connectors, and more' -> Connectors -> Manage connectors; logs at `%APPDATA%\Claude\logs\mcp-server-jobpilot.log`.
  - Claude Code: `claude mcp add --transport stdio --scope user jobpilot -- uv run --directory D:\Personal_Projects\JobPilot jobpilot-mcp`; check with `/mcp` or `claude mcp list`; tool names appear as `mcp__jobpilot__<tool>`; allow read-only tools without prompting via settings rule `"mcp__jobpilot__search_applications": "allow"`; output cap default 25,000 tokens (`MAX_MCP_OUTPUT_TOKENS`).
  - Codex: `codex mcp add jobpilot -- uv run --directory D:\Personal_Projects\JobPilot jobpilot-mcp`; config.toml `[mcp_servers.jobpilot] command="uv" args=[...] env={JOBPILOT_DB="..."}`; `default_tools_approval_mode = "prompt"`; `enabled_tools` allowlist.
  - ChatGPT (optional v1b): Settings -> Security and login -> Developer mode (web); connector must be a public HTTPS Streamable-HTTP `/mcp` URL or a Secure MCP Tunnel (`tunnel-client init --sample sample_mcp_stdio_local --profile local-stdio --tunnel-id tunnel_... --mcp-command "uv run --directory D:\Personal_Projects\JobPilot jobpilot-mcp"`, API key with Tunnels Read+Use).
  - MCP server skeleton (official SDK 2.x): `from mcp.server.fastmcp import FastMCP; mcp = FastMCP('jobpilot'); @mcp.tool() def search_applications(query: str = '', status: str | None = None, company: str | None = None, since: str | None = None, limit: int = 20) -> list[dict]: ...; @mcp.tool() def propose_status_update(application_id: int, new_status: str, reason: str = '') -> dict: ...; @mcp.tool() def confirm_action(action_id: str) -> dict: ...; mcp.run(transport='stdio')`. Dev inspector: `uv run mcp dev src/jobpilot/mcp_server.py`. Return tools in deterministic order; add `annotations={'readOnlyHint': True}` on read tools and `{'destructiveHint': False, 'idempotentHint': True}` on propose tools.
  - Tool registry contract: each tool declares `side_effect: Literal['none','local_db']`; `jobpilot.connectors` (gmail, linkedin, boards) exposes only `fetch_*`/`list_*`/`get_*`; CI test: `assert not any(name.startswith(('send','post','apply','label','delete','message','write')) for name in dir(connectors))` and no tool imports `googleapiclient` write methods; Gmail OAuth scope `https://www.googleapis.com/auth/gmail.readonly` only.
  - Schema additions for this layer (SQLite): `pending_actions(id TEXT PK, tool TEXT, args_json TEXT, summary TEXT, diff_json TEXT, status TEXT CHECK(status IN ('pending','confirmed','cancelled','expired')), created_at TEXT, expires_at TEXT, confirmed_at TEXT, confirmed_via TEXT CHECK(confirmed_via IN ('ui_click','host_approval','keyword')))`; `chat_sessions(id TEXT PK, started_at TEXT, provider TEXT, model TEXT, title TEXT)`; `chat_messages(id INTEGER PK, session_id TEXT, seq INTEGER, role TEXT, content_json TEXT, provider TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, created_at TEXT)`; `memory_facts(id INTEGER PK, kind TEXT CHECK(kind IN ('profile','preference','outcome','constraint','note')), key TEXT, value_json TEXT, source_message_id INTEGER, confidence REAL, created_at TEXT, superseded_by INTEGER NULL)`; `voice_settings(key TEXT PK, value TEXT)` for stt_provider, tts_enabled, language.
  - FTS for grounding: `CREATE VIRTUAL TABLE applications_fts USING fts5(company, title, notes, content='applications', content_rowid='id')` and `memory_fts` similarly; tools query FTS with `limit` and return `{id, company, title, status, last_event_at, snippet}`.
  - Pydantic AI v2 shape: `agent = Agent('anthropic:claude-sonnet-5', deps_type=AppDeps, instructions=SYSTEM, toolsets=[jobpilot_toolset], output_type=[str, DeferredToolRequests], model_settings=AnthropicModelSettings(anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True))`; `@jobpilot_toolset.tool(requires_approval=True) def update_status(ctx: RunContext[AppDeps], application_id: int, new_status: str) -> str`; run: `res = await agent.run(prompt, deps=deps, message_history=hist, model=selected_model)`; if `isinstance(res.output, DeferredToolRequests)`: show cards, then `await agent.run(message_history=res.all_messages(), deferred_tool_results=DeferredToolResults(approvals={c.tool_call_id: True | ToolDenied('declined')}))`; streaming: `async with agent.run_stream(...) as s: async for t in s.stream_text(delta=True)`; guard with `UsageLimits(tool_calls_limit=8, request_limit=6)`.
  - Thin-adapter reference shapes if you skip Pydantic AI: Anthropic tool `{name, description, input_schema, strict: true}` -> response `content[i].type=='tool_use'` with `.id/.name/.input` -> reply `{'role':'user','content':[{'type':'tool_result','tool_use_id': id, 'content': json.dumps(result)}]}`; streaming events `content_block_start` (tool_use) / `input_json_delta.partial_json` / `content_block_stop`; structured output `client.messages.parse(output_format=Model)` or `output_config={'format': {'type':'json_schema','schema':...}}`; caching `system=[{'type':'text','text':SYSTEM,'cache_control':{'type':'ephemeral'}}]`. OpenAI tool `{type:'function', name, description, parameters, strict: true}` -> `response.output[i].type=='function_call'` with `.call_id/.name/.arguments` (json.loads) -> reply item `{type:'function_call_output', call_id, output: json.dumps(result)}`; streaming `response.function_call_arguments.delta/.done`; structured `client.responses.parse(text_format=Model)`; caching automatic, set `prompt_cache_key='jobpilot-chat'`.
  - Web Speech push-to-talk snippet: `const SR = window.SpeechRecognition || window.webkitSpeechRecognition; const r = new SR(); r.lang = langSelect.value /* 'ja-JP' | 'zh-CN' | 'zh-TW' | 'en-US' */; r.interimResults = true; r.maxAlternatives = 1; btn.onpointerdown = () => r.start(); btn.onpointerup = () => r.stop(); r.onresult = e => { const t = e.results[e.results.length-1]; if (t.isFinal) postTranscript(t[0].transcript); };` Serve over http://localhost or HTTPS. On-device probe: `await SR.available({langs:[lang], processLocally:true})` -> 'available'|'downloadable'|'downloading'|'unavailable'; `await SR.install({langs:[lang], processLocally:true})`; then `r.processLocally = true` (Chrome 142+).
  - OpenAI STT call: `client.audio.transcriptions.create(model='gpt-transcribe', file=open(clip,'rb'), languages=['ja','zh','en'], keywords=[...company names...], response_format='json')` at `POST /v1/audio/transcriptions`; 25 MB limit; formats mp3/mp4/mpeg/mpga/m4a/wav/webm; `stream=True` emits `transcript.text.delta`/`transcript.text.done`. Realtime alternative: `session.type='transcription'`, `audio.input.format={'type':'audio/pcm','rate':24000}`, `audio.input.transcription.model='gpt-live-transcribe'`, `audio.input.transcription.delay='low'`, `turn_detection=null` + `input_audio_buffer.commit` for PTT; browser auth via server-side `POST /v1/realtime/client_secrets`, SDP at `POST /v1/realtime/calls`.
  - OpenAI TTS call: `client.audio.speech.create(model='gpt-4o-mini-tts', voice='marin', input=text, instructions='calm, concise', response_format='pcm')` at `POST /v1/audio/speech`; stream chunks to the browser; voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, marin, cedar.
  - Local STT: `uv add faster-whisper` (1.2.1); `WhisperModel('small', device='cpu', compute_type='int8')`; GPU needs CUDA 12 + cuDNN 9 (ctranslate2 >= 4.5); `segments, info = model.transcribe(path, language=None, vad_filter=True)`. VAD: `uv add silero-vad` (16 kHz, 30 ms+ chunks, <1 ms/chunk CPU). Local TTS: `uv add kokoro soundfile` + `misaki[ja]`/`misaki[zh]`, `KPipeline(lang_code='j')`; offline fallback `pyttsx3.init('sapi5')`.
  - Windows built-in voice input: Win+H voice typing (Settings toggle 'automatic punctuation'); languages include zh-CN, zh-TW, zh-HK, ja-JP, en-*; requires internet (Azure). Claude Code: `/voice hold` (push-to-talk Space, rebind via `~/.claude/keybindings.json` `voice:pushToTalk`), set `"language": "japanese"` in settings for ja dictation; `"voice": {"enabled": true, "mode": "tap", "autoSubmit": true}`.
  - Deepgram (if adopted): model `nova-3`, `language=multi` for zh/ja/en code-switching, streaming WebSocket; $200 free credit, no card; $0.0058/min multilingual streaming. Azure (if adopted): Speech SDK `SpeechRecognizer` with `AutoDetectSourceLanguageConfig(['zh-CN','ja-JP','en-US'])`; F0 = 5 h/month STT, 0.5 M chars/month neural TTS.
  - Package versions verified on PyPI 2026-09-15/16: anthropic 1.6.0 (Python 3.10+, httpx2), openai 3.14.1, pydantic-ai 2.43.0, mcp 2.2.0, litellm 1.101.0, openai-agents 0.22.2, faster-whisper 1.2.1, pyttsx3 2.99. Project is Python 3.12, so all are compatible.
  - System-prompt grounding rules (v2): 'Answer only from tool results. Every application you mention must include its id in brackets, e.g. [app:42]. If a tool returns no rows, say the tracker has no record. Never state that an email was sent, an application submitted, or a status changed unless a confirm_action result says so. For any change, call the propose_* tool and stop; the user confirms in the UI.'
  - Confirmation UX for voice: after `propose_*` returns, the UI speaks/prints `"Mark Acme SWE [app:42] as rejected? Say 'confirm' or click Confirm."`; the transcript is matched deterministically (`re.fullmatch(r'\s*(confirm|yes|確認|はい|确认|是)\s*', t, re.I)`) outside the model; only then is `confirm_action(action_id)` executed by application code, not by the LLM.

## Open questions
  - Does Claude Desktop voice mode invoke tools from a local stdio MCP server, or only cloud 'connectors' (Gmail, Calendar, Slack, web search) as the help article lists? This decides whether v1 voice control works end-to-end without Win+H; test with one read-only tool.
  - Is local MCP in Claude Desktop available on the user's plan? Anthropic's article does not state a plan gate for local servers (remote custom connectors are Pro+), but third-party reports conflict; verify on the actual account.
  - Which browser will host the v2 UI? Chrome's cloud Web Speech works today for zh/ja/en; Edge is reported to silently return no results in some environments and its on-device model lacks zh/ja. If the user prefers Edge, plan on OpenAI gpt-transcribe clips instead.
  - Does the user speak mixed Chinese/Japanese/English within one utterance (code-switching)? If yes, prefer Deepgram Nova-3 multilingual or gpt-transcribe with `languages=['zh','ja','en']`; Web Speech needs a single `lang` per utterance.
  - Does the machine have an NVIDIA GPU with CUDA 12 + cuDNN 9 (for faster-whisper GPU / Kokoro speed)? Otherwise local STT is limited to `small`/`turbo` int8 on CPU.
  - Does the user want spoken replies (TTS) at all, or voice-in/text-out? TTS adds latency and cost; confirmations only is a reasonable default.
  - Which OpenAI access exists: ChatGPT Plus/Pro (Developer mode, web only), Codex, and/or an OpenAI Platform org with billing (needed for API STT/TTS and Secure MCP Tunnel permissions)?
  - Are Chinese and Japanese Windows TTS/SAPI voices installed (needed for free offline `speechSynthesis`/pyttsx3 output in those languages)?
  - Compatibility check needed in the lockfile: anthropic 1.x uses httpx2; confirm pydantic-ai 2.43 / litellm 1.101 pins resolve cleanly with uv on Python 3.12.
  - Should the memory-extraction pass (proposing `memory_facts` after each turn) use the same model as the chat or a cheaper one (`claude-haiku-4-5` / a GPT mini variant)? Both must still flow through propose/confirm.
  - Should `confirm_action` be callable by the LLM at all in v1 (where the host's approval dialog is the only outer gate), or should v1 hosts only ever see `propose_*` tools while confirmation happens through a tiny local tray/CLI command (`jobpilot confirm <id>`)? The latter is strictly safer but adds friction.

## Sources
- OpenAI Speech to text guide (models gpt-transcribe, gpt-4o-transcribe-diarize, whisper-1, gpt-live-transcribe; /v1/audio/transcriptions): https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI Realtime transcription guide (session.type=transcription, gpt-live-transcribe, delay levels, events): https://developers.openai.com/api/docs/guides/realtime-transcription
- OpenAI Realtime guide (WebRTC/WebSocket, POST /v1/realtime/client_secrets, /v1/realtime/calls): https://developers.openai.com/api/docs/guides/realtime
- OpenAI Text to speech guide (gpt-4o-mini-tts, tts-1, tts-1-hd, voices, formats, instructions): https://developers.openai.com/api/docs/guides/text-to-speech
- OpenAI API pricing (audio transcription per minute, TTS per 1M chars): https://developers.openai.com/api/docs/pricing
- OpenAI Models page (gpt-6-astra, gpt-5.6-sol/terra/luna, realtime and transcription models): https://developers.openai.com/api/docs/models
- OpenAI Function calling (Responses API tool format, function_call / function_call_output, streaming events, tool_choice): https://developers.openai.com/api/docs/guides/function-calling
- OpenAI Structured outputs (text.format json_schema, responses.parse): https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Prompt caching (automatic, 1,024-token minimum, prompt_cache_key, cached_tokens): https://developers.openai.com/api/docs/guides/prompt-caching
- OpenAI Migrate to Responses (Chat Completions still supported; Assistants API sunset 2026-08-26): https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI ChatGPT Developer mode (plans, web, read/write MCP tools): https://developers.openai.com/api/docs/guides/developer-mode
- OpenAI Apps SDK: Connect your MCP server to ChatGPT (public HTTPS or Secure MCP Tunnel): https://developers.openai.com/apps-sdk/deploy/connect-chatgpt
- OpenAI Secure MCP Tunnel guide: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- OpenAI tunnel-client (stdio/HTTP local MCP servers to ChatGPT/Codex): https://github.com/openai/tunnel-client
- OpenAI Help Center: Developer mode and MCP apps in ChatGPT: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Codex MCP docs (codex mcp add, config.toml mcp_servers, approval modes): https://learn.chatgpt.com/docs/extend/mcp?surface=cli
- OpenAI Agents SDK: Models (default model, Responses vs Chat Completions, LiteLLM/any-llm adapters, non-OpenAI limitations): https://openai.github.io/openai-agents-python/models/
- OpenAI Agents SDK: Tools (function_tool, needs_approval, interruptions): https://openai.github.io/openai-agents-python/tools/
- OpenAI Agents SDK: MCP (MCPServerStdio, MCPServerStreamableHttp, require_approval): https://openai.github.io/openai-agents-python/mcp/
- Claude models overview (claude-opus-5, claude-sonnet-5, claude-haiku-4-5, claude-fable-5-1, pricing, context): https://platform.claude.com/docs/en/about-claude/models/overview.md
- Claude tool use overview: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- Claude prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Claude structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- Anthropic Python SDK repository (tool_runner, @beta_tool, anthropic.lib.tools.mcp): https://github.com/anthropics/anthropic-sdk-python
- Anthropic Python SDK v1 migration (httpx2): https://github.com/anthropics/anthropic-sdk-python/blob/main/MIGRATION.md
- Claude Code: MCP (claude mcp add, scopes, .mcp.json, Windows cmd /c, permissions, output limits): https://code.claude.com/docs/en/mcp
- Claude Code: Voice dictation (/voice, Windows, languages list, claude.ai login): https://code.claude.com/docs/en/voice-dictation
- Claude Help Center: Use voice mode (desktop, all plans, connected tools): https://support.claude.com/en/articles/11101966-use-voice-mode
- Claude Help Center: Getting started with local MCP servers on Claude Desktop: https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop
- Claude Desktop extensions (.mcpb bundles): https://claude.com/docs/connectors/custom/desktop-extensions
- MCP: Connect to local MCP servers (Claude Desktop config path, Windows notes, logs): https://modelcontextprotocol.io/docs/develop/connect-local-servers
- MCP specification 2026-07-28 changelog (stateless, server/discover, deprecations): https://modelcontextprotocol.io/specification/2026-07-28/changelog
- MCP specification 2025-11-25 (features, security principles): https://modelcontextprotocol.io/specification/2025-11-25
- MCP extension support matrix (clients incl. Claude Desktop, ChatGPT, Cursor): https://modelcontextprotocol.io/extensions/client-matrix.md
- MCP Python SDK (mcp 2.x, FastMCP decorators, stdio/streamable-http, mcp dev): https://github.com/modelcontextprotocol/python-sdk
- Pydantic AI: Models overview (provider strings, FallbackModel): https://pydantic.dev/docs/ai/models/overview/
- Pydantic AI: Agents (run model override, run_stream, message_history, UsageLimits): https://pydantic.dev/docs/ai/agents/
- Pydantic AI: Function tools: https://pydantic.dev/docs/ai/tools-toolsets/tools/
- Pydantic AI: Deferred tools / human-in-the-loop approval: https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/
- Pydantic AI: Output modes (ToolOutput, NativeOutput, PromptedOutput): https://pydantic.dev/docs/ai/output/
- Pydantic AI: Anthropic model (prompt caching settings, CachePoint, thinking/effort): https://pydantic.dev/docs/ai/models/anthropic/
- Pydantic AI: Install: https://pydantic.dev/docs/ai/install/
- LiteLLM: Function calling: https://docs.litellm.ai/docs/completion/function_call
- LiteLLM: Prompt caching: https://docs.litellm.ai/docs/completion/prompt_caching
- LiteLLM: Anthropic provider (supported params, passthrough): https://docs.litellm.ai/docs/providers/anthropic
- LangChain v1: Models (init_chat_model, bind_tools, with_structured_output, AnthropicPromptCachingMiddleware): https://docs.langchain.com/oss/python/langchain/models
- LangGraph: Interrupts (interrupt(), Command(resume), checkpointer): https://docs.langchain.com/oss/python/langgraph/interrupts
- MDN: Web Speech API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
- MDN: SpeechRecognition (processLocally, available(), install(), phrases; Chrome server-based note): https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
- MDN: Using the Web Speech API (on-device speech recognition section): https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API
- caniuse: Speech Recognition API browser support: https://caniuse.com/speech-recognition
- Chromium blink-dev: Intent to Ship Web Speech API on-device recognition quality (2026): https://groups.google.com/a/chromium.org/g/blink-dev/c/P8P-x7AnC6I
- Chromium issue: on-device SpeechRecognition available() regression / re-enabled in 142: https://issues.chromium.org/issues/444393111
- Microsoft Edge: SpeechRecognition API with on-device model (Canary/Dev 150+, languages): https://learn.microsoft.com/en-us/microsoft-edge/web-platform/speech-recognition-api
- Microsoft Edge policy SpeechRecognitionEnabled (Edge Web Speech uses Azure Cognitive Services): https://learn.microsoft.com/en-us/deployedge/microsoft-edge-browser-policies/speechrecognitionenabled
- mdn/browser-compat-data issue: Edge SpeechRecognition returns no results: https://github.com/mdn/browser-compat-data/issues/22126
- Microsoft Support: Use voice typing (Win+H) on Windows 11: https://support.microsoft.com/en-us/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc-fec94565-c4bd-329d-e59a-af033fa5689f
- faster-whisper repository (CUDA 12/cuDNN 9, int8 CPU, benchmarks): https://github.com/SYSTRAN/faster-whisper
- faster-whisper on PyPI (1.2.1): https://pypi.org/project/faster-whisper/
- whisper.cpp repository (platforms, model memory table, whisper-stream): https://github.com/ggml-org/whisper.cpp
- Silero VAD repository: https://github.com/snakers4/silero-vad
- openWakeWord repository (pretrained models, licenses, Windows ONNX): https://github.com/dscripka/openWakeWord
- Kokoro TTS repository (82M, Apache-2.0, ja/zh): https://github.com/hexgrad/kokoro
- edge-tts repository: https://github.com/rany2/edge-tts
- pyttsx3 on PyPI (SAPI5 offline): https://pypi.org/project/pyttsx3/
- Deepgram models & languages overview (nova-3, flux): https://developers.deepgram.com/docs/models-languages-overview
- Deepgram pricing ($200 free credit, per-minute rates): https://deepgram.com/pricing
- Azure Speech language support (zh-CN, zh-TW, ja-JP, en-US): https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt
- Azure Speech pricing (F0 free tier limits): https://azure.microsoft.com/en-us/pricing/details/speech/
- Gradio Audio component (microphone source, streaming): https://www.gradio.app/docs/gradio/audio
- anthropic on PyPI (1.6.0): https://pypi.org/project/anthropic/
- openai on PyPI (3.14.1): https://pypi.org/project/openai/
- pydantic-ai on PyPI (2.43.0): https://pypi.org/project/pydantic-ai/
- mcp on PyPI (2.2.0): https://pypi.org/project/mcp/
- litellm on PyPI (1.101.0): https://pypi.org/project/litellm/
- openai-agents on PyPI (0.22.2): https://pypi.org/project/openai-agents/
