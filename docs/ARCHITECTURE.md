# JobPilot 架构与技术选型

| 项目 | 内容 |
|---|---|
| 状态 | 草案 v0.1（2026-09-16） |
| 前置 | [REQUIREMENTS.md](REQUIREMENTS.md) 需求与硬约束 |
| 后续 | [ROADMAP.md](ROADMAP.md) 分阶段落地 |

本文描述推荐的系统架构。它综合了三个独立架构提案（MVP 优先 / 数据模型优先 / 集成风险优先）与三位评审的意见：以 MVP 优先的分期为骨架，吸收数据模型优先提案的数据纪律（优先级矩阵、公司别名、规则统计、画像快照），以及风险优先提案的运维安全（信息源状态、出站日志、令牌浸泡测试、密钥槽位白名单）。所有库版本与模型 ID 在实现时以官方页面为准。

---

## 1. 架构原则

1. **一个数据库，多个视图**：CLI、MCP 工具、Web UI、语音全部读写同一个 SQLite 文件，通过同一层服务函数，没有第二套逻辑。
2. **信息源是插件**：每个外部来源实现同一个只读 `Source` 接口（`fetch_*` / `list_*` / `get_*` / `import_*`），失败时降级为「不可用」状态而不是让整个应用挂掉。
3. **事实、判断、状态、日程分表**：岗位原始事实（来源可核验）、LLM 或用户的判断（匹配度、备注）、应聘状态、面试日程互不污染。
4. **每次写入带出处**：`source`、`source_ref`、`confidence`、`method`（rule / llm / user / import）、时间戳；自动变更与人工变更共用一张审计表。
5. **模型不直接改状态**：LLM 只能调用「提议」工具，落库必须经过用户确认（宿主审批、UI 点击、或程序匹配的确认关键词）。
6. **配置驱动**：个人画像、目标、地区、语言、模型 ID、路径全部来自配置与记忆，代码里没有任何个人信息。
7. **为迁移而设计**：本机运行是默认部署，但配置、数据目录、容器镜像从第一天就按「换机器只改环境变量」准备。

---

## 2. 总体架构

```
外部信息源（只读）                      本地进程（单进程、单写入者）                      对话入口
────────────────────                   ──────────────────────────────                 ─────────────────
Gmail API ──GET──▶ connectors/gmail ──▶ 分类管线 ──▶ services（pipeline/resolve/status）
Calendar API ─GET─▶ connectors/gcal ──▶   规则 → LLM        │                              Claude Desktop ─┐
LinkedIn 导出 ZIP ▶ connectors/linkedin_archive（零网络）    ▼                              Claude Code    ─┼─ stdio MCP ─▶ tools/registry
ATS 公开接口 ──GET─▶ connectors/boards ──▶ search（dedupe/scoring/learn）                  Codex CLI      ─┘        │
提供商网页搜索 ─────▶ connectors/websearch                     │                                                       │
                                                             ▼                              Web UI（Phase 2+）        │
                                              ┌──────────── SQLite（WAL） ────────────┐    浏览器 ◀─SSE─ FastAPI ◀──┘
                                              │ 追踪 · 事件 · 面试 · 岗位 · 记忆 · 审计 │    麦克风 → Web Speech → 聊天
                                              └────────────────────────────────────────┘        │
                                                             ▲                                  ▼
                                              memory（facts/extract/render）◀──── pydantic-ai Agent（Claude / GPT 可切）
                                                             ▲                         ▲ 只能调用 propose_* ，confirm 在程序侧
                                              actions（propose → pending_actions → confirm → audit_log）
```

数据流向：每一条指向外部服务的箭头都是 GET；每一次写入都落在本地数据库。发往 LLM 的只有脱敏截断后的文本。

---

## 3. 技术选型

