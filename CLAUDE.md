# JobPilot — 面向 AI 协作者的指引

## 先读什么

- `docs/REQUIREMENTS.md`：需求基线、硬约束、决策记录、待决问题。需求变更先改它。
- `docs/ARCHITECTURE.md`：技术选型、只读保证五层、数据模型、接入策略。
- `docs/ROADMAP.md`：当前阶段与退出标准。开工前确认正在做哪个阶段，不要提前实现后续阶段的功能。
- `docs/research/`：调研依据。实现某个集成前读对应文件并核对来源是否仍然有效。

## 不可协商的约束

1. **外部只读**。不得添加任何向外部服务写入的代码路径：没有 `gmail.send/modify/labels`、没有日历写范围、没有 LinkedIn 网络访问、没有 smtplib / imaplib / playwright / selenium / linkedin_api 依赖、没有 POST 到岗位站的申请接口。`tests/test_readonly_guard.py` 是这条约束的守门人，改它需要用户明确同意。
2. **模型不直接改状态**。任何本地写操作都走 `propose_* → pending_actions → confirm_action`；确认由用户或程序侧完成。
3. **人工优先，不虚构**。`user_status` 永远覆盖 `auto_status`；来源不足显示「待确认」，不补造链接或日期。
4. **无个人信息硬编码**。画像、目标岗位、地区、语言、模型 ID、路径全部来自配置、区域包或记忆表。仓库里不得出现真实邮件、真实姓名、邮箱地址；测试夹具必须匿名化。
5. **每次写入带出处与审计**。

## 工程约定

- Python 3.12，uv 管理；`src/jobpilot/` 布局；`uv run pytest`、`uv run ruff check --fix . && uv run ruff format .`、`uv run pyright` 提交前通过。
- 数据库：SQLite + 编号 SQL 迁移（`src/jobpilot/store/migrations/NNNN_*.sql`），标准库 `sqlite3`，Pydantic 行模型。不引入 ORM 除非文档决策更新。
- 时间存 UTC ISO 字符串，展示按 `JOBPILOT_TZ`。
- 配置用 pydantic-settings，前缀 `JOBPILOT_`；密钥只经 `SecretStore`，槽位白名单。
- 日本特有规则放 `src/jobpilot/regions/japan/`，通用规则放 `regions/global_en/`；规则数据文件带 `verified` 与来源 URL。
- 提交信息用英文，正文说明动机；文档用中文，技术名词保留英文。

## 与用户协作

- 用户用中文交流；回复与文档用中文，技术名词保留英文。
- 用户的真实邮箱、雇主、账号信息不写入仓库任何文件。
- 涉及外部服务的新集成、新依赖、新的数据外发路径，先在 `docs/REQUIREMENTS.md` 的决策表里记录再实现。
