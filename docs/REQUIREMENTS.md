# Mita JobPilot 需求与现状

| 项目 | 内容 |
|---|---|
| 状态 | 草案 v0.3（需求基线，随开发持续更新） |
| 日期 | 2026-09-17（初稿 2026-09-16） |
| 配套文档 | [ARCHITECTURE.md](ARCHITECTURE.md) 架构与技术选型 · [ROADMAP.md](ROADMAP.md) 分阶段路线图 · [research/](research/README.md) 调研附录 · [ref/gpt_design.txt](ref/gpt_design.txt) 参考原型 |

本文记录 Mita JobPilot 的定位、需求全貌、硬约束、领域基线、关键调研结论、当前状态、已做决策和待决问题。它是产品需求的唯一基线：需求变化先改这里，再改代码。v0.2 吸收了一轮四视角对抗式核查（需求完整性、事实一致性、内部一致性、隐私）的修正。v0.3 记录了用户对首批待决问题的回答：项目名 Mita JobPilot、多邮箱为核心能力、画像与记忆的数据库设计另行讨论、先私有自用。

---

## 1. 项目定位

### 1.1 一句话

Mita JobPilot 是一个**本地优先、只读接入外部信息源、带 AI 对话与记忆的个人求职工作台**：自动从 Gmail / Google Calendar / LinkedIn 导出等信息源推导出每一个选考流程的状态，帮助用户比较岗位、追踪进度、管理日程，并用 Claude 或 GPT 对话（含语音）操作系统和获取建议。

项目名 **Mita JobPilot**（与本地 PyCharm 项目目录 JobPilot 一致）；包名、命令与 MCP 服务名为 `jobpilot`，环境变量前缀 `JOBPILOT_`（决策 D18）。

### 1.2 定位演进（本次对话中确定）

| 维度 | 起点 | 现在的定位 |
|---|---|---|
| 使用者 | 作者本人 | **作者本人 + 任何愿意自托管的人**。作为可自托管的个人项目发布，每人运行一套自己的实例、使用自己的 API key 和 OAuth 凭据。不做多租户 SaaS。先私有自用，稳定后再考虑公开与许可证（决策 D19）。 |
| 求职阶段 | 日本 2027 年卒新卒就活 | **任意求职周期**：新卒（日本 2027 卒是首个真实场景）、将来的中途 / 转职、以及其他国家的求职。日本特有逻辑做成可插拔的「区域包」，状态机、事件、画像、引导问卷都按周期类型分派，不写死。 |
| 对话方式 | 生成提示词手动贴给 GPT（原型做法） | 应用内直接接入 Claude / GPT 的聊天框，可切换，带只读工具与语音操作。保留「生成研究提示词 → 外部执行 → 结构化结果回填」作为一种补充能力。 |
| 外部操作 | 原型要求「发送前二次确认」 | **目前全部禁止**：不发送、不回复、不申请、不写日历、不改标签。只读。 |

### 1.3 与现有工具的差别

调研发现日本市面上的「就活管理アプリ」（iOS 就活管理类应用、Jobhun、Notion / Spreadsheet 模板、i-web CONNECT 等）全部是**手动录入**的 MyPage / ID 管理器，没有邮件接入、没有日历同步、没有导出。Mita JobPilot 的差异化就是：**状态、截止日期和面试日程从邮件与日历自动推导，人工修正优先于自动识别，一切变更可审计**，再叠加记忆与 AI 对话。

### 1.4 示例用户画像（用于设计，已泛化，不写入代码）

以下是一个代表性画像，用于检验需求是否成立，不代表任何具体个人；实际画像来自用户配置与记忆系统。

- 以日本 2027 卒周期为首个场景，处于该周期尾段（秋採用 / 通年採用窗口）。
- 背景：AI Agent 产品开发、多模态 / VLM 研究、端到端工程交付。
- 目标岗位：Applied Research Engineer、Forward Deployed Engineer、Machine Learning Engineer、Software Engineer、AI Product / Applied AI；行业不限于 AI 公司，包括制造、自动驾驶、机器人、金融、咨询。
- 语言：中文、日语、英语混用。邮件、岗位描述、语音都可能三语混杂。
- 将来在职跳槽时，同一套系统要能切换到「中途」周期继续使用。

---

## 2. 硬约束（不可协商）

1. **外部只读**。应用对任何外部服务只能读取：Gmail 与 Calendar 只申请 `*.readonly` 范围；LinkedIn 不做任何网络访问（只导入官方导出文件、解析 Gmail 里的通知邮件）；岗位源只用 GET 请求的公开接口。不发送邮件、不建草稿、不改标签、不标已读、不创建或修改日历事件、不投递、不发消息、不点赞。这条约束要**由结构保证**（凭据范围、传输层、代码面、工具注册表、测试），而不是靠提示词。详见 ARCHITECTURE.md 第 4 节。
2. **本地优先，数据私有**。所有数据（数据库、令牌、导入文件）存在用户自己的机器或自己控制的服务器上。离开本机的只有发给 LLM 提供商的、经过脱敏截断的必要文本。经 MCP 宿主对话时，工具返回值会被宿主转发给提供商并写入宿主日志，因此**工具返回值本身也必须脱敏**，从第一阶段起就如此。
3. **人工修正优先于自动识别**。任何自动推导（邮件分类、状态变更、记忆抽取）都可以被用户覆盖，且覆盖后自动流程不得再改写。
4. **不虚构**。来源不足就显示「待确认」：没有会议链接就显示「待确认（ja: 待確認）」，不补造；匹配度是分析判断，不是录用概率。
5. **可审计**。每次自动或人工变更都记录变化前后内容、时间、来源、是自动判断还是人工确认。排除的岗位不删除，保留原因、时间和来源。
6. **渐进交付**。每个阶段独立可用；不做长周期无产出的基础设施。

---

## 3. 需求全貌

优先级说明：**核心** = 产品成立的必要能力（不等于第一阶段就交付）；**重要** = Phase 2 到 5 补齐；**后续** = Phase 6 起。各项的目标阶段以 ROADMAP.md 为准。「第一版」在全部文档中特指 ROADMAP 的 Phase 1。

### 3.1 选考追踪（Tracker）

