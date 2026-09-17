# JobPilot 分阶段路线图

| 项目 | 内容 |
|---|---|
| 状态 | 草案 v0.2（2026-09-16） |
| 前置 | [REQUIREMENTS.md](REQUIREMENTS.md) · [ARCHITECTURE.md](ARCHITECTURE.md) |

原则：每个阶段独立可用；先把「每个选考流程的状态自动保持最新」做对，再叠加控制、日历、记忆、搜索、自有对话、学习循环、对外发布。估时按一个人晚上和周末的节奏，评审一致认为原提案偏乐观，这里已上调约三成。

---

## 0. 阶段总览

| 阶段 | 名称 | 交付物 | 估时 |
|---|---|---|---|
| 0 | 骨架 | `src/` 布局、配置、密钥（含 DPAPI 令牌后端）、迁移器、区域包协议、CI 基线 | 1 到 2 个晚上 |
| 1 | 收件箱到看板 | Gmail 只读同步 → 三层分类 → SQLite → `jobpilot board` + 只读 MCP | 7 到 9 个晚上（约 1.5 到 2 周，含验收与浸泡） |
| 2 | 可信与可控 | 提议 / 确认写入、LinkedIn 导出导入、待复核队列、提醒、备份、`DESIGN.md`、只读看板 Web UI | 2 周 |
| 3 | 日历与记忆 v1 | Calendar 面试事件、`profile_facts` 与收件箱、按周期类型的引导问卷、历史聊天导入、响应式验收 | 1.5 到 2 周 |
| 4 | 岗位搜索 v1 | 只读岗位源、目击台账与核验、去重、硬过滤 + 软分 + LLM 重排、研究请求、评估粘贴岗位、并排比较 | 2 到 3 周 |
| 5 | 应用内对话与语音 | 提供商切换、流式、确认卡片、按住说话、语音操作、会话记忆与情节摘要 | 3 周 |
| 6 | 学习循环与加固 | 结果学习、语义检索、可选加密、清理策略、通知 | 持续，核心 2 周 |
| 7 | 对外发布 | 引导向导、Docker、i18n、双语文档、文档脱敏与 PII 守卫、许可 | 1 到 2 周 |

---

## Phase 0 · 骨架

**目标**：把空的 uv 项目变成可打包、可测试、可配置的应用，之后每个阶段都是「加一个迁移 + 一个服务 + 一个 CLI 子命令」。

范围：
- `uv self update`；`pyproject.toml` 加 `[build-system]`（`uv_build`）、`[project.scripts] jobpilot / jobpilot-mcp`、dev 依赖组（pytest、ruff、pyright）、项目元数据（描述、README；许可与作者待 Q7 / Q8 / Q13 决定）。
- `src/jobpilot/settings.py`（pydantic-settings，`JOBPILOT_` 前缀，含 `CAMPAIGN_NAME / _KIND / _REGION_PACK`）、`secrets.py`（`SecretStore` 协议：keyring 存短 key、DPAPI 文件存令牌、env 后端供测试；槽位白名单）。令牌从第一次落盘起就加密。
- `store/db.py`（连接工厂：WAL、外键、busy_timeout、迁移运行器）、`migrations/0001_init.sql` 空骨架。
- `regions/base.py` 协议 + `global_en` 与 `japan` 空目录。
- `campaign` 表 + `jobpilot campaign add --name --kind --region-pack --starts --ends`；迁移文件不含种子数据，作者用命令或 `.env` 创建自己的周期。
- `.env.example`、`Dockerfile`、`compose.yaml`、pre-commit（ruff、pyright、`scripts/check_pii.py`）。

退出标准：`uv run jobpilot --help` 可用；`uv run pytest` 通过一个冒烟测试；`uv run ruff check` 与 `pyright` 干净；`campaign add` 创建一条周期并能列出。

---

## Phase 1 · 收件箱到看板（MVP）

**目标**：过去 180 天在 Gmail 留下痕迹的每一个选考流程出现在状态看板上，阶段、下一步截止、最近事件正确；新邮件 2 分钟内更新看板；外部写操作在结构上不可能；Claude Desktop / Claude Code / Codex 能回答「我在 X 公司进行到哪了」。

