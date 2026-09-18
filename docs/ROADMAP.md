# Mita JobPilot 分步路线图

| 项目 | 内容 |
|---|---|
| 状态 | v0.4（2026-09-18，按决策 D26 重排） |
| 前置 | [REQUIREMENTS.md](REQUIREMENTS.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [design/v1/](design/v1/) |

原则：**先有每天能打开、能手动记录的看板，再让数据自动流入，最后加对话**。每一步独立可用；每一步一个 git 分支（`step1-board`、`step2a-gmail` …），用户验收后合回 `main`。托管部署（Docker、云、登录自启）全部放在最后一步（D27），此前只在本机 `jobpilot serve` 运行。不做语音（D31）。

---

## 0. 总览

| 步 | 名称 | 交付物 | 状态 |
|---|---|---|---|
| 0 | 骨架 | `src/` 布局、配置、密钥、迁移器、区域包协议、CI 基线 | 完成（2026-09-17） |
| 0.5 | 追踪域与 Google 连接器 | 迁移 0001 全部表、枚举、仓储、FTS；`ReadOnlyHttp`、多账号 `auth google`、Gmail API 层 | 完成（原 Phase 1 S1 / S2，`9ab39b3`、`1e95673`） |
| 1 | 基础网页看板 | FastAPI 看板 API + 手动录入 + React 四页（看板 / Pipeline / 申请详情 / 周期设置） | **进行中**（分支 `step1-board`） |
| 2a | Gmail 接入 | 规则与短语、同步与分类管线、`sync / senders / watch`、信息源页、待复核页 | |
| 2b | LinkedIn 导出导入 | `import linkedin <zip>`、Easy Apply 合并 | |
| 2c | Calendar 面试 | `interview_event`、gcal 只读同步、面试页 | |
| 3a | 只读对话 | MCP 只读工具 + 应用内对话页只读问答 | |
| 3b | 提议 / 确认 | `pending_actions`、确认卡片、语言操作、待复核裁决 | |
| 4 | 岗位搜索 v1 | 只读岗位源、目击与核验、去重、排序、研究请求、评估粘贴岗位、比较 | |
| 5 | 记忆 v1 | `profile_facts`、记忆收件箱、引导问卷、历史聊天导入 | |
| 6 | 学习循环与加固 | 结果学习、语义检索、可选加密、清理、备份 | |
| 7 | 发布与部署 | 引导向导、Docker、托管指南、i18n 文档、脱敏、许可、登录自启 | |

---

## 第 0 步 · 骨架（完成）

`pyproject.toml`（uv_build、控制台入口）、`settings.py`（`JOBPILOT_` 前缀，无个人默认值）、`secrets.py`（槽位白名单 + keyring / DPAPI / Fernet / env）、`store/db.py` + `0001_init.sql`、`regions/`（协议、注册表、`global_en` 与 `japan`）、`cli.py`（`campaign add / list`、`init`、`doctor`）、pre-commit（ruff、pyright、`check_pii`、守卫测试）。

## 第 0.5 步 · 追踪域与 Google 只读连接器（完成）

- 迁移 0001：`campaign / audit_log / company / company_alias / application（12 态、effective_status 生成列）/ application_event / email_account / email_message + FTS5 双表 / email_classification / classification_rule / rule_stat / pii_aliases / llm_call_log / source_state`。领域枚举与推导表在 `domain.py`；仓储在 `store/repo.py`；搜索在 `store/search.py`。
- `connectors/gmail/`：`ReadOnlyHttp`（仅 GET、白名单主机、令牌刷新为唯一 POST）、`auth.py`（loopback + PKCE、精确范围断言、`login_hint`、多账号 token）、`parse.py`、`sync.py`（配额预算、`history.list` 游标）。`jobpilot auth google / list / forget`。
- 用户侧：Google Cloud 项目、Gmail + Calendar API、External / Testing、测试用户、Desktop OAuth 客户端已就位（2026-09-18）。

---

## 第 1 步 · 基础网页看板（进行中）

**目标**：在浏览器里建周期、手动添加申请、记事件、改状态，看板与 Pipeline 随之变化；界面按 MITA Finance 设计语言，三语，暗色可切。数据全部手动录入，不接任何外部源。

范围：
- 后端：`services/status.py`（事件 → 自动状态推导、`is_ghosted`）、`services/manual.py`（添加申请 / 记事件 / 改用户状态，直接写库 + 审计，D29）、`CampaignRepo.set_active`、`web/`（FastAPI 工厂、9 个 JSON 接口、托管 `frontend/dist`）、`jobpilot serve`。
- 前端 `frontend/`：React 19 + Vite 7 + Tailwind v4 + TanStack Query + React Router + lucide-react；`tokens.css` 拷自 `docs/design/v1/`；应用外壳（完整导航树，未做项标 Soon；顶栏周期切换 / 语言 / 主题）；页面 01 看板、02 Pipeline（表格视图 + 添加申请）、03 申请详情（改状态确认卡、记事件、备注）、12 设置（周期管理）；i18n 跟随浏览器回退 en（D28）。
- 文档：本文件、REQUIREMENTS D26 到 D31、`docs/design/` 说明、CLAUDE.md 前端约定。

不做：⌘K 搜索、AI 提醒卡、信息源健康条、Pipeline 看板视图、手机版、面试页、任何自动数据源、`pending_actions`、CLI 录入命令。

退出标准：
- `uv run jobpilot serve` 后打开 `http://127.0.0.1:8765`：新建周期 → 添加申请 → 记一条「面试」事件 → 状态自动变为面试中 → 手动改为落选 → 看板计数与 Pipeline 分组随之变化；`audit_log` 有前后值。
- 语言三选一切换并记住；暗色切换正常。
- `pytest / ruff / pyright / check_pii` 全绿；`npm run build && npm run lint` 通过。
- 由用户验收，Claude Design 的四页 HTML 到齐后对照校正视觉细节。

---

## 第 2 步 · 信息获取

### 2a · Gmail 接入

**目标**：过去 180 天在 Gmail 留下痕迹的每一个选考流程自动出现在看板上；新邮件 2 分钟内更新；外部写操作在结构上不可能。

范围：
- 区域包数据：`regions/japan/data/` 与 `regions/global_en/data/` 的 senders / urls / phrases / company_suffixes / stages（平台级模式，每条 `verified` + 来源 URL；公司租户写本地 `user_senders.yaml`）。
- `classify/rules.py`、`classify/phrases.py`：发件人 / URL 匹配、短语打分、放行门。
- `services/resolve.py`（别名 → 归一化 → 模糊匹配，thread 粘连）、`services/pipeline.py`（每封一事务：分类 → 公司解析 → 申请 / 事件 upsert → 状态重算 → 待复核门 → 分类落库）、`services/gmail_sync.py`（回填 + `history.list` 增量 + 404 重拉 + 退避）。
- `classify/pii.py`、`truncate.py`、`schemas.py`、`llm.py`（pydantic-ai 分类器）：**默认关闭**，`JOBPILOT_CLASSIFIER_MODEL` 为空时只走规则 + 待复核；用户回答 REQUIREMENTS 9.2 第 3 问后再开。
- 14 天 → `followup_needed`；30 天 → ghosted；现雇主域名例外；D23 自动新建申请的条件。
- CLI：`sync --backfill-days`、`senders`、`watch`、`company employer`；网页：信息源页（账号列表、健康状态、最近同步）、待复核页（接受 / 改归 / 忽略）、看板的信息源健康条与「最近变化」接自动事件、Pipeline 来源徽标 Gmail。
- 用户侧：Auth Platform 点击 Publish app（In production，不提交验证），重新授权，8 天后确认令牌仍有效。

退出标准：看板列出过去 6 个月每一个流程，随机 30 条 ≥ 27 条正确；`watch` 运行时新邮件 2 分钟内成为事件；只读守卫通过；若开了 LLM，180 天回填费用有记录且约 15 美元以内。

### 2b · LinkedIn 导出导入

迁移 0002：`source_import` + `li_*`。`jobpilot import linkedin <zip>`（表头驱动、自然键幂等、原 ZIP 归档、Easy Apply 合并为 `application(channel='linkedin_easy_apply')`）；信息源页「导入 ZIP」入口与摘要。退出：同一 ZIP 导入两次零新增；每条 Easy Apply 申请在 `application` 中并链接到 Gmail 事件。

### 2c · Calendar 面试

迁移 0003：`interview_event`。`connectors/gcal/sync.py`（syncToken 增量，410 重拉，只读守卫扩展到 Calendar）；Calendly 与日历邀请邮件产出事件；面试页（月份概览 + Agenda，确认 vs 待排期，无链接显示待确认）；看板「后续面试」区接真实数据。退出：过去 90 天每个面试邀请成为 `interview_event` 并链接到正确申请；`meeting_url` 缺失时 UI 显示待确认。

---

## 第 3 步 · 对话

### 3a · 只读问答

- `tools/readonly.py`（`list_pipeline / get_application / search_emails / get_sync_status`，返回值经 `pii_aliases` 脱敏）；`mcp_server.py`（`MCPServer('jobpilot')`，`ToolAnnotations` 只读提示）；注册到 Claude Desktop / Claude Code / Codex（`docs/guides/mcp-hosts.md`）。
- 应用内对话页（设计 B 第 08 页）：pydantic-ai `Agent` 复用同一工具注册表，Claude / GPT 切换，流式，动作卡；只读，不产生提议。
- 退出：在宿主与应用内各问一次「我在面试哪些公司，本周截止什么」，回答引用 `[app:id]`，查不到时说无记录；MCP 返回值不含原始邮箱 / 电话 / 人名。

### 3b · 提议 / 确认与语言操作

- 迁移 0004：`pending_actions`、`egress_log`。`actions.py` 与 `propose_* / confirm_action` 工具；确认卡片；`jobpilot review` 与网页待复核裁决回写 `user_confirmed` 与 `rule_stat`；`jobpilot today`；`egress-report`。
- 退出：说「把 Acme SWE 标为落选」产生提议摘要，确认前无变化，确认后 `audit_log` 有前后值；`egress-report` 零非 GET（令牌刷新与 LLM 端点除外）。

---

## 第 4 步 · 岗位搜索 v1

迁移 0005：`watch_target / job_posting / job_canonical / job_sighting / job_judgement / job_note / job_interactions / research_request / job_features / job_scores / preference_weights / fit_signals / search_runs`；`application.canonical_id`。`connectors/boards/`（`GetOnlyTransport`：限速、ETag、robots；Greenhouse / Lever / Ashby / SmartRecruiters / Workable / Recruitee / Teamtailor / Rippling + ATS 自动识别）；网页搜索工具作为只读发现源；核验（连续 3 次未见 → 待核实）；`search/dedupe.py`、`search/scoring.py`（硬过滤 → 陈述权重 → LLM 重排前 20）；`search/research.py`（研究请求模板 → 提示词 → 粘贴回填）；`evaluate_posting`；岗位工作台、侧板、并排比较、研究请求页；招聘状态四分与核验日期。可选 Adzuna / JSearch 默认关闭。不做登录站抓取、Workday `cxs`（待裁定）。

退出：`jobpilot jobs` 列出排序结果并解释过滤；驳回 5 条后不再出现；关闭岗位 3 个轮询内标记待核实；一次研究请求 10 分钟内回填；24 小时内所有岗位源请求为 GET / HEAD；粘贴 JD 30 秒内得到判断并可一键记录申请。

## 第 5 步 · 记忆 v1

用户档案设计讨论（D17）先定稿。迁移 0006：`profile_facts / company_intel / profile_snapshot / extraction_runs / memory_fts`；`memory/{facts,render}.py`；取代逻辑与过期默认值；MCP 工具 `get_profile / search_memory / propose_memory_fact`；引导问卷（按 `campaign.kind`）、LinkedIn Job Seeker Preferences、ChatGPT / Claude 对话导出（`jobpilot import chat`）→ 同一抽取管线 → 记忆收件箱页；每轮对话后 `MemoryExtraction` 提议（D15 例外可自动生效）；会话摘要。

退出：说「希望年収は 600 万以上、東京勤務、リモート可が理想」产生三条候选事实；确认后 `get_profile()` 返回；再说不同年薪后旧事实被取代且 `valid_to` 有值。

## 第 6 步 · 学习循环与加固

`search/learn.py` 夜间任务（`w_learned`、半衰期、冷启动守卫）；sqlite-vec + 本地多语言 embedding（先做 50 条真实查询小评测）；情节摘要滚动汇总；可选 SQLCipher；正文清理与非求职邮件 30 天清理；`jobpilot backup / restore`；Windows toast 提醒；手机 390 px 适配（看板、面试）与 Tailscale 访问文档。

退出：4 周后 precision@10 优于纯陈述权重；驳回 10 条纯现场岗位后排名可见下降；若启用加密，FTS5 与 sqlite-vec 在加密连接上工作。

## 第 7 步 · 发布与部署

`jobpilot init` 引导向导（数据目录、区域包、周期、Google Cloud 分步说明、OAuth 客户端导入、LLM key、现雇主域名）；Dockerfile 多架构、compose、托管指南（GCP 或其他云、Tailscale / VPS）、登录自启（schtasks ONLOGON / systemd）、日志轮转；文档英文版与 UI 文案复核；`docs/research` 脱敏；匿名化夹具与示例数据集；许可、贡献指南、安全披露；去除任何针对首个用户的默认值。

退出：一位没参与开发的人按 README 在另一台机器上完成安装、授权、回填并看到看板；`check_pii.py` 全量零命中。

---

## 与当前日期的关系

今天 2026-09-18 处于 2027 卒秋採用窗口；内定式 2026-10-01。第 1 步完成后即可手动记录进行中的流程；第 2a 步完成时看板应已覆盖秋採用期间收到的所有邮件；若周期开启了留学生标记，在留资格变更窗口（2026-12-01 至 2027-01-31）会作为日本包的周期里程碑在第 2c 步出现于日程视图。