| 优先级 | 需求 |
|---|---|
| 核心 | 汇总用户参与的每一个选考流程：潜在 / 进行中 / 已结束。 |
| 核心 | 状态自动来自信息源（邮件、日历、导入），并记录「自动状态」与「用户状态」两列，用户状态永远优先。 |
| 核心 | 每条记录保存：当前状态、更新时间、当前情况、下一步行动、截止日期、信息来源（手动 / Gmail / Calendar / LinkedIn 导出）。 |
| 核心 | 事件流（append-only）：报名、ES 提交、书类选考、笔试、面试各轮、结果、内々定、内定、承诺、辞退、退职交涉、入职、跟进提醒等。 |
| 核心 | 低置信度的自动识别进入「待复核」队列，不直接改状态。 |
| 重要 | 「门户待查看」事件：邮件只写「マイページをご確認ください」时，记录一条带门户链接的待办，用户可一键或语音回填结果。 |
| 重要 | 跟进与沉默：14 天无回复生成「需跟进」事件并进入今日待办；30 天仍无事件则打上 ghosted 标记（看板灰显，不改状态）。截止提醒：ES 截止、Web テスト期限、24 小时内面试。 |
| 重要 | 公司别名表：处理「株式会社Acme / Acme Inc. / acme.co.jp」等中日英与域名变体，避免同一公司被拆成多条。 |
| 重要 | 同一公司多流程：实习、本選考、中途、不同职位分开记录（申请记录带 track 字段）。 |
| 重要 | 合并 / 拆分记录的命令，带审计。 |

### 3.2 信息接入

| 优先级 | 信息源 | 需求 |
|---|---|---|
| 核心 | Gmail | 只读 OAuth（`gmail.readonly`），180 天回填 + 每 1 到 2 分钟增量同步；发件人 / URL 规则 → 短语打分 → LLM 三层分类，LLM 只处理低置信与自由格式邮件；支持中 / 日 / 英邮件。 |
| 核心 | Gmail 里的 LinkedIn 通知 | 申请已发送 / 被查看 / 被拒、消息通知、岗位提醒。 |
| 核心 | 现雇主邮件 | 用户可配置「现雇主域名」；来自该域名的邮件默认不分类为选考，除非用户确认（在职跳槽场景）。 |
| 重要 | Google Calendar | `calendar.events.readonly`，面试事件与申请记录关联；确认与待排期分开。 |
| 重要 | LinkedIn 官方数据导出 | 手动下载 ZIP，应用内导入（Job Applications、Saved Jobs、Job Seeker Preferences、messages 等 CSV），幂等，带导入批次来源。 |
| 重要 | 日本就活平台通知邮件 | マイナビ、リクナビ、ONE CAREER、外資就活、OfferBox、LabBase、Wantedly、アカリク 等只能通过邮件接入，发件域名表见区域包。 |
| 核心 | 多邮箱 | 邮箱由用户登录添加，不预设也不限定数量；每个 Google 账号独立令牌与同步游标，看板与搜索跨账号合并（决策 D20）。 |
| 后续 | 其他渠道缺口 | LINE 公式アカウント、电话、SMS、Slack Connect 等无法接入，提供手动 / 语音记录与「粘贴邮件或截图 → 结构化」的补录路径。 |
| 禁止 | 任何平台的登录态抓取 | LinkedIn、マイナビ、リクナビ、Wantedly、Bizreach、OpenWork 等明文禁止或有兜底条款，且封号风险发生在求职中期不可接受。 |

### 3.3 岗位搜索与匹配

| 优先级 | 需求 |
|---|---|
| 核心 | 搜索时参考：用户画像与偏好记忆、以前搜到的岗位、已申请岗位及结果。已申请、已驳回、已排除的岗位永不重复展示；现雇主的岗位默认排除。 |
| 核心 | 招聘状态四分：**确认在招 / 待核实 / 特别线索 / 排除记录**（排除保留原因、时间、来源）。每个岗位带官方来源与核验日期。 |
| 核心 | 核验过程：每次轮询或人工核验写一条「目击记录」；连续 3 次轮询未见即视为关闭并降为「待核实」；用户可手动核验；失效岗位进入「排除记录」并保留原因、时间、来源。 |
| 核心 | 岗位模型字段：公司、正式职位名、行业、方向标签、招聘对象（新卒 / 中途 / 实习）、地点与工作形式、招聘状态、截止时间、薪资及口径、工作内容、匹配度、匹配理由、技能或经历缺口、成长性与取舍、AI 相关度、是否要求先实习、未确认事项、官方来源、官方报名入口、我的应聘状态、备注与下一步。 |
| 核心 | 排序：综合、匹配度、AI 相关度、薪资、成长性、截止时间、公司名。筛选：关键词、方向、行业、招聘对象、招聘状态、匹配度、应聘进度、仅收藏。 |
| 重要 | 岗位来源（只读）：各公司 ATS 公开接口（Greenhouse、Lever、Ashby、SmartRecruiters、Workable、Recruitee、Teamtailor、Rippling）、Gmail 中的岗位提醒邮件、LLM 提供商自带的网页搜索工具、可选的 Adzuna / JSearch 免费额度；TokyoDev / Japan Dev 在核实利用条款后加入。 |
| 重要 | 研究请求（继承原型 UpdateRequest）：按任务模板（搜索新岗位 / 复核当前清单 / 寻找可主动敲门的公司与团队 / 清理失效岗位）生成结构化研究提示词，用户在 ChatGPT / Claude 网页执行后把结构化结果粘贴回应用，作为来源为 `llm_research` 的岗位或「特别线索」导入，带核验日期与出处，先进待复核。这是「特别线索」唯一条款干净的发现渠道。 |
| 重要 | 「评估这条岗位」：粘贴 JD 链接或文本 → 匹配判断与缺口 → 存为手动岗位 → 可选「记录申请」。这是聊天里最常见的用法。 |
| 重要 | 最多三个岗位并排比较：工作内容、匹配度、技能缺口、薪资、成长性、截止时间、申请资格、不确定事项、建议下一步。 |
| 后续 | 从结果学习：申请 / 收藏 / 忽略 / 驳回反馈到偏好权重；显示「陈述权重 vs 学习权重」及样本数；样本不足时不学习。 |