范围：
- Google Cloud 项目：启用 Gmail 与 Calendar API；Auth Platform External + Testing，本人为测试用户；**一次性申请** `gmail.readonly` 与 `calendar.events.readonly`；Desktop 客户端。`jobpilot auth google`（loopback + PKCE），落盘前断言范围子集，启动时在线核对 `tokeninfo`。
- `ReadOnlyHttp` 传输层；`connectors/gmail/{auth,readonly_http,sync,parse}.py`。
- 迁移 0001：`campaign`、`company`（含 `is_current_employer`）、`company_alias`、`application`（12 态枚举）、`application_event`、`email_account`、`email_message` + `email_fts`、`email_classification`、`classification_rule`、`rule_stat`、`pii_aliases`、`audit_log`、`source_state`。
- `jobpilot sync --backfill-days 180`：元数据全取，规则放行的邮件取全文；按 ≤ 50 封一批并退避；存最大 `historyId`。
- `jobpilot senders`：发件域名 / 地址 / 主题模板统计。只把平台 / 供应商级的域名与 URL 正则写入 `regions/japan/senders.yaml`（每条附公开来源 URL）；从本人收件箱观察到的具体公司租户写本地 `JOBPILOT_DATA_DIR/rules/user_senders.yaml`（不入库）。
- `classify/rules.py` + `phrases.py`：日本包与全球包的发件人、URL、日语 / 中文 / 英文短语表，带 `verified` 标记；`classify/llm.py`：pydantic-ai 结构化输出，PII 别名 + 4k 截断，按 `(gmail_id, prompt_version)` 缓存，记录成本；提示注入防护（不可信文本作为数据分块）。
- `services/{resolve,pipeline,status}.py`：别名 → 归一化名 → 模糊匹配；thread 粘连；幂等事件插入；`auto_status` 重算；现雇主域名例外；`portal_check_required` 事件；置信度 < 0.7 进待复核；14 天 → `followup_needed`；30 天 → `is_ghosted`。
- `jobpilot board`（按 `effective_status` 分组、JST、下一截止列、待复核与 ghosted 标记、顶部信息源状态）、`jobpilot show <id>`、`jobpilot watch --interval 90`。
- `mcp_server.py`：`MCPServer('jobpilot')`，只读工具 `list_pipeline / get_application / search_emails / get_sync_status`，带 `ToolAnnotations` 只读提示（从 `mcp.types` 导入，字段名以 2.x 源码为准），返回值经 `pii_aliases` 脱敏，工具描述内嵌落地规则；注册到 Claude Desktop（`%APPDATA%\Claude\claude_desktop_config.json`，uv 绝对路径）、Claude Code（`claude mcp add`）、Codex（`codex mcp add`）。
- `tests/test_readonly_guard.py`、`tests/test_rules.py`（匿名化夹具，由 `jobpilot fixtures anonymize` 生成的最小版本）。
- 周末：点击「Publish app」（In production，不提交验证），删除令牌重新授权；设一个 8 天后的日历提醒检查令牌是否仍然有效。

不做：任何写范围、IMAP、Pub/Sub；LinkedIn 除 Gmail 通知邮件外的一切；Calendar 同步（只申请范围）；Web UI；语音代码；记忆；搜索；提议 / 确认工具；数据库加密（SQLCipher）；ORM；APScheduler。

退出标准：
- 看板列出你记得的过去 6 个月每一个流程；随机抽 30 条，≥ 27 条状态与公司 / 职位正确。
- `jobpilot watch` 运行时，新 ATS / 招聘者邮件 2 分钟内成为看板事件。
- 只读守卫测试通过：传输层拒绝非 GET；connectors 无写符号；无 smtplib / imaplib / playwright / linkedin_api 导入；范围列表不变。
- MCP 工具返回值不含原始邮箱 / 电话 / 人名。
- 令牌浸泡：发布后重新授权的令牌在第 8 天仍能同步；若失败，记录并退回 Testing 每周授权。
- Claude Desktop 与 Codex 都能引用 `[app:id]` 回答「我在面试哪些公司，本周截止什么」；语音侧用 Win+H 听写验证。
- 实测并记录：Claude Desktop 语音模式是否会调用本地 MCP 工具。
- 180 天回填的 LLM 费用有记录且约 15 美元以内。

