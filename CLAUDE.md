# Mita JobPilot — 面向 AI 协作者的指引

## 先读什么

- `docs/REQUIREMENTS.md`：需求基线、硬约束、决策记录、待决问题。需求变更先改它。
- `docs/ARCHITECTURE.md`：技术选型、只读保证五层、数据模型、接入策略。
- `docs/ROADMAP.md`：当前阶段与退出标准。开工前确认正在做哪个阶段，不要提前实现后续阶段的功能。
- `docs/research/`：调研依据。实现某个集成前读对应文件并核对来源是否仍然有效。

## 不可协商的约束

1. **外部只读**。不得添加任何向外部服务写入的代码路径：没有 `gmail.send/modify/labels`、没有日历写范围、没有 LinkedIn 网络访问、没有 smtplib / imaplib / playwright / selenium / linkedin_api 依赖、没有 POST 到岗位站的申请接口。`tests/test_readonly_guard.py` 是这条约束的守门人，改它需要用户明确同意。
2. **模型不直接改状态**。任何本地写操作都走 `propose_* → pending_actions → confirm_action`；确认由用户或程序侧完成。
3. **人工优先，不虚构**。`user_status` 永远覆盖 `auto_status`；来源不足显示「待确认」，不补造链接或日期。
4. **无个人信息硬编码**。画像、目标岗位、地区、语言、模型 ID、路径、求职周期全部来自配置、区域包或记忆表；迁移文件不含种子数据。仓库里不得出现真实邮件、真实姓名、邮箱地址、作者雇主或签证状况；测试夹具必须匿名化；文档与测试中的公司示例一律使用虚构名称（如 Acme）。
5. **每次写入带出处与审计**。
6. **不假设求职周期与地区**。阶段枚举、里程碑、短语表、提示词、引导问卷都按 `campaign.kind` / `application.track` / 区域包取值；核心代码不得出现「新卒」「2027」「日本」字面量，这些只能出现在 `regions/japan/` 的数据文件里。

## 工程约定

- Python 3.12，uv 管理；`src/jobpilot/` 布局；`uv run pytest`、`uv run ruff check --fix . && uv run ruff format .`、`uv run pyright`、`uv run python scripts/check_pii.py` 提交前通过。
- 数据库：SQLite + 编号 SQL 迁移（`src/jobpilot/store/migrations/NNNN_*.sql`），标准库 `sqlite3`，Pydantic 行模型。不引入 ORM 除非文档决策更新。
- 时间存 UTC ISO 字符串，展示按 `JOBPILOT_TZ`。
- 配置用 pydantic-settings，前缀 `JOBPILOT_`；新增配置项必须同步 `env.example`（无前导点，避开 `.env*` 保护规则）与 `jobpilot init`；`tests/test_env_example.py` 会断言两者一致。密钥只经 `SecretStore`，槽位白名单。
- 每个 Windows 专有实现（DPAPI、schtasks、toast）必须有 Linux 对应或显式降级；不得写入只对首个用户成立的默认值。
- 日本特有规则放 `src/jobpilot/regions/japan/`，通用规则放 `regions/global_en/`；规则数据文件带 `verified` 与来源 URL。仓库内只收平台 / 供应商级模式；从个人收件箱观察到的公司租户写本地 `JOBPILOT_DATA_DIR/rules/user_senders.yaml`，不入库。
- 提交信息用英文，正文说明动机；文档中文为主，技术名词保留英文，对外发布前补英文版。

## 与用户协作

- 用户用中文交流；回复与文档用中文，技术名词保留英文。
- 用户的真实邮箱、雇主、账号、签证信息不写入仓库任何文件，包括 `docs/research/`。
- 涉及外部服务的新集成、新依赖、新的数据外发路径，先在 `docs/REQUIREMENTS.md` 的决策表里记录再实现。
- **严格按用户指定的范围开发**：没说的不做；可以建议额外工作，但未获同意不动手。发现 bug 只向用户报告，不擅自修改。不自行跑 smoke test。
- 代码尽量精简、好维护：能用一个函数解决就不建类，不为未来需求预留抽象。
- 出计划时要解释每个模块是做什么的、为什么需要，计划里出现的参数名也要解释。
- 每个开发步骤开专门分支（`step1-board`、`step2a-gmail` …），用户验收后合回 `main`。

## 前端约定（`frontend/`）

- React 19 + Vite 7 + TypeScript + Tailwind v4（CSS-first，无 `tailwind.config.js`）+ TanStack Query 5 + React Router 7 + lucide-react，npm 管理；工程文件与姊妹项目 MITA Finance 一致。
- `frontend/src/tokens.css` 是 `docs/design/v1/tokens.css` 的拷贝，改 token 先改 `docs/design/v1/`。
- 界面文案全部走 `src/i18n/{zh,ja,en}.ts` 字典，不在组件里硬编码；用户数据（公司名、岗位名）保持原文。
- 页面示例与测试数据只用虚构公司（Acme 等）；不出现任何真实公司作为「用户申请过的公司」。
- 页面上不存在「发送 / 投递 / 回复 / 申请」按钮；官方入口一律外链。