### 3.4 对话与语音

| 优先级 | 需求 |
|---|---|
| 核心 | 应用内聊天框，可选 Claude 或 GPT；答案必须基于应用数据库（工具检索），引用记录 ID；查不到就说「记录中没有」，不编造。 |
| 核心 | 所有会改本地数据的操作两阶段：模型只能「提议」，用户「确认」后才执行；外部写操作不存在对应工具。 |
| 重要 | 应用内对话面板细节：流式输出、提供商下拉切换、确认卡片、会话持久化并喂给记忆抽取。 |
| 重要 | 语音：按住说话（push-to-talk），支持 ja / zh / en；语音可执行的操作明确枚举（清单以 ARCHITECTURE.md 第 9 节为准）：显示看板、按状态筛选、打开某公司申请、下一个面试、本周截止、改状态、记录申请、记录备注、门户回填、评估这条岗位、收藏或驳回岗位。确认关键词（确认 / はい / yes）由程序正则匹配，不经模型。 |
| 后续 | 三语混说（code-switching）识别、公司名词表增强、可选的服务端转写（OpenAI 转写 / 本地 whisper）。不做唤醒词、不做常开麦克风。 |

**过渡方案（实现决策 D3，不是需求）**：Phase 1 到 4 借 MCP 宿主提供对话入口，Claude 侧为 Claude Desktop / Claude Code，GPT 侧仅 Codex CLI（终端工具）；语音以 Windows Win+H 听写进宿主为保底，Claude Desktop 语音模式能否调用本地 MCP 工具未证实，第一周实测。应用内聊天框按当前路线图在 Phase 5 到位（用户已确认，见 9.1）。

### 3.5 记忆系统

| 优先级 | 需求 |
|---|---|
| 核心 | 结构化历史：公司、岗位、申请、事件、面试、联系人、文档。完全由接入数据填充，主键不依赖 LLM 判断。 |
| 核心 | 用户画像事实：目标岗位、年薪期望、地点与远程偏好、公司类型与规模偏好、行业偏好、技术偏好、文化偏好、工作方式、硬性排除项、性格、优劣势、语言、签证、可入职时间、毕业时间；在职场景另有现雇主、现年薪、通知期、在职状态、跳槽动机。每条带来源、时间、置信度、有效期、被谁取代。 |
| 核心 | 记忆收件箱：从聊天、邮件、导入抽取的候选事实先进收件箱，默认用户确认后生效；唯一例外是「用户第一人称明确陈述、置信度 ≥ 0.85、非敏感类别」可自动生效并在收件箱标「已自动生效，可撤销」（决策 D15）。被否决的不再重复提议。 |
| 重要 | 公司与面试情报作为记忆类型：新卒名额、面试形式、笔试类型、联系人风格等「聊天里出现过的任何有用情报」。 |
| 重要 | 导入历史聊天：用户与 ChatGPT / Claude 的既有对话导出作为记忆种子，走同一条抽取 + 确认流程。 |
| 重要 | 情节记忆：会话摘要，长期滚动汇总。 |
| 后续 | 语义检索（本地多语言 embedding + sqlite-vec）、过期与遗忘策略、从结果推断的候选偏好。 |

**设计说明（决策 D17）**：用户档案由两部分组成：传统结构化 profile（经历、学历、在职状态、现雇主、技能等）与 LLM 记忆事实层（偏好、性格、聊天中出现的情报）。二者如何分工、如何互相引用，在 Phase 3 开工前单独讨论定稿；ARCHITECTURE.md 5.2 目前的 `profile_facts` 是初稿。「现雇主排除」等规则从档案推导，不单独向用户提问。

### 3.6 工作台 UI

| 优先级 | 需求 |
|---|---|
| 核心 | 首屏即工作台：当前求职概况、后续面试、应聘进度、岗位列表。不做营销式落地页。 |
| 核心 | 应聘 pipeline 视图（状态枚举见第 4.1 节）、岗位卡片、岗位详情或侧边面板。 |
| 核心 | 卡片 / 详情的动作：收藏、加入比较、前往官方入口、记录备注、改应聘状态（经确认门）；面试条目可跳到对应申请并回填结果。侧栏固定入口：看板 / 岗位 / 面试 / 记忆收件箱 / 待复核 / 信息源。 |
| 重要 | 面试日程：月份概览 + Agenda 列表，统一 JST（时区可配置），确认与待排期分开，无链接显示「待确认」。 |
| 重要 | 并排比较视图、记忆收件箱、待复核队列、信息源健康状态条（正常 / 降级 / 需重新授权 / 不可用 / 已禁用）。 |
| 重要 | 设计交付物 `docs/DESIGN.md`（Phase 2 前置）：Mita JobPilot 自己的信息架构（侧栏导航树）、5 到 8 条核心用户流程、页面与组件清单、design tokens。由 Claude Design 按 [design/claude-design-prompt.md](design/claude-design-prompt.md) 产出后蒸馏（决策 D22）。 |
| 重要 | 视觉方向：沿用姊妹项目 MITA Finance 的设计语言（决策 D22）：暖纸 cream / ink 色板、琥珀点缀、手写体品牌字标与大标题、Fraunces 页面标题、14px 纸感卡片与暖棕阴影、黄色导航高亮、手绘 SVG 图表、右下角 FAB 聊天面板；「待确认」用琥珀虚线占位；安静、轻盈、像求职手账而非 SaaS 后台；线性图标；固定侧栏；高信息密度但不拥挤。原型文档里的「深绿主色 / 薄荷绿选中态」方案作废。 |
| 重要 | 桌面优先、移动可用：看板与面试 Agenda 在 390 px 宽度可用；手机访问（如 Tailscale）有文档。 |
| 后续 | PWA、桌面通知。 |

### 3.7 面向他人：自托管

