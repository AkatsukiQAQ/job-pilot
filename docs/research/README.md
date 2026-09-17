# 调研附录索引

这些文件是 2026-09-16 三轮并行调研（共 23 个 agent）的整理输出，英文，按官方页面核实过但仍可能过时；实现每个集成前请再次核对对应文件里的 `sources`。需求与决策以 [../REQUIREMENTS.md](../REQUIREMENTS.md) 为准，本目录只提供依据与细节。

## 集成可行性

| 文件 | 内容 |
|---|---|
| [integration-gmail-calendar.md](integration-gmail-calendar.md) | OAuth 范围、Testing 状态 7 天过期、发布未验证应用、配额、同步机制、ATS 发件人与主题模式、Calendar 增量同步 |
| [integration-linkedin.md](integration-linkedin.md) | 官方 API 边界、用户协议 8.2、判例记录、数据导出 ZIP 内容、通知邮件类型 |
| [job-sources.md](job-sources.md) | 各聚合器与 ATS 公开接口的可用性、额度、署名义务、URL 模式、去重方案 |
| [chat-voice-llm.md](chat-voice-llm.md) | STT / TTS 选项、pydantic-ai 与其他统一层比较、MCP 宿主接入细节、两阶段工具设计 |
| [memory-system.md](memory-system.md) | 四层记忆、抽取管线、学习循环、FTS5 / sqlite-vec / SQLCipher 在本机的实测、推荐 schema |
| [tech-stack.md](tech-stack.md) | UI 方案比较、FastAPI + SQLite 细节、密钥存储、工具链、仓库布局 |

## 架构提案与评审

| 文件 | 内容 |
|---|---|
| [proposal-a-mvp-first.md](proposal-a-mvp-first.md) | 胜出提案：Gmail → 分类 → SQLite → 看板 + MCP，六个阶段，第一周逐场计划 |
| [proposal-b-data-first.md](proposal-b-data-first.md) | 数据模型与记忆优先：优先级矩阵、公司别名、规则统计、画像快照等被吸收进架构文档 |
| [proposal-c-risk-first.md](proposal-c-risk-first.md) | 风险优先：能力内核、信息源状态、出站日志、令牌浸泡测试等被吸收 |
| [proposal-judgments.md](proposal-judgments.md) | 三位评审（独立开发者 / 安全工程师 / 产品）的打分、理由、可移植点子、**三个提案共同遗漏的需求**、事实疑点 |

## 部署

| 文件 | 内容 |
|---|---|
| [deployment-decision.md](deployment-decision.md) | 「是否需要服务器」的结论、13 条路径的决策矩阵、分阶段推荐、现在就要做的架构决策、12 条价格事实核查 |
| [deployment-vps.md](deployment-vps.md) | Oracle / Google / AWS / Azure 免费额度现状，Hetzner / Vultr / Linode / ConoHa / Sakura 价格 |
| [deployment-paas.md](deployment-paas.md) | Fly.io / Railway / Render / Koyeb / Cloud Run / Workers / Hugging Face Spaces 等 |
| [deployment-selfhost.md](deployment-selfhost.md) | Tailscale、Cloudflare Tunnel、Windows 服务、现代待机问题、家用迷你主机 |
| [deployment-db-cron.md](deployment-db-cron.md) | Turso / Neon / Supabase / D1、GitHub Actions cron、Modal、Apps Script |

## 日本求职领域

| 文件 | 内容 |
|---|---|
| [japan-platforms.md](japan-platforms.md) | マイナビ / リクナビ / ONE CAREER / 外資就活 / LabBase / Wantedly 等的数据获取方式与条款；新卒 ATS 域名；目标公司 ATS 快照 |
| [japan-timeline.md](japan-timeline.md) | 2027 卒官方与现实时间线、秋採用、阶段枚举、薪资口径、留学生签证窗口 |
| [japan-email-patterns.md](japan-email-patterns.md) | 三类发件人、日语阶段短语表、日期与链接提取、マイページ与 LINE 缺口 |
| [japan-critique.md](japan-critique.md) | 对以上三份的完整性批评与更正（如 Rakuten October 2027 Entry 仅商务岗且在 i-web；Workable 发件域名补充；ABABA / アカリク 等遗漏平台） |