---

## Phase 2 · 可信与可控

**目标**：看板可信、可改；LinkedIn 官方导出补上 Gmail 看不到的申请；用户可通过聊天 / 语音 / CLI 改状态、记申请，全部经确认门；有每日摘要与提醒；有备份；有设计文档；有一个每天愿意打开的只读 Web 看板。

范围：
- **`docs/DESIGN.md`（前置交付物）**：JobPilot 自己的信息架构（侧栏导航树：看板 / 岗位 / 面试 / 记忆收件箱 / 待复核 / 信息源 / 设置）、5 到 8 条核心用户流程（新邮件 → 看板变更 → 复核；粘贴 JD → 评估 → 记录申请；语音改状态 → 确认卡片；门户回填；多周期切换；研究请求 → 回填）、页面与组件清单、design tokens（色板、字号、间距、状态色，含金色「待确认」）。
- 迁移 0002 / 0003：`source_import` + `li_*`、`pending_actions`、`egress_log`。`jobpilot import linkedin <zip>`（表头驱动、自然键幂等、原 ZIP 归档、Easy Apply 合并为 `application(channel='linkedin_easy_apply')`）；应用内下载清单与「Did you apply? 一律答是」提示；LinkedIn 邮件通知设置提醒。
- `actions.py` 与提议 / 确认 MCP 工具；CLI 对应 `set-status / log / note / exclude / merge / split`；优先级矩阵；含糊匹配 → `candidates_json`。
- `jobpilot review`：走查待复核分类，接受 / 拒绝回写 `user_confirmed` 与 `rule_stat`；规则三档精度门槛生效。
- `jobpilot today`：今日与本周截止、待排期、需跟进、门户待查看；Windows toast 可选。
- 密钥与出站：Linux Fernet 令牌后端；`egress_log` + `jobpilot egress-report`。
- 登录自启（schtasks ONLOGON）；日志轮转。
- `jobpilot backup` / `restore`（SQLite online backup API 到 `backups/`，保留 14 份）；文档说明把数据目录排除在云同步之外。
- **只读 Web 看板**：FastAPI（127.0.0.1）+ React / Vite 单页，按 `DESIGN.md` 落地：pipeline 看板、申请详情（事件、关联邮件主题、门户链接）、截止与待办列表、信息源状态条。先做桌面端。不含聊天、不含写操作（写操作仍走 CLI / MCP 确认）。
- 匿名化夹具生成器 `jobpilot fixtures anonymize` 完整版。

不做：Calendar、记忆抽取、岗位搜索、应用内聊天、语音代码、LinkedIn 任何网络访问。

退出标准：
- `DESIGN.md` 评审通过并被前端实现引用。
- 同一 ZIP 导入两次零新增；新 ZIP 只增增量；每条 Easy Apply 申请都在 `application` 中并链接到 Gmail 事件。
- 在 Claude Desktop 说「把 Acme SWE 标为落选」产生提议摘要，确认前无变化，确认后 `audit_log` 有前后值。
- 重启后 1 分钟内 `watch` 自动运行。
- 浏览器打开看板，数据与 CLI 一致，页面在 1 秒内渲染 200 条申请。
- `egress-report` 报告零非 GET（令牌刷新与 LLM 端点除外）。

---

## Phase 3 · 日历与记忆 v1

**目标**：面试成为一等对象（确认 vs 待排期，JST，链接或明确「待确认」）；应用开始通过可审阅的收件箱记住画像与偏好；看板与面试在手机上可用。