| 优先级 | 需求 |
|---|---|
| 核心 | 无个人信息硬编码：画像、目标、地区、语言、求职周期全部来自配置与记忆；迁移文件不含种子数据。 |
| 核心 | 「自带凭据」：每个用户自建 Google Cloud 项目与 Desktop OAuth 客户端，自填 Anthropic / OpenAI API key。应用提供分步引导。 |
| 重要 | 十二要素配置（环境变量前缀 `JOBPILOT_`）、单一数据目录、Dockerfile 与 compose、`backup` / `restore` 命令。 |
| 重要 | 区域包机制：日本包（发件域名、阶段枚举、日历里程碑、薪资口径）为首个实现；全球 / 英文包为默认兜底。仓库内的规则只收平台 / 供应商级模式并附公开来源；从个人收件箱观察到的公司租户写本地文件，不入库。 |
| 重要 | 匿名化测试夹具生成器：从真实邮箱脱敏出主题模板，保证仓库里没有 PII（Phase 1 测试与 CLAUDE.md 的禁写规则都依赖它）。 |
| 重要 | UI 文案三语并存 zh / ja / en（与 MITA Finance 一致），品牌字标固定英文，用户数据保持原文；文档中文为主，对外发布前补英文版。 |
| 后续 | 许可选择、贡献指南、发布前的文档脱敏与 PII 自动检查。 |

### 3.8 非功能需求

- **隐私**：不展示招聘负责人邮箱、电话等个人信息；面试链接只在私有空间显示；发给 LLM 的文本与工具返回值先做 PII 别名替换（邮箱、电话、URL、人名）并截断；非求职邮件只存元数据且 30 天后清理；日志不含邮件正文与地址。
- **安全**：令牌用操作系统凭据保护（Windows DPAPI，Linux 加密文件）；密钥槽位白名单（只允许 Google 令牌、LLM key、岗位源 key），结构上不存在放 LinkedIn cookie 或 SMTP 密码的位置；对不可信文本（邮件、JD、日历描述）做提示注入防护。
- **可靠性**：单文件 SQLite + WAL；每日备份到第二位置；同步游标持久化，任意时刻中断可恢复；信息源状态可见。
- **成本**：LLM 分类走缓存（同一邮件同一提示词版本不重复计费）；批量分类默认用便宜模型；每次调用记录 token 与费用。
- **多语言**：中 / 日 / 英；NFKC 归一化、全角半角、法人后缀（株式会社、(株)、Inc.、K.K.）处理；FTS 对 CJK 用 trigram。
- **时区**：存 UTC，展示按 `JOBPILOT_TZ`；未配置时取活动求职周期所属区域包的默认时区（日本包为 Asia/Tokyo），再无则 UTC。代码里不写死任何时区。

---

## 4. 参考原型提取（Career Kompas）

来源：[ref/gpt_design.txt](ref/gpt_design.txt)（用户与 GPT 共同完成的原型需求，2026-09）。我们从零重做信息架构、交互、UI 与工程，只继承以下产品基线。

### 4.1 状态词汇

**招聘状态**（岗位侧）：确认在招 / 待核实 / 特别线索 / 排除记录。

**应聘状态**（用户侧）：在原型十态基础上补两个终态以支持中途场景，共 12 态。代码为数据库枚举值，映射见下表；区域包的具体阶段作为子阶段挂在其下。

| 代码 | 中文 | 新卒典型子阶段 | 中途典型子阶段 |
|---|---|---|---|
| `unrecorded` | 未记录 | — | — |
| `considering` | 考虑中 | 检索到、收到スカウト | カジュアル面談 |
| `preparing` | 准备申请 | プレエントリー、ES 撰写 | 书类准备 |
| `applied` | 已申请 | ES 提交、エントリー完了、書類選考 | 応募、書類選考 |
| `assessment` | 笔试或课题 | Web テスト、コーディングテスト、録画面接 | 技術課題 |
| `interviewing` | 面试中 | GD、一次 / 二次 / 最終面接 | 一次 / 二次 / 最終面接 |
| `offer` | Offer | 内々定、オファー面談 | 内定通知、オファー面談 |
| `accepted` | 已承诺 | 内定承諾、内定（10/1） | 内定承諾、退職交渉 |
| `joined` | 已入职 | 入社 | 入社 |
| `rejected` | 已落选 | お祈り | お祈り |
| `withdrawn` | 主动放弃 | 辞退 | 辞退 |
| `unsuitable` | 不合适 | 资格不符、要求先实习 | 条件不符 |

`ghosted`（长期沉默）与 `needs_review`（待复核）**不是**状态：前者是申请上的派生标记，后者是分类与提议的队列。

### 4.2 数据实体基线

`Company`、`Job`、`SourceEvidence`、`Application`、`ApplicationUpdate`、`InterviewEvent`、`PendingSchedule`、`UserNote`、`UpdateRequest`。

原则：岗位事实、个人判断、应聘状态、日程信息**分开存储**，改申请状态不污染岗位原始数据；每次自动更新记录变化前后内容、时间、来源、自动还是人工。`UpdateRequest` 对应第 3.3 节「研究请求」，`UserNote` 对应岗位备注表。

### 4.3 页面基线

机会比较（首页）→ 岗位卡片 → 岗位详情 → 并排比较（≤3）→ 应聘进度追踪 → 面试日程 → 更新请求。这是原型的页面顺序；Mita JobPilot 自己的信息架构在 `docs/DESIGN.md` 中定义。

### 4.4 我们与原型的差异

| 原型 | Mita JobPilot |
|---|---|
| 「GPT 更新请求」生成提示词，用户手动贴给 GPT | 应用内 Agent 直接执行只读工具（查邮件、查日历、搜岗位）；「研究请求」保留为补充能力，结果可结构化回填 |
| 网站不联网，靠人回填 | Gmail / Calendar 自动接入，用户只回填门户里的结果 |
| 首页是「机会比较」（岗位工作台） | 首屏是追踪看板；岗位工作台在 Phase 4 到位 |
| 单人使用 | 可自托管的个人项目 |
| 只面向 2027 卒 | 任意求职周期，日本逻辑做成区域包 |
| 无记忆系统 | 四层记忆，驱动搜索排序 |

---

## 5. 领域基线：日本求职

以下事实在 2026-09-16 调研核实过（另有标注的除外），详情与来源见 [research/japan-platforms.md](research/japan-platforms.md)、[research/japan-timeline.md](research/japan-timeline.md)、[research/japan-email-patterns.md](research/japan-email-patterns.md)、[research/japan-critique.md](research/japan-critique.md)。