| 层 | 选择 | 理由 | 备选 |
|---|---|---|---|
| 语言 / 包管理 | Python 3.12，uv（packaged `src/` 布局，`uv_build` 后端，`[project.scripts]` 暴露 `jobpilot` 与 `jobpilot-mcp`） | 已有工具链；3.12 兼容全部候选库（faster-whisper 尚不支持 3.13） | — |
| 数据库 | SQLite（WAL、`foreign_keys=ON`、`busy_timeout=5000`），标准库 `sqlite3` + 编号 SQL 迁移文件 + Pydantic 行模型 | FTS5、生成列、sqlite-vec 都是原生 SQL，少一层 ORM；单文件便于备份；单租户不需要 Postgres | SQLAlchemy 2 + Alembic（batch 模式）。若协作者更习惯 ORM 可改，但 Postgres 明确不在范围 |
| 全文检索 | FTS5 双表：`unicode61`（拉丁）+ `trigram`（CJK），1 到 2 字查询回退 `LIKE` | 中日英混合语料 | — |
| 向量检索（后期） | sqlite-vec 0.1.x + 本地 bge-m3 / multilingual-e5，或 Voyage / OpenAI embedding | 语料十万块以下暴力 KNN 足够 | LanceDB |
| Gmail / Calendar | google-api-python-client + google-auth-oauthlib（`InstalledAppFlow.run_local_server`，PKCE），自定义 `ReadOnlyHttp` 传输 | 官方 SDK；传输层可拦截非 GET | — |
| HTTP（岗位源） | httpx + `GetOnlyTransport`，ETag / If-Modified-Since，令牌桶限速，protego 解析 robots.txt | 结构性只读 | — |
| LLM 统一层 | pydantic-ai（`anthropic` + `openai` 扩展），模型字串来自配置 | 工具调用、结构化输出、流式、`requires_approval` 两阶段工具，两家差异被屏蔽 | 薄封装两家官方 SDK；LiteLLM |
| MCP 服务 | 官方 `mcp` Python SDK 2.x（`MCPServer`，stdio） | Claude Desktop / Claude Code / Codex 直接可用 | — |
| CLI | typer + rich | 快速可用的看板与诊断 | — |
| 调度 | Phase 1 简单循环 `jobpilot watch`；Phase 2 起 Windows 任务计划登录自启；Web 阶段 APScheduler 3.11（4.x 仍是预发布） | 单进程足够，无需队列 | systemd timer（Linux） |
| Web 后端 | FastAPI + uvicorn（默认绑定 127.0.0.1），sse-starlette 流式 | 与 pydantic 同生态 | — |
| Web 前端 | React 19 + TypeScript + Vite + Tailwind（`frontend/`） | 完整控制设计系统；Node 22 已在 | NiceGUI 挂在同一 FastAPI 上（工具链拖慢时的备选） |
| 语音 | 浏览器 Web Speech API 按住说话（ja-JP / zh-CN / en-US 切换）；可选 OpenAI 转写后备；本地 faster-whisper 仅离线用 | 免费、零后端代码 | Deepgram 多语模式 |
| 密钥 | keyring（Windows Credential Manager）存短 key；Google 令牌用 DPAPI 加密文件（Credential Manager 有长度上限）；Linux 用 Fernet 加密文件 | 平台原生保护 | — |
| 质量 | pytest、ruff、pyright、pre-commit | 常规 | — |

---

## 4. 只读保证：五层，任一层单独成立

| 层 | 机制 | 测试 |
|---|---|---|
| 1 凭据范围 | Google 令牌只含 `gmail.readonly` + `calendar.events.readonly`；`jobpilot auth google` 在落盘前断言 `set(scopes) ⊆ ALLOWED_SCOPES`；启动时再对 `oauth2.googleapis.com/tokeninfo` 做一次在线核对 | 单元测试：范围集合不变 |
| 2 传输 | 所有 Google 请求走 `ReadOnlyHttp`（`AuthorizedHttp` 子类，非 GET 抛 `WriteAttempted`，不使用 `/batch` 端点，因为 batch 包体可夹带写子请求）；岗位源走 httpx `GetOnlyTransport`；`FORBIDDEN_HOSTS`（linkedin.com、indeed.com、glassdoor.com、wantedly.com、bizreach.jp、mynavi.jp、rikunabi.com 等）直接拒绝 | 测试：POST / PUT / PATCH / DELETE 抛异常 |
| 3 代码面 | `jobpilot.connectors` 只导出 `fetch_* / list_* / get_* / import_*`；LinkedIn 连接器零网络代码；依赖树中没有 smtplib、imaplib、playwright、selenium、linkedin_api | 测试：导入全部模块，扫描公开符号名与 import 列表 |
| 4 工具注册表 | LLM / MCP 可见工具是静态白名单，每个声明 `side_effect ∈ {none, local_db}`；工具模块不得导入 connectors（导入图测试）；本地写操作两阶段（`propose_*` → `pending_actions` → `confirm_action`），确认动作由宿主审批、UI 点击或程序侧正则完成 | 测试：注册表快照 |
| 5 数据方向 | 唯一的非 GET 出站是 LLM / embedding API 调用，载荷为脱敏截断文本；`egress_log` 记录每次出站（时间、方法、主机、路径、状态），`jobpilot egress-report` 断言除令牌刷新与 LLM 端点外零非 GET | 集成测试 |

诚实说明：LLM SDK 各自持有 HTTP 客户端，`egress_log` 只能覆盖自建传输层的流量；令牌刷新 POST 由 Google SDK 内部发出。这两类在报告中单列。

密钥槽位白名单：`SecretStore` 只接受 `google_token`、`anthropic_api_key`、`openai_api_key`、`adzuna_*`、`jsearch_*` 等固定名字，结构上不存在放 LinkedIn cookie、SMTP 密码或 App Password 的位置。

---

## 5. 数据模型