范围：
- 迁移 0004：`interview_event`；`connectors/gcal/sync.py`（syncToken 增量，410 重拉）；与申请关联；Calendly 与日历邀请邮件（Sender 头识别）产出事件；本地 `.ics` 生成供手动导入。
- MCP 工具 `list_interviews / get_next_interview`；看板与 Web UI 增加「面试」区（月份概览 + Agenda）。
- 迁移 0005：`profile_facts`（含在职类别）、`company_intel`、`profile_snapshot`、`extraction_runs`、`memory_fts`；`memory/{facts,render}.py`；取代逻辑；过期默认值。
- MCP 工具 `get_profile / search_memory / propose_memory_fact`；资源 `jobpilot://profile`。
- 种子：按 `campaign.kind` 分组的引导问卷（新卒组 / 中途组）→ 候选事实；LinkedIn Job Seeker Preferences → 候选事实；**ChatGPT / Claude 对话导出导入**（`jobpilot import chat <file>`）→ 同一抽取管线 → 收件箱。
- `jobpilot memory inbox` CLI 与 Web UI 收件箱页。
- 多邮箱：`email_account` 多行，每账号令牌与游标。
- 响应式验收：看板与面试 Agenda 在 390 px 宽度可用；`tailscale serve` 手机访问文档。

不做：embedding、自动每轮抽取（需自有聊天）、情节摘要、岗位搜索。

退出标准：
- 过去 90 天主日历里每个面试邀请都成为 `interview_event` 并链接到正确申请；邮件写「オンライン面接」无链接时 `meeting_url` 为空且 UI 显示待确认。
- 在 Claude Desktop 说「希望年収は 600 万以上、東京勤務、リモート可が理想」产生三条候选事实；确认后 `get_profile()` 返回；再说一个不同年薪后旧事实被取代且 `valid_to` 有值。
- 日历同步从不发出非 GET（守卫测试扩展到 Calendar 服务）。
- 手机通过 Tailscale 打开看板与面试页可正常使用。

---

## Phase 4 · 岗位搜索 v1

**目标**：从条款干净、无需登录、只读的来源发现并排序新岗位，使用画像事实与申请历史，永不重复展示已申请或已驳回的岗位，每条岗位带来源、核验日期与目击记录。

范围：
- 迁移 0006：`watch_target`、`job_posting`（含 `hiring_track`、`industry`、`tags_json`、`deadline_at`）、`job_canonical`、`job_sighting`、`job_judgement`、`job_note`、`job_interactions`、`research_request`、`job_features`、`job_scores`、`preference_weights`、`fit_signals`、`search_runs`；`application.canonical_id`。
- `connectors/boards/`：`GetOnlyTransport`（限速、ETag、robots）；Greenhouse / Lever / Ashby / SmartRecruiters / Workable / Recruitee / Teamtailor / Rippling 连接器 + ATS 自动识别，每次轮询写 `job_sighting`；Gmail 岗位提醒解析为 `job_posting`；`connectors/websearch/`（Anthropic / OpenAI 提供商网页搜索工具作为只读发现源）；TokyoDev / Japan Dev 在核实条款后加入。
- 核验：连续 3 次未见 → 关闭并降为待核实；`jobpilot job verify <id>` 手动目击；`jobpilot jobs cleanup` 把失效岗位移入排除记录并保留原因 / 时间 / 来源。
- `search/dedupe.py`、`search/scoring.py`（SQL 硬过滤含现雇主排除 → 陈述权重软分 → LLM 重排前 20，结构化输出含匹配理由、缺口、AI 相关度、成长性、是否需先实习，盖画像快照哈希）。
- `search/research.py`：研究请求模板（搜索新岗位 / 复核清单 / 可主动敲门的公司与团队 / 清理失效岗位）→ 提示词 → 用户外部执行 → 粘贴结构化结果 → 解析为 `job_posting(source='llm_research')` 或特别线索 → 待复核。
- `evaluate_posting(url_or_text)`：粘贴 JD → 判断 → 存手动岗位 → 可选记录申请。
- MCP 工具 `search_jobs / get_job / evaluate_posting / propose_save_job / propose_dismiss_job / create_research_request / import_research_result`；Web UI 岗位列表、卡片（收藏 / 加入比较 / 前往官方入口 / 备注）、详情、最多三个并排比较、研究请求页。
- 招聘状态四分与核验日期；「复核官方页面」一键跳转。
- 可选：Adzuna、JSearch，默认关闭。

不做：抓取任何登录站；Workday `cxs`（待裁定）；学习权重；embedding。