### 5.1 2027 卒官方时间线（内閣官房 2026-03-24 要請，已确认）

| 里程碑 | 日期 |
|---|---|
| 広報活動解禁 | 2026-03-01 |
| 採用選考活動解禁 | 2026-06-01 |
| 正式内定（内定式） | 2026-10-01 |
| （可选，仅留学生）留学 → 技術・人文知識・国際業務 在留資格変更 申请窗口（4 月入职） | 2026-12-01 至 2027-01-31 |

签证类里程碑由区域包提供、按周期开关启用，默认关闭。现实远早于官方：约六成企业在 5 月及之前已发出内々定（内閣官房 2025-12-26 資料）。今天处于**秋採用**窗口（9 到 11 月，内定式后因辞退空出名额），冬採用 12 到 2 月。外资、初创、AI 研究机构多为通年 / 随时招聘。区域包应把这些做成可配置的周期里程碑，并默认把新机会标为「待核实」。

### 5.2 日本阶段枚举（区域包提供）

新卒（已调研）：プレエントリー → ES 提出 → Web テスト（SPI3 / 玉手箱 / TG-WEB / SCOA）→ コーディングテスト → 録画面接 → GD → 一次 / 二次 / 最終面接 → 内々定 → オファー面談 → 内定承諾 → 内定（10/1）→ 入社。

中途（设计假设，未调研；实现中途区域包前需核实）：カジュアル面談 → 書類選考 → 技術課題 → 一次 / 二次 / 最終面接 → オファー面談 → 内定 → 退職交渉 → 入社。

两套枚举到应聘状态的映射见第 4.1 节表。

### 5.3 薪资口径

新卒常见「初任給 月給 按学历分档」「基本給 + 固定残業代」「年俸制 / 想定年収」「裁量労働制」。岗位模型需要 `salary_basis` 枚举（monthly_starting_by_degree / monthly_incl_fixed_overtime / annual_salary_system / model_annual_income / discretionary_labor / hourly / unknown）加学历档、固定加班时长与金额、奖金是否含入、年度，仅为排序统一折算为估算年収。

### 5.4 平台与邮件信号（摘要）

| 类别 | 结论 |
|---|---|
| 就活导航站（マイナビ、リクナビ、ONE CAREER、外資就活、unistyle、キャリタス、OfferBox、LabBase、アカリク、Wantedly 等） | 无导出、无 API；只能靠发到 Gmail 的通知邮件。マイナビ官方发件人已确认（`mynavi.jp` 域下五个地址）、外資就活为 `info@gaishishukatsu.com`；ONE CAREER 用主题前缀「【ONE CAREER】」识别；リクナビ发件人未确认，需从真实邮件头核对。 |
| 新卒 ATS（マイページ系统） | 集中在少数域名：`*.snar.jp`（sonar，发件人 `<公司>@snar.jp`）、`*.i-web.jpn.com` 与 `mypage.30NN.i-webs.jp`（i-web，发件人通常是公司自有域名）、`job.axol.jp`（マイナビ アクセスオンライン）、`www.e2r.jp`（日立品牌）。 |
| 外资 / 初创 ATS | Greenhouse、Ashby、Workable 的发件人已由官方文档确认（如 `no-reply@us.greenhouse-mail.io`、`no-reply@ashbyhq.com` 按域名匹配、`noreply@candidates.workablemail.com`）；Lever（`no-reply@hire.lever.co`）与 SmartRecruiters（`notifications@smartrecruiters.com`）仅域名级有官方依据，具体地址需从真实邮件头核对；Workday 为 `<tenant>@myworkday.com`；HERP（`candidacy.herp.cloud`，官方 FAQ 页 404，未核实）、HRMOS（`@<slug>.hrmos.co`，已核实）、TalentIO 只有 HTML 页面和邮件，且有公开 GET 接口的只有前五家。 |
| 笔试供应商 | SPI テストセンター发件人 `noreply_tc@arorua.net`；玉手箱系列由公司代发，用 URL（`*.e-exams.jp` 等）识别。 |
| 覆盖缺口 | 大量新卒结果只在マイページ内展示；不少公司报名后转 LINE 公式アカウント。这两类在 Gmail 里只有「请查看」的存根，需要「门户待查看」事件与手动补录。 |

### 5.5 市场快照

秋採用窗口中各公司的开放状态随时变化，只放在调研附录里，**不进入产品需求**。产品层面的对应要求是：每个岗位带核验日期，默认「待核实」，并支持一键跳转官方页面复核。

---

## 6. 关键调研结论

每一项都在 2026-09-16 对照官方文档核实过；实现时仍需再次确认。详细选项、利弊、来源见 [research/](research/README.md)。

### 6.1 Gmail 与 Google Calendar

- 只读接入完全可行，费用为零。个人使用（「你是应用的唯一用户」）在 Google 官方例外清单中，**不需要**品牌验证与 CASA 安全评估。
- 关键坑：OAuth 同意屏幕留在「Testing」状态时，refresh token 与用户授权**7 天后过期**。解决：首次验证通过后点击「Publish app」进入「In production」但**不提交验证**，删除旧令牌重新授权。之后令牌仅在 6 个月未使用、被撤销、改 Gmail 密码、或同一客户端 ID 下有效 refresh token 超过 100 个时失效。Google 的 Audience 页面对受限范围的措辞含糊，此行为以 Phase 1 的 8 天令牌浸泡测试为准；若失败则退回 Testing 状态每周重新授权。
- 个人 `@gmail.com` 账号不能用「Internal」类型（那是 Workspace / Cloud Identity 专属）。
- 第一次授权就同时申请 `gmail.readonly` 与 `calendar.events.readonly`，避免二次「未验证应用」警告。
- 同步：初次回填用 `messages.list` + `messages.get`（元数据为主，只有规则命中的邮件取全文），增量用 `history.list`（每次 2 配额单位），1 到 2 分钟一次绰绰有余；`startHistoryId` 失效返回 404 时按最新 `internalDate` 重新同步。推送（`users.watch` + Pub/Sub）是在 Google 侧注册状态的 POST，在「不写任何外部服务」的字面约束下暂不使用。
- IMAP + App Password 是**全账户凭据**（能发信、能删），只读只能靠代码自律，与「结构保证」矛盾，**不作为方案**。Takeout 无法自动化，仅可作一次性历史回填。
- 给他人使用时：每个自托管者自建 Google Cloud 项目（一次性、按分步引导完成，研究估计以小时计）。正式验证成本每年 675 美元起加数周流程，不适合个人项目。