数据库路径 `JOBPILOT_DATA_DIR/jobpilot.db`（Windows 默认 `%LOCALAPPDATA%\JobPilot\`）。时间统一存 UTC ISO 字符串，展示按 `JOBPILOT_TZ`。下表按引入阶段列出。

### 5.1 追踪域（Phase 1 至 2）

| 表 | 关键列 | 说明 |
|---|---|---|
| `campaign` | `campaign_id`, `name`, `kind CHECK IN ('shinsotsu','midcareer','other')`, `region_pack`, `starts_on`, `ends_on`, `is_active` | 求职周期。首条为「2027 新卒」。区域包决定阶段枚举与里程碑。 |
| `company` | `company_id`, `name`, `name_norm UNIQUE`, `domain`, `industry`, `size_bucket`, `hq_country`, `notes` | `name_norm` = NFKC + casefold + 去法人后缀（株式会社、(株)、合同会社、Inc.、Ltd.、K.K.、GmbH） |
| `company_alias` | `alias_norm PK`, `company_id`, `lang`, `source` | 来自导入、发件域名、用户确认的匹配；解析器先查别名再模糊匹配 |
| `application` | `application_id`, `campaign_id`, `company_id`, `role`, `role_norm`, `track CHECK IN ('intern','newgrad','midcareer','other')`, `channel`, `auto_status`, `user_status NULL`, `effective_status GENERATED AS COALESCE(user_status, auto_status)`, `status_set_by`, `applied_at`, `last_event_at`, `next_action`, `next_action_due`, `deadline_at`, `excluded_reason`, `job_url`, `portal_url`, `notes` | 状态枚举映射到需求文档的十态。同一公司多流程靠 `track` + `role_norm` 区分，不再用 `UNIQUE(company_id, role_norm)`。 |
| `application_event` | `event_id`, `application_id`, `event_type`, `round_no`, `occurred_at`, `source CHECK IN ('gmail','gcal','linkedin_export','chat','manual','import')`, `source_ref`, `confidence`, `summary`, `user_confirmed`, `UNIQUE(application_id, event_type, occurred_at, source_ref)` | append-only，幂等。`event_type` 含 `entry`, `es_submitted`, `ack`, `viewed`, `web_test`, `assessment`, `interview`, `final_interview`, `scheduling`, `pass`, `rejection`, `offer_informal`（内々定）, `offer`（内定）, `accepted`, `withdrawn`, `portal_check_required`, `followup_needed`, `note` |
| `email_account` | `account_id`, `email`, `provider`, `token_ref`, `history_id`, `enabled` | 多邮箱支持，每账号独立游标 |
| `email_message` | `gmail_id PK`, `account_id`, `thread_id`, `history_id`, `internal_date_ms`, `from_addr`, `from_domain`, `from_name`, `subject`, `snippet`, `body_text NULL`, `has_ics`, `raw_format CHECK IN ('metadata','full')`, `language` | 只有规则命中的邮件取全文；`body_text` 90 天后可清理；FTS5 外部内容表 `email_fts` |
| `email_classification` | `gmail_id PK`, `is_job_related`, `category`, `company`, `role`, `ats`, `stage`, `action_required`, `deadline_iso`, `event_start_iso`, `meeting_url NULL`, `meeting_link_pending`, `portal_url`, `language`, `confidence`, `method CHECK IN ('rule','llm')`, `rule_id`, `model`, `prompt_version`, `input_hash` | 缓存键 `(gmail_id, prompt_version)`；置信度 < 0.7 进待复核 |
| `classification_rule` / `rule_stat` | `rule_id`, `from_pattern`, `subject_pattern`, `body_url_pattern`, `platform`, `category`, `gate`, `region_pack`; `rule_stat(rule_id, n_fired, n_confirmed, n_rejected, last_fired_at)` | 观测精度低于 0.9 的规则降级为「仅提议」 |
| `interview_event` | `interview_id`, `application_id`, `gcal_event_id UNIQUE NULL`, `gmail_id NULL`, `round_label`, `start_at`, `end_at`, `mode CHECK IN ('online','onsite','phone','unknown')`, `meeting_url NULL`, `location`, `status CHECK IN ('confirmed','pending_schedule','cancelled')`, `source` | 确认与待排期分开；无链接则 `meeting_url` 为空，UI 显示「待确認」 |
| `pending_actions` | `id`, `tool`, `args_json`, `summary`, `diff_json`, `candidates_json`, `status CHECK IN ('pending','confirmed','cancelled','expired')`, `created_at`, `expires_at`, `confirmed_via CHECK IN ('host_approval','cli','ui_click','keyword')` | 两阶段写入；邮件匹配到 2 到 3 条候选申请时提议「链接到其中一条」而不是自动新建 |
| `audit_log` | `id`, `ts`, `actor CHECK IN ('user','llm','system')`, `action`, `table_name`, `row_id`, `before_json`, `after_json`, `source` | 所有变更，包括同步引起的 `auto_status` 变化 |
| `source_state` | `source PK`, `transport`, `status CHECK IN ('healthy','degraded','auth_required','unavailable','disabled')`, `cursor`, `last_success_at`, `last_error`, `failure_streak`, `next_retry_at`, `data_as_of` | 看板顶部与 UI 状态条的数据来源 |
| `source_import` + `li_*` | `source_import(id, source, archive_type, zip_name, sha256 UNIQUE, archive_date)`; `li_job_application`, `li_saved_job`, `li_message`, `li_job_seeker_preferences` | LinkedIn 导出原样落地，再映射到 `application` |
| `egress_log` | `ts`, `method`, `host`, `path`, `status`, `allowed` | 见第 4 节 |

**优先级矩阵**（写入 `application` 状态时）：用户 > 规则（精度 ≥ 0.95）> LLM > 导入。任何自动写入若触碰用户改过的行、或要新建申请、或匹配含糊，一律变成 `pending_actions`。

### 5.2 记忆域（Phase 3 起）

| 表 | 关键列 | 说明 |
|---|---|---|
| `profile_facts` | `fact_id`, `category`（role_target, salary_expectation, location_pref, remote_pref, company_type_pref, company_size_pref, industry_pref, tech_pref, culture_pref, work_style, deal_breaker, personality, strength, weakness, language, visa_status, availability, graduation, other）, `key`（点分 slug，如 `salary.base.min_jpy`）, `value_text`, `value_json`, `polarity CHECK IN ('prefer','avoid','neutral','hard_require','hard_exclude')`, `strength`, `confidence`, `source_type CHECK IN ('user_stated','user_confirmed','llm_inferred','outcome_inferred','linkedin_preferences','chat_import','manual')`, `source_ref`, `evidence_quote`, `valid_from`, `valid_to`, `expires_at`, `status CHECK IN ('candidate','active','superseded','rejected','expired')`, `superseded_by` | 双时态 + 取代链。单值类别（年薪、远程、可入职时间、签证）在 `status='active'` 上做部分唯一索引 |
| `company_intel` | `intel_id`, `company_id`, `kind`（headcount_newgrad, interview_format, test_type, culture, contact_style, other）, `text`, `source_type`, `source_ref`, `confidence`, `status` | 「聊天里出现的任何有用情报」中不属于个人画像的部分 |
| `profile_snapshot` | `snapshot_hash PK`, `facts_json`, `rendered_md`, `created_at` | 岗位评分与搜索运行都盖上快照哈希，画像变了就知道该重评 |
| `extraction_runs` | `run_id`, `source_type`, `source_ref`, `provider`, `model`, `prompt_version`, `schema_version`, `input_hash`, `output_json`, `status`, `cost_usd`, `UNIQUE(source_type, source_ref, prompt_version, schema_version)` | 抽取幂等 + 成本审计 |
| `chat_sessions` / `chat_turns` / `episode_summaries` | 会话（provider, model）、轮次（role, content, modality text/voice, asr_confidence, tokens）、摘要（summary_md, key_facts_json, open_loops_json） | Phase 5 自有 UI 后才有本地聊天历史；之前聊天在宿主里，只有确认过的事实进库 |
| `memory_fts` / `chunks` + `vec0` | FTS 双表；后期 `chunks(kind, ref_id, text, embedding_model, dims)` + sqlite-vec 表 | 混合检索 RRF 融合 |

### 5.3 搜索域（Phase 4 起）

| 表 | 关键列 | 说明 |
|---|---|---|
| `watch_target` | `id`, `kind`（greenhouse, lever, ashby, smartrecruiters, workable, recruitee, teamtailor, rippling, sitemap, rss, websearch）, `company_id`, `identifier`, `poll_interval_min`, `etag`, `last_polled_at`, `enabled` | 从已申请公司自动播种 + 用户添加 |
| `job_posting` | `id`, `canonical_id`, `source`, `source_id`, `source_url`, `apply_url`, `title`, `title_norm`, `company_name`, `company_norm`, `city`, `country_code`, `remote_type`, `employment_type`, `salary_min/max/currency/period`, `salary_basis`, `description_text`, `language`, `posted_at`, `first_seen_at`, `last_seen_at`, `is_active`, `content_hash`, `attribution_text`, `raw_json`, `UNIQUE(source, source_id)` | 一条来源一条记录 |
| `job_canonical` | `id`, `blocking_key`（sha1(company_norm|title_norm|country|city_or_remote)）, `best_posting_id`, `source_count`, `status CHECK IN ('open','closed')`, `verification CHECK IN ('confirmed_open','to_verify','special_lead','excluded')`, `verified_at`, `excluded_reason`, `official_url` | 招聘状态四分落在这里 |
| `job_judgement` | `canonical_id`, `fit_score`, `fit_reasons_json`, `gaps_json`, `growth_notes`, `tradeoffs`, `requires_internship_first`, `unconfirmed_json`, `model`, `prompt_version`, `profile_snapshot_hash` | 个人判断与岗位事实分表；UI 标注「分析判断，非录用概率」 |
| `job_interactions` | `canonical_id`, `action CHECK IN ('shown','ignored','saved','dismissed','applied','withdrawn','compared')`, `reason_text`, `ts` | 「永不重复展示」是这张表上的 SQL 谓词 |
| `preference_weights` / `job_features` / `job_scores` / `fit_signals` / `search_runs` | 陈述权重与学习权重、每岗位特征、硬过滤结果 + 软分 + LLM 重排解释、公司侧结果信号、每次搜索的画像快照与来源额度消耗 | 学习循环所在 |

---

## 6. 信息源接入策略

### 6.1 Gmail

- 授权：Google Cloud 项目 → 启用 Gmail API 与 Calendar API → Auth Platform 用户类型 External → 添加本人为测试用户 → 一次性申请两个范围 → 建 Desktop 类型 OAuth 客户端 → `jobpilot auth google` 走 loopback + PKCE → 验证通过后点击「Publish app」（不提交验证）→ 删除旧令牌重新授权。第一阶段退出标准之一是**令牌 8 天浸泡测试**通过。
- 回填：`messages.list q='newer_than:180d -category:promotions -category:social -in:spam -in:trash'`，每页 500；`messages.get format=metadata`（From、To、Reply-To、Sender、Subject、Date、Message-ID、In-Reply-To、References、List-Unsubscribe）；只有规则门放行的邮件再取 `format=full`。约 5000 封邮件耗 10 万配额单位，远低于每用户每分钟 6000 的上限。
- 增量：`users.history.list(startHistoryId, historyTypes=messageAdded)` 每 90 秒；404 则从最新 `internalDate` 起重同步；429 / 403 指数退避到 64 秒。
- 不做：任何写范围、标签、已读状态、草稿、附件（后期只读取 offer PDF 可考虑）、IMAP、Pub/Sub 推送。

### 6.2 Google Calendar

- `calendar.events.readonly`，`events.list(calendarId='primary', timeMin=now-90d, singleEvents=true)` 取 `nextSyncToken`，之后同一节拍增量；410 则清空重拉。
- 与申请关联：参会者或组织者域名 + 标题关键词（interview | 面接 | 面談 | 面试 | screen | onsite）；`conferenceData.entryPoints` 取会议链接，没有就留空。
- 与邮件里的 `.ics` 按 `iCalUID` 去重。Calendly 邮件（`notifications@calendly.com`）与 Google Calendar 邀请邮件（`calendar-notification@google.com`）也产出面试事件。
- 本地生成 `.ics` 文件供用户手动导入日历，这不是外部写操作，用于把マイページ预约同步回日历。

### 6.3 LinkedIn

- 通知邮件：`from:(@linkedin.com OR @e.linkedin.com OR @el.linkedin.com)`，按发件人 + 主题模板归类为 application_sent / viewed / resume_downloaded / rejected / message_received / job_alert；从 `/comm/jobs/view/(\d+)` 提取岗位 ID。应用内提示用户开启 LinkedIn 邮件通知（申请更新逐条、岗位提醒每日、消息通知）。
- 官方导出：应用内清单打开 `linkedin.com/mypreferences/d/download-my-data`，建议 Jobs 类每周、完整档每月；`jobpilot import linkedin <zip>`，表头驱动 CSV 解析，自然键幂等 upsert，原 ZIP 归档到 `imports/linkedin/<日期>/`。UI 显示「LinkedIn 数据截至 <归档日期>」。
- 提醒用户对 LinkedIn 的「Did you apply?」一律回答「是」，外部申请才会进入导出。
- 不做：OIDC 登录（单用户无价值）、任何抓取、任何第三方「本人数据」服务。粘贴的 `linkedin.com/jobs/view/{id}` 链接只作为手动岗位记录，不发请求。

### 6.4 日本就活平台（区域包提供规则）

三级发件人：① 平台中继（`mynavi.jp` 家族、リクナビ、`offerbox.jp`、`wantedly.com`、`linkedin.com`）只能确定平台，公司要从主题 / 正文解析；② 编码公司的 ATS 地址（`<公司>@snar.jp`、`@<slug>.hrmos.co`、`<tenant>@myworkday.com`、i-web 多为公司自有域名）；③ 固定供应商地址（Greenhouse、Lever、Ashby、SmartRecruiters、Workable、HERP、TalentIO、ジョブカン、SPI `noreply_tc@arorua.net`、Calendly、Google Calendar、Zoom）。

正文里的 URL 主机同样是强信号：`*.snar.jp`、`*.i-web.jpn.com`、`mypage.30NN.i-webs.jp`、`job.axol.jp`、`www.e2r.jp/ja/*`、`apply.workable.com/j/*`、`herp.careers/v1/*`、`open.talentio.com/r/1/c/*`、`*.myworkdayjobs.com`、`*.e-exams.jp`。

「マイページをご確認ください」类存根 → `portal_check_required` 事件 + 门户链接 + 一键 / 语音回填。「今後のご連絡は LINE にて」→ 标记该申请渠道为 LINE，提示手动记录。

### 6.5 岗位来源

| 层 | 来源 | 方式 |
|---|---|---|
| 1 公司观察名单 | Greenhouse `boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`、Lever `api.lever.co/v0/postings/{site}?mode=json`、Ashby `api.ashbyhq.com/posting-api/job-board/{name}`、SmartRecruiters `api.smartrecruiters.com/v1/companies/{id}/postings`、Workable `apply.workable.com/api/v1/widget/accounts/{subdomain}?details=true`、Recruitee `{company}.recruitee.com/api/offers/`、Teamtailor `{company}.teamtailor.com/jobs.rss`、Rippling | 从公司 careers 页自动识别 ATS；每 4 小时轮询；ETag |
| 2 日本英文岗位站 | TokyoDev、Japan Dev | 每日 sitemap 差分 + JobPosting JSON-LD |
| 3 邮件岗位提醒 | LinkedIn、Indeed、Wantedly、Bizreach、マイナビ、リクナビ、ONE CAREER、外資就活 的提醒 / スカウト邮件 | `gmail.readonly` 已覆盖，解析为 `job_posting(source='gmail_alert')`；Wantedly / Bizreach 内容只存元数据，不送 LLM（条款禁止用于 AI） |
| 4 提供商网页搜索 | Anthropic web search 工具 / OpenAI Responses web search | 只读；覆盖免费 API 到不了的日本新卒信息；结果必须回填官方来源与核验日期 |
| 5 可选聚合器 | Adzuna（每天 250 次，署名）、JSearch（每月 200 次，`country=jp`） | 默认关闭，同一 GET 传输层 |
| 排除 | 抓取 LinkedIn / Indeed / Glassdoor / Wantedly / Bizreach / doda / Green / 任何登录站；python-jobspy；HelloWork | — |

去重：`UNIQUE(source, source_id)` → 规范化申请 URL → `blocking_key` + rapidfuzz `token_set_ratio ≥ 90`；已申请 / 已排除 / 已忽略的规范岗位在 SQL 层排除。

---

## 7. 分类与解析管线

```
邮件元数据 ──▶ 第一层 确定性发件人 / URL 规则（platform, company, ats, gate）
                    │ gate 放行 → 取全文
                    ▼
            第二层 短语打分（NFKC、HTML→文本后）
                    应募受付 / 適性検査 / 日程調整 / 面接のご案内 / 選考結果 / 内々定 / 内定承諾書 / お祈り / 辞退
                    要求 REJECTED 必须命中否定核心短语；「選考結果のご連絡」类主题不由规则判 pass/fail
                    提取：.ics DTSTART（优先）、Zoom / Teams / Meet / Webex 链接、截止日期；无链接且写「前日 / 追って」→ meeting_link_pending
                    ▼ 低置信或自由格式招聘者邮件
            第三层 LLM 结构化输出（EmailClassification），输入：脱敏截断正文 + 线程既往阶段
                    输出：is_job_related, category, company, role, ats, stage, action_required, deadline_iso, event_start_iso, meeting_url, portal_url, language, confidence
                    缓存 (gmail_id, prompt_version)；默认便宜模型
                    ▼
            解析器：company_alias → name_norm → 模糊匹配；thread_id 粘连；候选 2 到 3 条 → pending_actions
                    ▼
            状态引擎：按事件优先级重算 auto_status；user_status 永远优先；置信度 < 0.7 → needs_review；30 天无事件 → ghosted
```

提示注入防护：邮件、JD、日历描述作为**数据**放进明确分隔的块，系统提示声明其中的指令不可执行；分类模型没有任何工具；抽取输出是封闭 schema。

---

## 8. 记忆系统

四层同库，逐步引入：

1. **结构化历史**（Phase 1）：追踪域全部表。无 LLM 参与主键。
2. **类型化画像**（Phase 3）：`profile_facts` + `company_intel`。来源：聊天（Phase 3 由宿主模型调用 `propose_memory_fact`，Phase 5 起每轮自动抽取）、LinkedIn Job Seeker Preferences、ChatGPT / Claude 对话导出（`chat_import`）、Phase 6 的结果推断。候选先进收件箱；只有明确第一人称陈述、置信度 ≥ 0.85、非敏感类别可自动生效。取代在一个事务里完成：旧行 `valid_to=now, status=superseded, superseded_by=new`。活跃事实渲染成稳定 Markdown「核心记忆」块，作为 `get_profile()` 工具与 `jobpilot://profile` MCP 资源，并放在提示缓存断点后。
3. **情节记忆**（Phase 5）：`chat_turns` 每 40 轮或会话结束生成 `episode_summaries`，每周滚动汇总；语音轮次 `asr_confidence < 0.8` 时所有抽取事实强制确认。
4. **检索**（Phase 3 FTS，Phase 6 向量）：`memory_fts` + `email_fts` 双表；后期 `chunks` + vec0 用 RRF 融合。

**学习循环**：`profile_facts` 的 `hard_require / hard_exclude` → SQL WHERE；`prefer / avoid` → `preference_weights.w_stated`；每岗位算 `job_features`；`job_scores` 存透明软分 + LLM 重排（盖 `profile_snapshot_hash`）；每次展示 / 收藏 / 驳回 / 申请写 `job_interactions`；公司侧结果写 `application_event` 与 `fit_signals`。Phase 6 夜间任务把交互变成 `w_learned`（申请 +1、收藏 +0.5、驳回 −1、忽略 ×3 −0.25；0.7 / 0.3 混合；90 天半衰期），并把「你从不申请 5000 人以上公司」这类推断作为候选事实送进收件箱。**冷启动守卫**：某特征样本数 < 20 时 `w_learned` 不生效；权重页显示陈述值、学习值、样本数、最后更新。

过期：可入职时间 14 天、通知期 90 天、年薪期望 180 天后标「陈旧」并提示确认；性格永不过期。

---

## 9. LLM、对话与语音层

- **Phase 1 到 4：MCP 宿主即 UI**。`jobpilot-mcp`（stdio）暴露只读工具 `list_pipeline(status?, limit≤50)`、`get_application(id)`、`search_emails(query, limit≤20)`、`get_sync_status()`，Phase 2 起加 `propose_status_update / propose_log_application / propose_note / propose_exclude / propose_memory_fact / confirm_action / cancel_action / list_pending_actions`，Phase 3 加 `list_interviews / get_next_interview / get_profile / search_memory`，Phase 4 加 `search_jobs / get_job / evaluate_posting / propose_save_job / propose_dismiss_job`。工具描述里嵌入落地规则（只答工具结果、引用 `[app:id]`、查不到就说没有），宿主侧再放一份项目指令（Claude Desktop 项目、Claude Code `CLAUDE.md`、Codex `AGENTS.md`）。`tools/list` 顺序确定，利于提示缓存。
- **Phase 5：自有对话面板**。pydantic-ai `Agent`，`FunctionToolset` 复用同一注册表，写操作 `requires_approval=True` → `DeferredToolRequests` → 确认卡片 → `DeferredToolResults`；`output_type=[str, DeferredToolRequests]`；`UsageLimits(tool_calls_limit=8)`；Anthropic 开启指令与工具定义缓存；SSE 流式并每 15 秒心跳。
- **语音**：按住说话，`SpeechRecognition` 语言切换 ja-JP / zh-CN / en-US；转写填入聊天框，带 `modality='voice'`；`ui_command(navigate | filter | open)` 由前端执行；确认关键词 `re.fullmatch(confirm|yes|はい|確認|确认|是)` 由程序匹配。可选 `/api/voice/transcribe` 走 OpenAI 转写（`keywords` 用库里的公司名播种）。
- **语音可操作动作清单**（每条都有无 LLM 的确定性意图后备）：显示看板 / 按状态筛选 / 打开某公司申请 / 下一个面试 / 本周截止 / 改状态 / 记录申请 / 记录备注 / 门户回填 / 评估这条岗位 / 收藏或驳回岗位。
- **落地回归套件**：一组固定问题与语音指令 → 期望工具调用与期望「无记录」回答，两家提供商各跑一遍，每次改提示词或换模型后运行。
- **模型选择**：分类与批量抽取默认便宜档（如 Claude Haiku 级），聊天默认高档（如 Claude Opus / Sonnet 级），GPT 侧对应配置；具体 ID 以 `platform.claude.com` 与 OpenAI 官方 models 页为准，写在 `.env` / 设置里。

---

## 10. 区域包

```
src/jobpilot/regions/
  base.py        # RegionPack 协议：stage_taxonomy(track), milestones(campaign), sender_rules(), url_rules(), salary_parsers(), phrase_lists(lang)
  global_en/     # 默认包：通用 ATS 发件人、英文短语、通用阶段
  japan/         # 日本包：mynavi/rikunabi/onecareer/... 发件人、snar/i-web/axol URL、新卒与中途阶段、2027 卒里程碑、salary_basis 解析、日语短语表
```

规则表与短语表是数据文件（YAML / JSON），带 `verified: true|false` 与来源 URL；未核实的条目只提议不自动生效。新增国家 = 新增目录，不改核心代码。

---

## 11. 部署与运行

| 阶段 | 部署形态 | 成本 |
|---|---|---|
| 开发与第一版 | 本机 Windows 11：uv venv，`jobpilot watch` 或 uvicorn 绑定 127.0.0.1；稳定后用 WinSW 注册为服务（登录前启动、更新重启后自恢复）；`powercfg /change standby-timeout-ac 0` 防止现代待机冻结进程 | 0 |
| 手机访问 | 同一台机 + Tailscale Personal `tailscale serve --bg <port>` 得到 HTTPS（麦克风与 PWA 需要安全上下文） | 0 |
| 需要「关机也同步」 | 东京 5 美元 VPS（Vultr / Linode / ConoHa）或 Fly.io nrt 机器 + 卷，跑同一镜像，仅经 Tailscale 访问，夜间 `VACUUM INTO` + rclone 异地备份；隐私优先替代：家用 N100 迷你主机；机会主义：Oracle Always Free A1（东京 / 大阪，1 OCPU / 6 GB 以避开闲置回收） | 0 到 5 美元 / 月 |
| 浏览器直达（可选） | Cloudflare Tunnel + Access 免费档做登录墙 | 域名约 10 美元 / 年 |

现在就落实的决策：`pydantic-settings` 单一 `Settings`（前缀 `JOBPILOT_`：`DATA_DIR`、`DATABASE_PATH`、`HOST/PORT`、`BASE_URL`、`AUTH_MODE=none|password|proxy`、`TZ`、模型 ID、轮询间隔）；单一数据目录（数据库、加密令牌、导入、备份）；所有同步任务是幂等函数并暴露为 CLI 子命令（`jobpilot sync gmail`），调度器只是薄胶水；游标存库；单进程单写入者显式声明 `workers=1`；Dockerfile（`python:3.12-slim`，`uv sync --frozen`，非 root，`/data` 卷，`/healthz`）多架构构建；结构化 JSON 日志到 stdout，不含正文与地址；`jobpilot backup` / `restore`（SQLite online backup API）。

---

## 12. 安全与隐私细则

- **令牌**：Windows 用 DPAPI 加密文件（`win32crypt`），Linux 用 Fernet 加密文件（密钥来自环境或 keyring）；永不明文、永不入库、永不进日志。诚实说明 DPAPI 是用户级保护：同一用户下的任何进程都能解密。
- **发给 LLM 前**：`pii_aliases` 表把邮箱、电话、URL、人名替换为稳定别名；正文截断 4k 字符；Wantedly / Bizreach 来源文本不外发。
- **保留**：非求职邮件只存元数据并在 30 天后清理；求职邮件正文在派生事件后 90 天清理；`li_message` 与 `Connections.csv` 提供最小化导入选项（仅招聘者会话、连接人邮箱哈希）与一键擦除。
- **日志**：MCP 宿主日志（`%APPDATA%\Claude\logs\mcp-server-jobpilot.log`）会包含工具返回值，工具返回值本身就应脱敏；应用日志不记主题与地址。
- **提供商条款**：文档提醒用户检查 Anthropic / OpenAI 账号的数据保留与训练设置；消费级宿主（Claude Desktop、Codex）与 API 的政策不同。
- **Google Cloud 项目生命周期**：不绑定账单、只启用两个 API、限制 OAuth 客户端、定期在 Google 账号「第三方访问」中检查授权、求职结束后撤销并删除项目。
- **供应链**：锁文件固定版本；处理令牌的依赖开启漏洞扫描；把数据目录排除在 OneDrive 等云同步之外。
- **测试夹具**：提供从真实邮箱生成匿名化夹具的工具（保留主题模板、替换公司与人名），保证仓库中没有 PII。

---

## 13. 仓库结构（目标）

```
JobPilot/
  pyproject.toml            # uv_build；[project.scripts] jobpilot / jobpilot-mcp；dev 组 pytest ruff pyright
  uv.lock
  .env.example              # 非机密配置示例
  Dockerfile  compose.yaml
  CLAUDE.md                 # 面向 AI 协作者的约束与指引
  docs/                     # 本文档集 + research/ + ref/
  src/jobpilot/
    settings.py  secrets.py  cli.py  mcp_server.py
    store/{db.py, repo.py, migrations/0001_init.sql ...}
    connectors/{gmail/, gcal/, linkedin_archive/, boards/, websearch/}   # 只读包
    classify/{rules.py, phrases.py, llm.py, schemas.py, prompts/}
    services/{pipeline.py, resolve.py, status.py, reminders.py}
    actions.py              # propose / confirm / audit
    memory/{facts.py, extract.py, render.py, fts.py}
    search/{dedupe.py, scoring.py, learn.py}
    regions/{base.py, global_en/, japan/}
    tools/{registry.py, readonly.py, local_mutations.py}
    web/{app.py, api/}
  frontend/                 # React + TS + Vite + Tailwind（Phase 2 起）
  tests/
    test_readonly_guard.py  test_rules.py  test_pipeline.py  fixtures/emails/*.json（匿名化）
运行时数据（仓库外）：JOBPILOT_DATA_DIR/{jobpilot.db, secrets/, imports/, backups/, logs/}
```