退出标准：
- `jobpilot jobs` 列出排序结果，每条硬过滤失败有解释，无一条与现有申请或已驳回岗位重复，每行有来源署名、核验日期与最近目击时间。
- 驳回 5 条后再搜索永不再现；收藏后记录申请能自动关联到规范岗位。
- 关闭的岗位在 3 个轮询周期内被标记为待核实并可一键移入排除记录。
- 一次研究请求从生成提示词到结果回填进待复核在 10 分钟内完成。
- 24 小时内所有岗位源请求为 GET / HEAD；每源配额未超。
- 粘贴一条 JD 链接，30 秒内得到匹配判断与缺口，并可一键记录申请。

---

## Phase 5 · 应用内对话与语音

**目标**：不再依赖宿主：本地 Web UI 内置对话面板，Claude / GPT 下拉切换，流式，确认卡片，ja / zh / en 按住说话，语音驱动看板，会话持久化并自动喂给记忆抽取。

范围：
- `web/app.py` lifespan（DB、迁移、APScheduler 3.11 取代 `watch`）、`/api/chat` SSE、`/api/events`。
- pydantic-ai `Agent` 复用工具注册表；写操作 `requires_approval=True`；确认卡片；`ui_command` 由前端执行；确认关键词程序匹配。
- 迁移 0007：`chat_sessions / chat_turns / episode_summaries`；每轮后 `MemoryExtraction` 提议进收件箱（D15 例外可自动生效并可撤销）；每 40 轮或会话结束生成 `episode_summaries`。
- 前端：聊天面板、麦克风按钮（Web Speech，语言切换）、可选 `/api/voice/transcribe`；TTS 默认关闭。
- 语音可操作动作清单落地（11 项），每条有确定性意图后备。
- 落地回归套件（固定问题与指令 → 期望工具调用），两家提供商各跑。

不做：唤醒词、常开麦克风、实时流式转写、桌面壳、安装包、ChatGPT 网页端接入。

退出标准：
- 会话中途在下拉里切换 Claude 与 GPT，工具与历史不变。
- 说「显示下周的面试」导航看板；说「把 Acme 标为落选」出现确认卡片且确认前无变化。
- 聊天中陈述的事实一轮内出现在记忆收件箱；被否决的不再提议。
- 回归套件在两家提供商上全部通过。

---

## Phase 6 · 学习循环与加固

**目标**：搜索从你的行为与结果中可度量地变聪明；检索语义化；存储与隐私加固。

范围：
- `search/learn.py` 夜间任务：`w_learned`、混合、半衰期、冷启动守卫；`fit_signals` 作为重排上下文；结果推断的候选事实进收件箱；权重页（陈述 / 学习 / 样本数）。
- sqlite-vec + 本地多语言 embedding（先做 50 条真实查询的小评测再定模型）；`chunks` 与 RRF 混合检索；相似度 > 0.95 的近重复压制。
- 情节摘要的每周滚动汇总与压缩策略（每 40 轮摘要已在 Phase 5）。
- 可选 SQLCipher（`sqlcipher3`，DPAPI 保护的密钥，默认关闭）；正文清理策略；非求职邮件元数据 30 天清理。
- 可选来源白名单：Workday `cxs`（若裁定允许）、BambooHR、付费聚合器；`users.watch` + Pub/Sub（若解除字面约束）。
- Windows toast：新面试邀请与截止。

退出标准：
- 4 周交互后，对留出一周岗位的排序 precision@10（按收藏 / 申请）优于纯陈述权重。
- 行为验收：在无陈述偏好的情况下驳回 10 条纯现场岗位，现场岗位排名可见下降且权重页解释原因。
- 若启用加密：数据库仅在持有密钥时可打开；FTS5 与 sqlite-vec 在加密连接上工作。

---

## Phase 7 · 对外发布

**目标**：任何人能在 30 分钟内跑起自己的 JobPilot，且仓库里没有作者的身份信息。