### 6.2 LinkedIn

- 面向普通开发者的官方 API 只有 OIDC 登录（`openid profile email`）与 `w_member_social`（发帖，**写权限，永不申请**）。EU 注册账号另有 DMA Member Data Portability API（只读），日本账号不可用。申请记录、消息、岗位搜索都是合作伙伴专属，且 Job Posting API 已停止接受新伙伴。
- 用户协议 8.2 条（2025-11-03 起）明文禁止爬虫、插件、脚本、复制数据。hiQ 案以 LinkedIn 胜诉终结（2022），Proxycurl 于 2025-07-04 在永久禁令下关停。登录态自动化会导致封号，求职中期不可接受。
- 两条合规通道：① Gmail 里的 LinkedIn 通知邮件（`jobs-noreply@linkedin.com`、`messages-noreply@linkedin.com`、`jobalerts-noreply@linkedin.com` 等，需从真实邮件头核对）；② 官方「Get a copy of your data」ZIP 手动导入（Jobs 类 10 分钟档、完整档 24 到 72 小时），CSV 表头未文档化且会变，解析必须按表头驱动。
- 只有 Easy Apply 与用户主动确认「Did you apply?」的外部申请会出现在 LinkedIn 数据里；`messages.csv` 是唯一能拿到招聘者消息全文的地方。

### 6.3 日本就活平台

见第 5.4 节。结论：邮件是唯一合规入口；ONE CAREER 列表页为客户端渲染，即便合规抓取也拿不到内容。

### 6.4 岗位搜索源

- Indeed、LinkedIn、Glassdoor 对个人**没有**公开搜索 API；Google for Jobs 没有 API；HelloWork API 仅限自治体与有牌照的职业介绍机构。
- 可用（GET、无需登录、条款允许）：Greenhouse Job Board API、Lever Postings、Ashby Posting API、SmartRecruiters Postings、Workable Widget、Recruitee、Teamtailor RSS、Rippling；Remotive / Himalayas / Jobicy / The Muse 等远程岗位站（需展示来源署名）。
- robots.txt 宽松但**利用条款未核实**：TokyoDev / Japan Dev 的 sitemap 差分。启用前须核对两站条款；TokyoDev 是否输出 JobPosting JSON-LD 待验证，否则改用其 newsletter 邮件。
- 有额度限制的聚合器：Adzuna（每天 250 次，无日本市场，需展示「Jobs by Adzuna」）、JSearch 免费档每月 200 次（支持 `country=jp`）。
- Workday 的 `cxs` 搜索接口是 POST（无服务端状态）；是否算「写」需你裁定（见第 9 节）。
- Anthropic 与 OpenAI 的**提供商侧网页搜索工具**是只读的岗位发现渠道，能覆盖免费 API 到不了的日本新卒信息，作为一个岗位源实现。

### 6.5 对话、语音与 LLM

- 过渡方案零 UI：用官方 `mcp` Python SDK 2.x（`FastMCP` 已改名 `MCPServer`）通过 stdio 暴露只读工具，注册到 Claude Desktop、Claude Code、Codex CLI，即得 Claude 与 GPT 两种对话入口。ChatGPT（Developer mode，仅网页版）不能拉起本地 stdio 服务，需要公网 HTTPS 端点或 OpenAI Secure MCP Tunnel；Codex 已提供 GPT 侧本地入口，暂不做。
- 语音过渡方案：Windows Win+H 语音输入（支持中 / 日 / 英，走 Azure 在线识别）为保底；Claude Desktop 语音模式（**未证实**它会调用本地 MCP 工具，需第一周实测）；Claude Code `/voice`（支持日语，不支持中文）。
- 自有 UI 阶段：pydantic-ai 作为 Anthropic / OpenAI 统一层，模型 ID 只放配置；浏览器 Web Speech API 做按住说话。Chrome 默认走 Google 云端识别，支持 zh / ja / en；本地识别需 Chrome 142+ 并按语言下载 language pack，zh / ja 包是否可用需运行时探测；Edge 的本地模型仅 Canary / Dev 且不含 zh / ja，并有静默无结果的报告。OpenAI 转写 API 作为可选后备。
- 提示词缓存、结构化输出、工具调用格式在两家有差异，由 pydantic-ai 屏蔽；MCP 的 prompt 是用户手动选择的模板，**不是**系统提示，落地约束要靠工具描述与宿主的项目指令文件。

### 6.6 记忆系统

- 不引入 mem0 / Letta / Zep 作为依赖，借鉴其设计：类型化事实 + 双时态有效期 + 取代链（Graphiti 的边有效期思想）、渲染成固定「核心记忆」块（Letta 思想）、候选收件箱。
- 记忆检索在 Phase 3 只用 SQLite FTS5（拉丁文用 unicode61，CJK 用 trigram，1 到 2 字查询回退 LIKE），语料量在十万块以下时 sqlite-vec 暴力 KNN 已足够，embedding 推迟到 Phase 6。
- Anthropic 没有 embedding API；本地多语言模型（bge-m3 / multilingual-e5）或 Voyage / OpenAI embedding 二选一，行内记录模型名与维度。
- 学习循环：申请 +1、收藏 +0.5、忽略 ×3 −0.25、驳回 −1，陈述权重 0.7 与学习权重 0.3 混合，90 天半衰期；公司侧拒绝进入「现实信号」而非偏好。**样本不足时不学习**，权重页显示样本数。

### 6.7 部署

- **第一版不需要服务器**。单用户、只读、轻 CPU，数据不到 1 GB。电脑休眠只会让同步暂停，唤醒后一次 `history.list` 即可补齐。
- 手机访问：Tailscale Personal（免费、6 用户）`tailscale serve` 提供 HTTPS，麦克风与 PWA 需要安全上下文。数据不出家门。
- 需要「电脑关机也同步」时再上服务器：东京 5 美元 / 月 VPS（Vultr、Linode、ConoHa）或 Fly.io 东京机器（约 4.3 美元）；家用 N100 迷你主机一次性约 180 美元。Oracle Always Free（ARM，额度 2026-06-15 起减半为 2 OCPU / 12 GB，东京 / 大阪可选）值得试但不可依赖。
- 已过时的常识：AWS 2025-07-15 后新账号不再有 12 个月免费 EC2；Google e2-micro 免费仅限美国区；Serverless（Cloud Run、Lambda、Workers）无持久文件系统，需要重构 SQLite 与调度器，不值得。
- 现在就要做的架构决策（让迁移只是改配置）：十二要素配置、单一数据目录、Dockerfile（amd64 + arm64）、`AUTH_MODE=none|password|proxy`、默认绑定 127.0.0.1、SSE 心跳、单进程单写入者、备份命令。

---

## 7. 现状（2026-09-16）

### 7.1 仓库

- `pyproject.toml`：packaged `src/` 布局，`uv_build` 后端，控制台入口 `jobpilot` 与 `jobpilot-mcp`，运行依赖 typer / rich / pydantic / pydantic-settings / platformdirs / keyring / cryptography / pyyaml / tzdata / pywin32（仅 Windows），dev 组 pytest / ruff / pyright / pre-commit / stubs；`uv.lock` 完整锁定。
- `.venv/`：uv 0.10.7 创建的 CPython 3.12.12。本机 SQLite 3.50.4，FTS5 与扩展加载可用（已实测）。
- Git：已初始化，分支 `main`。`.gitignore` 排除 `.venv/`、`.idea/`、`.claude/settings.local.json`、`.env`、令牌与凭据文件、`data/`、`imports/`、`backups/`、`*.db`、LinkedIn 导出 ZIP。
- 工具链：uv 0.10.7、Node 22.17、git、PyCharm。
- 代码：**Phase 0 骨架已完成（2026-09-17）**。`src/jobpilot/` 含 `settings.py`（`JOBPILOT_` 配置，无个人默认值）、`secrets.py`（槽位白名单 + keyring / DPAPI / Fernet / env 后端）、`domain.py`（周期类型、track、12 态应聘状态枚举）、`store/`（连接工厂、带 checksum 的迁移运行器、`0001_init.sql` 含 `campaign` 与 `audit_log`、`CampaignRepo`）、`regions/`（`RegionPack` 协议、注册表、`global_en` 与 `japan` 两个 YAML 驱动的包，时区与语言只在 `data/pack.yaml`）、`connectors/`（只读空壳）、`cli.py`（`campaign add / list`、`init`、`doctor`、`version`）、`mcp_server.py`（Phase 1 占位）。`tests/` 8 个文件 43 个用例，含只读守卫与「核心代码无地区 / 周期字面量」扫描。`scripts/check_pii.py` 在 pre-commit 中运行。

### 7.2 本次完成

- 需求、架构、路线图三份文档（本文、ARCHITECTURE.md、ROADMAP.md）。
- 三轮并行调研共 23 个 agent，覆盖 Gmail / Calendar、LinkedIn、岗位源、对话与语音、记忆、技术栈、部署、日本平台、2027 卒时间线、日本招聘邮件模式，结果整理在 `docs/research/`。
- 三个不同视角的架构提案（MVP 优先 / 数据模型优先 / 集成风险优先）由三位评审打分，MVP 优先胜出，并吸收另两者的优点，形成 ROADMAP.md。
- 一轮四视角对抗式核查（78 条发现）并修正。

### 7.3 下一步

Phase 1「收件箱到看板」。第一步是 Google Cloud 项目（Gmail + Calendar API、两个只读范围、Desktop OAuth 客户端）与 `jobpilot auth google`，见 ROADMAP.md Phase 1 与「第一周计划」。UI 设计由 Claude Design 按 `docs/design/claude-design-prompt.md` 并行推进。

---

## 8. 已做决策

| 编号 | 决策 | 理由 | 可逆性 |
|---|---|---|---|
| D1 | 外部只读，由结构保证 | 用户要求；信任建立前工具只观察不行动 | 用户可解除 |
| D2 | 本地优先，SQLite 单文件，单进程单写入者 | 单租户、备份简单、FTS5 / sqlite-vec 原生 | 不支持 Postgres，多租户不在范围 |
| D3 | Phase 1 无自有 UI，对话入口用 MCP 宿主；Phase 2 起加只读 Web 看板；应用内对话面板在 Phase 5 | 把精力先放在数据正确性上，同时尽早有每天打开的界面 | 用户已确认按推荐执行（9.1） |
| D4 | Gmail 走 OAuth Desktop 客户端 + `gmail.readonly` + `calendar.events.readonly`，发布为「In production（未验证）」 | 唯一免费、免审核、且预期令牌不周期过期的路径；以浸泡测试验证 | 若共享需验证；失败则退回 Testing 每周授权 |
| D5 | 不做 IMAP / App Password 路径 | 凭据可写，破坏结构保证 | 可作紧急备用文档化 |
| D6 | LinkedIn 零网络代码：通知邮件 + 官方导出 ZIP | 协议与判例风险 | 永不自动化 |
| D7 | 不爬取任何登录态平台；日本导航站只靠邮件 | 条款禁止，封号风险 | 无 |
| D8 | 模型 ID 只放配置，不进代码；批量分类用便宜模型 | 模型更新频繁；成本 | 无 |
| D9 | 面向他人 = 可自托管的个人项目、自带凭据；不做多租户 | Gmail 受限范围验证成本；隐私 | 公开时机见 D19 |
| D10 | 日本逻辑做成区域包，求职周期为一等实体，状态 / 事件 / 画像 / 问卷按周期类型分派 | 用户要求支持中途与其他国家 | 无 |
| D11 | 第一版不部署服务器；架构按可迁移设计 | 调研结论 | 需要时改配置 |
| D12 | 文档中文为主，技术名词保留英文；文件名 ASCII | 作者习惯；跨平台 | 对外发布前补英文 |
| D13 | 数据库访问用标准库 `sqlite3` + 编号 SQL 迁移，不用 ORM | FTS5 / 生成列 / sqlite-vec 是原生 SQL，少一层抽象 | 协作者偏好 ORM 时可换 SQLAlchemy |
| D14 | 应聘状态为 12 态封闭枚举；`ghosted` 与 `needs_review` 为标记 / 队列而非状态 | 状态机闭合，中途终态可表达 | 无 |
| D15 | 记忆候选默认人工确认；仅第一人称明确陈述、置信度 ≥ 0.85、非敏感类别自动生效并可撤销 | 兼顾省力与硬约束 3 | 可收紧为全部人工确认 |
| D16 | 迁移文件不含任何种子数据；首个求职周期由配置或 `jobpilot init` 创建 | 无个人信息硬编码 | 无 |
| D17 | 用户档案 = 结构化 profile + LLM 记忆事实层；具体 schema 在 Phase 3 前专门讨论 | 用户要求融合传统 profile 与 LLM memory 库，先不定死 | 5.2 为初稿 |
| D18 | 项目名 Mita JobPilot；标识符 `jobpilot` | 与本地 PyCharm 项目一致 | 无 |
| D19 | 先私有自用，稳定后再公开；许可证届时决定；git 提交身份已改为 GitHub noreply 地址（2026-09-17，仓库级 `git config`，历史提交已改写） | 用户决定 | 公开前复核 Phase 7 清单 |
| D20 | 多邮箱为核心能力，由用户登录添加，数量不限；Phase 1 即支持 | 用户要求 | 无 |
| D21 | 阶段顺序按推荐执行，但阶段是检查点而非停顿，开发连续推进 | 用户希望一口气做完 | 无 |
| D22 | UI 沿用 MITA Finance 设计系统（token、字体、纸感卡片、侧栏、FAB 聊天面板），信息架构与页面重做；UI 三语；设计由 Claude Design 按 `docs/design/claude-design-prompt.md` 产出 | 用户要求与 MITA Finance 风格一致；复用已验证的设计语言省下整套视觉探索 | 可换 token 但保持同一套语法 |