范围：
- `jobpilot init` 引导向导：数据目录、区域包、求职周期、Google Cloud 项目分步说明（截图）、OAuth 客户端文件导入、LLM key、浏览器选择、现雇主域名（可选）。
- Dockerfile 多架构镜像、compose、Tailscale / VPS 部署指南、备份指南。
- UI 文案 i18n（zh / ja / en），文档英文版。
- **文档脱敏**：逐文件清理 `docs/research` 中「the user's own / this user / for the user」及雇主、签证、机器路径表述；`scripts/check_pii.py` 作为 pre-commit hook，对 tracked 文件匹配内置模式与本地 denylist，命中即拒绝提交。
- 匿名化夹具与示例数据集（虚构公司），CI 跑全部守卫测试。
- 许可、贡献指南、安全披露说明、隐私与提供商条款提醒；`pyproject.toml` 元数据补齐（作者不填个人邮箱）；提交身份改用 noreply 地址（Q13）。
- 去除任何针对首个用户的默认值。

退出标准：一位没参与开发的人按 README 在另一台机器上完成安装、授权、回填并看到看板；`uv run scripts/check_pii.py` 在全量 tracked 文件上零命中。

---

## 第一周计划（Phase 0 + Phase 1 主体；第二周做退出标准验收、规则修正与 8 天浸泡）

| 场次 | 时长 | 内容 |
|---|---|---|
| 1 | 2.5 h | Google Cloud 项目、两个只读范围、Desktop 客户端、`client_secret.json` 放到数据目录 `secrets/`。`uv self update`；`pyproject.toml` 构建后端、脚本入口、元数据；`src/jobpilot/__init__.py`；`uv add` 核心依赖；`settings.py`、`secrets.py`（DPAPI 令牌后端）、`readonly_http.py`、`auth.py`；`uv run jobpilot auth google` 完成 loopback 授权并断言范围；`jobpilot campaign add` 创建首个周期。 |
| 2 | 3 h | `store/db.py` + 迁移 0001（含 `pii_aliases`）；`connectors/gmail/sync.py` 回填；`uv run jobpilot sync --backfill-days 180`；`jobpilot senders`，阅读输出：平台级模式进 `regions/japan/senders.yaml`（附公开来源），公司租户进本地 `user_senders.yaml`。 |
| 3 | 3 h | 规则表与短语表（日本包 + 全球包，带 `verified`）；`EmailClassification` schema；放行门；`tests/test_rules.py` 10 到 20 条匿名夹具；`history.list` 增量与 404 回退；`jobpilot watch`。提交。 |
| 4 | 3 h | `classify/llm.py`（pydantic-ai 结构化输出，PII 别名，截断，缓存，成本日志，提示注入分块）；对回填中放行 / 含糊邮件跑一遍；抽 30 条复核，修提示词或规则。API key 入 keyring。 |
| 5 | 3 h | `resolve.py`（别名 → 归一化 → 模糊，thread 粘连）、`pipeline.py`（幂等事件、状态重算、截止与下一步、待复核、门户待查看、跟进与 ghosted、现雇主例外）、`status.py`；`jobpilot board`、`jobpilot show`。看一遍看板，记下每条错误留给 Phase 2。 |
| 6 | 2.5 h | `tools/registry.py` + 只读工具（返回值脱敏）；`mcp_server.py`；`uv run mcp dev` 调试；注册到 Claude Desktop、Claude Code、Codex；先打字再用 Win+H 与 Claude Desktop 语音模式问「哪些流程在进行，本周截止什么」。记录语音模式是否调用了本地工具。 |
| 7 | 1.5 h | `test_readonly_guard.py`；`pytest`、`ruff`、`pyright`、`check_pii`；Auth Platform → Publish app（不提交验证）→ 删除令牌重新授权 → 设 8 天后提醒；提交。顺手申请 LinkedIn Jobs 档导出，Phase 2 开始时 ZIP 已就位。 |

---

## 与当前日期的关系

今天 2026-09-16 处于 2027 卒秋採用窗口；内定式 2026-10-01。Phase 1 完成时（约 10 月初）看板应已覆盖秋採用期间收到的所有邮件；Phase 2 的提醒功能应在 10 月中旬可用，正好覆盖秋 / 冬採用的密集截止期；若周期开启了留学生标记，在留资格变更窗口（2026-12-01 至 2027-01-31）会作为日本包的周期里程碑在 Phase 3 出现于日程视图。