---

## 9. 待决问题

### 9.1 已回答（2026-09-17）

| 问题 | 回答 | 落实 |
|---|---|---|
| 读哪些邮箱 | 由用户登录添加，数量不限，不预设 | D20；3.2 多邮箱升为核心；Phase 1 支持多账号 |
| 在职状态 / 现雇主 | 取决于用户档案（含经历），不单独提问；档案设计需融合传统 profile 与 LLM 记忆库，后面专门讨论 | D17；3.5 设计说明 |
| 阶段顺序 | 按推荐顺序；顺序本身不重要，计划连续推进 | D21 |
| UI 风格与语言 | 与 MITA Finance 相近；中日英三语并存 | D22；默认语言未定，prompt 中假设 zh |
| 项目名 | Mita JobPilot | D18 |
| 是否公开 | 先私有自用，没问题后再公开 | D19 |
| git 提交身份 | 一起做：改用 GitHub noreply 地址（`<id>+<用户名>@users.noreply.github.com`，在公开提交里隐藏真实邮箱） | D19；已在仓库级 `git config` 设置并改写历史提交 |
| 只读 Web 看板与聊天框时机 | 按推荐（看板 Phase 2，聊天框 Phase 5） | D3 保持 |

### 9.2 仍待回答

1. **浏览器**：Chrome 还是 Edge？Chrome 云端识别支持 zh / ja / en；Edge 本地识别不含 zh / ja 且有静默失败报告。
2. **语音习惯**：会在一句话里混说中日英（如「把 Acme 的状态改成面接中」）吗？会则 Web Speech 单语言模式不够，需 OpenAI 转写或 Deepgram 多语模式。
3. **GPU**：本机有 NVIDIA GPU 吗？决定本地 whisper / embedding 是否可行。
4. **Workday `cxs` POST 搜索**（无服务端状态）算不算「写」？决定能否覆盖大量传统企业岗位。
5. **数据外发接受度**：脱敏后的邮件片段、岗位文本发给 Anthropic / OpenAI 可接受吗？账号的数据保留 / ZDR 设置如何？不接受则抽取需走本地模型。
6. **UI 默认语言**：三语并存已定，默认语言 zh / ja / en 哪个？设计 prompt 暂按 zh。
7. **非 Google 邮箱**：若某个要读的邮箱（如大学邮箱）不是 Google 账号，需要另一条 IMAP 只读路径，与 D5 冲突，届时讨论。

---

## 10. 术语表

| 术语 | 含义 |
|---|---|
| 第一版 / MVP | ROADMAP 的 Phase 1 |
| 选考 / 選考 | 一家公司一次招聘流程中的全部环节 |
| 新卒 / 中途 | 应届毕业招聘 / 有工作经验者招聘 |
| 秋採用 / 通年採用 | 秋季追加招聘 / 全年随时招聘 |
| ES | エントリーシート，报名申请书 |
| 内々定 / 内定 | 非正式录用意向 / 正式录用（10 月 1 日后） |
| マイページ | 企业或 ATS 提供给应聘者的门户，状态常只在门户内显示 |
| ATS | Applicant Tracking System，招聘管理系统 |
| MCP | Model Context Protocol，让 Claude Desktop / Claude Code / Codex 调用本地工具的协议 |
| 区域包 | 按国家 / 市场打包的发件域名规则、阶段枚举、日历里程碑、薪资口径 |
| 求职周期 | 一次完整的求职活动（如「2027 新卒」「2029 转职」），申请记录归属于某个周期 |
| 待复核 `needs_review` | 分类置信度 < 0.7 或匹配含糊而进入的人工复核队列，`jobpilot review` 处理 |
| 待确认 | 展示层占位，来源不足（如会议链接为空）时显示；不是数据库状态。日文界面显示为「待確認」 |
| 待核实 `to_verify` | 岗位招聘状态四分之一：是否仍在招未经官方页面核对 |
| 待排期 `pending_schedule` | 面试事件状态：面试已确定但时间未定 |
| 驳回 `dismissed` | 用户对搜索结果中某岗位的否定反馈，写入交互记录，永不再展示 |
| 排除（申请） | 申请进入「不合适」并填写排除原因 |
| 排除记录（岗位） | 岗位招聘状态四分之一：已截止、已落选、放弃或不合适，保留原因、时间、来源 |
| ghosted | 申请上的派生标记：进行中状态下 30 天无任何事件 |
