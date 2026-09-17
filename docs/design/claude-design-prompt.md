# Claude Design prompt：Mita JobPilot UI

> **使用说明（不要粘贴这一段）**
>
> 1. 把下面「── prompt 开始 ──」到「── prompt 结束 ──」之间的全部内容作为第一条消息粘进 Claude Design。
> 2. 建议同时附上 MITA Finance 仓库里的 `design/screenshots/dashboard-a.png` 作为视觉锚点；不附也能用，prompt 自带全部 token。
> 3. prompt 要求 Claude Design 分批交付：先 A（tokens.css）+ B（信息架构与流程），停下等你反馈；确认后再按 3 到 4 页一批出页面原型。每批产出保存到本仓库 `docs/design/output/`，我据此蒸馏成 `docs/DESIGN.md` 与前端 token 文件。
> 4. 所有示例数据必须是虚构公司；如果 Claude Design 用了真实公司名或真实人名，让它改。

---

── prompt 开始 ──

# 任务：为 Mita JobPilot 设计完整 UI

你是资深产品设计师。请为 **Mita JobPilot** 设计全部界面。它是 **MITA Finance**（一个个人记账助手）的姊妹产品，必须与 MITA Finance 共用同一套设计语言（下文逐字给出 token 与组件语法），但信息架构、页面和求职专用组件全部重新设计。请严格按第 12 节的交付物格式与分批节奏产出。

## 1. 产品是什么

Mita JobPilot 是一个**本地优先、只读接入外部信息源、带 AI 对话与记忆的个人求职工作台**。它从 Gmail、Google Calendar、LinkedIn 官方数据导出等来源**只读**地推导出用户参与的每一个选考流程的状态、截止日期和面试日程；用户可以用 Claude 或 GPT 对话（含语音）查询进度、评估岗位、操作系统；记忆系统记住用户的画像、偏好和申请结果，并据此搜索和排序新岗位。

首个真实场景是日本的应届生就活，但设计**不得假设**地区或求职类型：同一套界面要能服务将来的在职跳槽和其他国家的求职。

## 2. 影响 UI 的硬规则（不可违反）

1. **外部只读**。界面上不存在任何「发送 / 投递 / 回复 / 申请 / 写入日历」的动作。通往公司官网或报名页的入口一律是外链按钮（图标为外链箭头），文案是「前往官方入口」而不是「申请」。
2. **模型只能提议，用户确认**。AI 对话中任何会改动本地数据的操作（改状态、记录申请、记笔记、保存记忆事实）都先以「确认卡片」形式出现：摘要 + 变化前 / 后 + 「确认」「取消」两个按钮。确认前界面不变。确认卡片是一等组件，在聊天面板、待复核队列、记忆收件箱里都会出现。
3. **用户状态覆盖自动状态**。申请记录同时有「自动状态」（由邮件 / 日历推导）和「用户状态」（用户手动设置）。用户改过的记录要有明确的「已手动覆盖」标识，并能一键看到自动状态是什么。
4. **不虚构**。来源不足就显示「待确认」占位：面试没有会议链接就显示「待确认」，绝不画一个假链接；日期不确定就显示「待确认」，不填一个猜的日期。
5. **每条信息带出处**。每个事件、每条记忆事实、每个岗位都带来源徽标（Gmail / Calendar / LinkedIn 导出 / 手动 / 聊天 / 导入 / 研究请求）和时间；岗位另带「核验日期」。
6. **匹配度是分析判断，不是录用概率**。所有匹配度、成长性分数的旁边都要有「分析判断」小字标注，不能画成成功率仪表。
7. **多求职周期**。顶栏有周期切换器（如「2027 新卒」「2029 转职」），所有数据按周期归属。
8. **多邮箱**。用户可以登录多个 Google 账号，数量不限；信息源页要能列出每个账号的健康状态。
9. **时间按 JST 展示**（时区可配置），格式如 `2026-10-01（水）14:00 JST`；存储时区不是设计关心的事。
10. **界面三语**：简体中文 / 日本語 / English 可切换；**品牌字标永远是英文**「Mita JobPilot」；用户数据（公司名、岗位名、邮件主题）保持原文不翻译。

## 3. 用户与使用场景

- 单人使用，本机运行（Windows 桌面），偶尔用手机看面试与截止（通过内网访问）。
- 数据天然是日英中混排：公司名可能是日文（株式会社アクメ），岗位名可能是英文（Applied Research Engineer），用户用中文思考。排版必须能承受混排，CJK 正文行高放宽到 1.75。
- 每天打开一次到几次；核心动作是「看今天有什么截止 / 面试」「看某公司进行到哪」「复核几条自动识别」「评估一条新岗位」「和 AI 聊几句」。
- 桌面 1440 宽为主；看板与面试两页必须在 390 宽的手机上可用。

## 4. 与 MITA Finance 的血缘

**直接复用**（不要重新发明）：设计 token、字体体系、`.card-paper` 纸感卡片、固定左侧栏与黄色导航高亮、顶栏结构（⌘K 搜索 / 语言 / 主题 / 头像）、右下角琥珀渐变 FAB 与聊天面板、手绘风格 SVG 图表、吉祥物「M」圆形头像、品牌字标用 `.hand` 手写体英文。

**全部重做**：信息架构、所有页面、求职专用组件（状态 chip、四分徽标、来源徽标、确认卡片、时间线、日程 Agenda 等）。

**MITA Finance 唯一的审美规则，原文照录，必须遵守**：

> The prototype is deliberately paper-like and quiet. No gradients as page backgrounds. No emoji used as UI. No heavy drop shadows. If you find yourself adding visual noise to compensate for a weak layout, fix the layout.

风格关键词：warm · papery · handwritten · quiet · earthy · ink-on-cream · analog-journal · unshouty。感觉像一本摊开的求职手账，不像 SaaS 后台。

## 5. 设计 token（逐字沿用，Tailwind v4 `@theme` 格式）

```css
@theme {
  /* Surface: cream paper, warm yellow undertone */
  --color-cream-50:  #FFFEF8;   /* 卡片 / 输入框表面 */
  --color-cream-100: #FEF9E7;   /* 页面底色、hover 填充 */
  --color-cream-200: #FCF3CF;   /* 分隔线、浅填充、表头、AI 气泡 */
  --color-cream-300: #F9E79F;   /* 导航激活态 pill */
  --color-cream-400: #F4D03F;   /* 高亮 ring、「待确认」虚线 */
  --color-cream-500: #E8C547;   /* focus outline、涂鸦下划线 */

  /* Ink: warm near-black text and borders */
  --color-ink-100: #F2ECE0;
  --color-ink-200: #E5DED0;     /* 默认 1px 边框、网格线 */
  --color-ink-300: #C8BEB0;
  --color-ink-400: #8B7E6C;     /* 禁用文字 */
  --color-ink-500: #6B5E4E;     /* 次要文字、标签、eyebrow */
  --color-ink-700: #3D342A;     /* 正文 */
  --color-ink-900: #1F1A14;     /* 主文字，也是主按钮填充 */

  /* Accent: earth tones, never synthetic neons */
  --color-accent-amber: #D97706;
  --color-accent-olive: #7A8450;
  --color-accent-rose:  #B56576;
  --color-accent-sage:  #9DB17C;

  /* Semantic state: muted, never pure red/green */
  --color-pos-500: #4F7B49;  --color-pos-50: #E8F0E0;
  --color-neg-500: #B8563E;  --color-neg-50: #F5E6DE;
  --color-warn-500: #D97706; --color-warn-50: #FFF8E1;

  --spacing-gutter: 4rem;    /* 主内容右侧留白，避开浮动按钮 */

  --font-sans:      "Noto Sans JP", "Geist", ui-sans-serif, system-ui, -apple-system, "Helvetica Neue", sans-serif;
  --font-hand:      "Kalam", "Indie Flower", "Klee One", cursive;
  --font-hand-body: "Indie Flower", "Kalam", "Klee One", cursive;
  --font-num:       "Klee One", "Kalam", "Indie Flower", cursive;
  --font-serif:     "Fraunces", "Noto Sans JP", serif;
  --font-mono:      "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}

/* 页面背景：两层暖黄径向渐变叠在 cream-100 上，attachment fixed。这是唯一允许的「渐变」 */
body {
  background:
    radial-gradient(1200px 800px at 80% -10%, rgba(228,195,98,.18), transparent 60%),
    radial-gradient(900px 700px at -10% 110%, rgba(228,195,98,.10), transparent 60%),
    var(--color-cream-100);
  background-attachment: fixed;
  color: var(--color-ink-900);
  font-family: var(--font-sans);
}

.hand      { font-family: var(--font-hand); font-weight: 700; }   /* 品牌字标与真正的大标题 */
.hand-body { font-family: var(--font-hand-body); font-weight: 400; } /* 首屏问候、AI 提示标题 */
.serif     { font-family: var(--font-serif); }                    /* 页面标题 */
.num       { font-family: var(--font-num); font-variant-numeric: tabular-nums; letter-spacing: .2px; } /* KPI 大数字 */

.card-paper {
  background: var(--color-cream-50);
  border: 1px solid var(--color-ink-200);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(95,75,40,.04), 0 8px 24px -12px rgba(95,75,40,.12);
}

/* 暗色模式（整套值已定，请在 tokens.css 中保留） */
[data-theme="dark"] {
  --color-cream-50: #1A1712; --color-cream-100: #221E17; --color-cream-200: #2B261D;
  --color-cream-300: #3D3524; --color-cream-400: #5C4F32; --color-cream-500: #7A6B44;
  --color-ink-900: #F5EFE2; --color-ink-700: #D8CEBA; --color-ink-500: #A89E8A; --color-ink-400: #847B68;
  --color-ink-300: #4A4338; --color-ink-200: #35302A; --color-ink-100: #2A2620;
  --color-pos-500: #8FB37E; --color-pos-50: #2B3426; --color-neg-500: #D88968; --color-neg-50: #3A2A22;
}
[data-theme="dark"] .card-paper { background: var(--color-cream-200); border-color: var(--color-ink-300);
  box-shadow: 0 1px 2px rgba(0,0,0,.2), 0 8px 24px -12px rgba(0,0,0,.4); }
```

几何与动效：圆角 按钮 / 输入 / 导航项 8px（`rounded-lg`），卡片 14px，模态与表格容器 16px（`rounded-2xl`），chip 全圆；边框 1px，卡片用 `ink-200`，页面骨架分隔用 `cream-200`；focus `outline: 2px solid var(--color-cream-500); outline-offset: 2px`；动效 `--ease: cubic-bezier(.4,0,.2,1)`，`150ms` 颜色、`200ms` 位移、`300ms` 面板；可点击卡片 hover `translateY(-2px)` + 轻微加深阴影；尊重 `prefers-reduced-motion`。

**需要你新增的 token**（在同一土色系内提出，全部给出 light 与 dark 两组值，禁止纯红 / 纯绿 / 霓虹，色觉障碍友好，同组状态用同一色相不同明度以减少色相数量）：

- 12 个应聘状态的 chip 色（前景 + 背景），按四组分配色相：
  - 未开始：`unrecorded` 未记录 · `considering` 考虑中 · `preparing` 准备申请
  - 进行中：`applied` 已申请 · `assessment` 笔试或课题 · `interviewing` 面试中
  - 成功终态：`offer` Offer · `accepted` 已承诺 · `joined` 已入职
  - 结束终态：`rejected` 已落选 · `withdrawn` 主动放弃 · `unsuitable` 不合适
- 岗位招聘状态四分徽标：`confirmed_open` 确认在招 · `to_verify` 待核实 · `special_lead` 特别线索 · `excluded` 排除记录
- 7 种来源徽标（小、低对比、可并排）：Gmail · Calendar · LinkedIn 导出 · 手动 · 聊天 · 导入 · 研究请求
- 「待确认」占位：`1px dashed var(--color-cream-400)` + `cream-100` 底 + `ink-500` 文字，沿用 MITA 聊天里内嵌结果卡的虚线做法
- 信息源健康五态：`healthy` 正常 · `degraded` 降级 · `auth_required` 需重新授权 · `unavailable` 不可用 · `disabled` 已禁用
- 两个派生标记：`ghosted`（长期沉默，整行灰显 `ink-400` + 斜体小标）与「已手动覆盖」（小图标 + tooltip）

## 6. 字体角色（逐字沿用）

| 角色 | class 字串 |
|---|---|
| eyebrow / 小标签 | `text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500` |
| 页面标题 | `serif text-3xl font-medium tracking-tight text-ink-900` |
| 首屏问候 | `hand-body text-4xl md:text-5xl text-ink-900`，可尾随一个琥珀色 ✦ 小装饰（唯一允许的装饰符号） |
| 卡片标题 | `text-sm font-semibold text-ink-900` |
| 提示 / 次要 | `text-xs text-ink-500` |
| 表单标签 | `text-xs font-semibold uppercase tracking-wide text-ink-500` |
| KPI 大数字 | `num text-3xl md:text-4xl leading-tight` + 语义色 |
| 表格数字 / 日期 / ID | `font-mono text-sm`，右对齐；日期一律 mono |
| 品牌字标 | `hand text-xl leading-[1.05] text-ink-900` + 副标 `text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-500` |

正文 16px，CJK 行高 1.75；ja / zh 界面下手写体回退到 Klee One（ja）与 Ma Shan Zheng（zh），但品牌字标锁定 Kalam。

## 7. 组件语法（逐字沿用，Tailwind class）

```
PaperCard    : card-paper p-5   （KPI 用 p-4；高亮变体 bg-cream-200 ring-2 ring-cream-400）
Button base  : inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors
               focus-visible:ring-2 focus-visible:ring-ink-900/30 disabled:cursor-not-allowed
  primary    : bg-ink-900 text-cream-50 hover:bg-ink-700 disabled:bg-ink-200 disabled:text-ink-500   ← 主按钮是墨色，不是品牌色
  outline    : bg-transparent text-ink-900 border border-ink-200 hover:bg-cream-100
  ghost      : bg-transparent text-ink-700 hover:bg-cream-100
  danger     : bg-neg-500 text-cream-50
  sizes      : sm h-8 px-3 text-xs | md h-10 px-4 text-sm | lg h-12 px-5 text-base
NavItem      : flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
  active     : bg-cream-300 text-ink-900        ← 黄色纸面高亮，不是反白
  inactive   : text-ink-700 hover:bg-cream-200/60
  upcoming   : text-ink-400 + 尾部 <span class="ml-auto rounded-full bg-cream-200 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-500">Soon</span>
Sidebar      : md:w-60 h-full border-r border-cream-200 p-4，透明底（让页面渐变透出来）；顶部品牌块：48px 透明 logo + 字标 + 副标；底部「收起」按钮
TopBar       : h-14 border-b border-cream-200；左：搜索框 max-w-xl + ⌘K kbd；右：周期切换器 · 语言 · 主题 · 头像
Main         : p-4 md:p-6 md:pr-gutter；纵向节距 space-y-5；网格 gap-4
Pill / chip  : inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold + 前导 h-1.5 w-1.5 rounded-full 圆点
Status chip  : rounded-full border px-2 py-0.5 text-[11px] font-semibold（前景 / 背景 / 边框同色相三档）
Input        : w-full rounded-lg border border-ink-200 bg-cream-50 px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-ink-900/20
Alert        : rounded-lg border px-3 py-2 text-sm；error bg-neg-50 text-neg-500 border-neg-500/30；success bg-pos-50 text-pos-500 border-pos-500/30；warning bg-cream-100 text-warn-500 border-warn-500/30；info bg-cream-100 text-ink-700 border-ink-200
Modal        : 背景 bg-ink-900/40 backdrop-blur-sm；面板 rounded-2xl border border-cream-200 bg-cream-50 shadow-xl max-w-md
Table        : 容器 overflow-hidden rounded-2xl border border-cream-200 bg-cream-100；表头 bg-cream-200/60 text-xs uppercase tracking-wide text-ink-500；行 divide-y divide-cream-200；单元格 px-4 py-3
Empty state  : PaperCard 内居中：28px ink-500 图标 + text-lg font-semibold 标题 + max-w-md text-sm text-ink-500 说明 + 一个 primary 按钮
Icons        : Lucide，24 视窗，stroke 2，round caps，默认 18px
Charts       : 手绘 SVG，虚线网格 ink-200 "3 4"，线宽 1.8，点 r=3 cream-50 填充；不用图表库风格

Chat FAB     : 56×56 圆，bottom/right 24，background linear-gradient(135deg,#F4C430,#D97706)，白色对话气泡图标，2.8s 软脉冲
Chat panel   : 380×520（桌面可拉宽到 480），bg cream-50，1px ink-200，radius 16，shadow 0 24px 60px -10px rgba(70,50,20,.35)
  header     : linear-gradient(180deg,cream-200,cream-100)，34px 圆形琥珀渐变头像写手写「M」，标题 hand 18/700「Mita」，状态行 10.5px ink-500 + 6px pos-500 圆点
  bubble     : max-width 86%；用户 bg ink-900 / cream-50 文字，radius 14 14 3 14；AI bg cream-200 / ink-900 文字，radius 14 14 14 3；13px / 1.55
  result card: 气泡内嵌 padding 12 radius 10 bg cream-100，1px dashed cream-400；10.5px 大写标签 + hand 26/700 数值 + 11px 副文
  chips      : padding 5px 10px，全圆，bg cream-50，1px ink-200，ink-700，11.5px
  typing     : 三个 6px ink-400 圆点 bounce 1.2s 错位 .15s
  input bar  : 顶部 1px ink-200，padding 10；输入 h36 radius 10；发送按钮 36×36 radius 10 bg ink-900
```

## 8. 信息架构

侧栏（固定，从上到下）：

1. 看板（首页）
2. 申请 Pipeline
3. 岗位
4. 面试
5. 记忆收件箱
6. 待复核
7. 研究请求
8. 信息源
9. 设置

顶栏：⌘K 全局搜索（搜公司 / 岗位 / 邮件主题） · 求职周期切换器（当前周期名 + 下拉） · 语言 zh / ja / en · 主题 · 头像。

全局：右下角 FAB 打开聊天面板，任何页面可用；面板可从右侧停靠为 480 宽侧栏。

## 9. 页面清单（13 页 + 2 张手机版）

每页给出必备元素；布局由你设计，但首屏不许是营销页。

1. **看板（首屏）**：日期 eyebrow + 手写问候；KPI 四格（进行中流程数、本周截止数、7 天内面试数、待复核数，第四格用高亮变体）；「今日与本周」待办列表（截止 / 面试 / 需跟进 / 门户待查看，各带来源徽标与 JST 时间）；「后续面试」区（确认与待排期分开）；状态分布（12 态四组的手绘横向堆叠条，不用饼图）；信息源健康状态条（每个邮箱账号一个小圆点 + 最近同步时间）；AI 提示卡「Mita 的提醒」（hand-body 标题）。
2. **申请 Pipeline**：表格与看板两种视图切换（分段控件）；按 12 态分组；每行：公司（原文）+ 岗位 + 状态 chip + 最近事件 + 下一步 / 截止（mono 日期）+ 来源徽标 + 「已手动覆盖」标识；ghosted 行灰显；筛选：状态组、周期、track（实习 / 新卒 / 中途）、邮箱账号；空状态。
3. **申请详情**：头部：公司、岗位、track、状态 chip（旁边显示自动状态 vs 用户状态，含「改状态」按钮 → 确认卡片）；事件时间线（append-only，每条：类型、时间、来源徽标、摘要、关联邮件主题、置信度小字，低置信标「待复核」）；面试子区；「门户待查看」条目带外链按钮与「回填结果」按钮；备注区；「前往官方入口」外链。
4. **岗位工作台**：左侧筛选栏（关键词、方向、行业、招聘对象、招聘状态四分、匹配度、应聘进度、仅收藏）；顶部排序（综合 / 匹配度 / AI 相关度 / 薪资 / 成长性 / 截止 / 公司名）；岗位卡片：公司与行业、岗位名、四分徽标、方向 tag、薪资及口径、匹配度（数值 + 「分析判断」标注）、我的应聘状态、核验日期、动作：收藏 / 加入比较 / 查看详情 / 前往官方入口 / 记录备注；「评估这条岗位」入口：粘贴链接或文本的输入框。
5. **岗位详情侧板**：完整工作内容、薪资口径、匹配理由、需补足的部分、成长空间与风险、是否要求先实习、未确认事项（用「待确认」样式）、官方来源与核验日期、目击记录（最近三次轮询）、备注、改应聘状态（→ 确认卡片）。
6. **并排比较**：最多三列；维度行：工作内容、匹配度、技能缺口、薪资、成长性、截止时间、申请资格、不确定事项、建议下一步；单元格差异高亮用 cream-200 而非彩色。
7. **面试日程**：左侧月份概览（小格子，有面试的日子画手绘圆圈），右侧 Agenda 列表；「已确认」与「待排期」两个分区；每场：JST 日期时间、公司、岗位、轮次、线上 / 线下、工具或地点、会议链接（无则「待确认」占位）、跳到对应申请、「回填结果」按钮。
8. **聊天面板**：头部有 Claude / GPT 分段切换；消息流；流式输出中的光标；确认卡片（摘要 / 变化前后 / 确认 / 取消）出现在 AI 气泡下方；内嵌结果卡（如「本周截止 3 项」）；建议 chips；输入条：文本框 + 按住说话麦克风按钮（三态：闲置 / 按住录音（琥珀脉冲）/ 转写中）+ 语言小标（ja / zh / en）+ 发送；语音转写回显为一条带麦克风图标的用户气泡；顶部「待处理提议 2」小标。
9. **记忆收件箱**：候选事实卡列表；每卡：类别标签（目标岗位 / 年薪期望 / 地点偏好 / 硬性排除 …）、事实正文、来源引文（灰底引号块）、置信度、来源徽标、时间；动作：确认 / 编辑 / 否决；若与现有事实冲突，显示「将取代：旧事实」链条；右侧或下方「当前画像」渲染块（活跃事实按类别分组，手写体小标题）。
10. **待复核队列**：低置信分类列表；每行：邮件主题（原文）、发件人域名、系统猜测（分类 + 公司 + 阶段 + 置信度）、候选申请二到三个单选、动作：接受 / 改为 / 忽略；批量操作栏。
11. **研究请求**：任务模板卡（搜索新岗位 / 复核当前清单 / 寻找可主动敲门的公司与团队 / 清理失效岗位 / 自定义）→ 生成的提示词预览（mono，可复制）→ 「粘贴结果」大文本框 → 解析预览表（将导入的岗位 / 线索，标「待复核」）→ 导入按钮。
12. **信息源与设置**：邮箱账号列表（地址、健康五态、最近同步、消息数、「重新授权」按钮、「添加账号」）；Calendar、LinkedIn 导出（最近导入日期、「导入 ZIP」）、岗位源开关与配额条；求职周期管理（列表 + 新建：名称、类型、区域包、起止）；模型设置（Claude / GPT 各一个模型字串、默认便宜模型开关）；密钥槽位（固定名单，只显示「已设置 / 未设置」，不显示值）；时区与语言。
13. **首次引导向导**：步骤条：数据目录 → 选择区域包 → 创建第一个求职周期 → Google Cloud 项目分步说明（截图占位）→ 导入 OAuth 客户端文件 → LLM key → 完成。每步一张 PaperCard，纸感、不催促。

手机版（390 宽）：看板（KPI 两列、待办列表、面试）、面试日程（只保留 Agenda）。侧栏折叠为底部标签栏（看板 / 申请 / 面试 / 聊天）。

## 10. 核心用户流程（请在 B 交付物中分步写出）

1. 新邮件到达 → 自动分类 → 看板「最近变化」出现新事件 → 用户点开申请详情 → 若标「待复核」则接受或修正。
2. 粘贴一条 JD 链接或文本 → 「评估这条岗位」→ 得到匹配判断与缺口 → 存为手动岗位 → 可选「记录申请」→ 确认卡片。
3. 语音说「把 Acme 的状态改成面试中」→ 转写回显 → AI 提议 → 确认卡片 → 确认 → 详情页状态更新并标「已手动覆盖」。
4. 邮件只写「请查看マイページ」→ 看板出现「门户待查看」→ 用户点外链看门户 → 回来点「回填结果」→ 选择结果 → 事件写入。
5. 顶栏切换求职周期 → 全站数据切换 → 看板问候语与 KPI 随之变化。
6. 研究请求：选模板 → 复制提示词到外部 AI → 粘贴结果 → 解析预览 → 导入为「特别线索」→ 出现在岗位工作台并标「待核实」。
7. LinkedIn 导出 ZIP 导入 → 进度 → 摘要（新增 / 更新 / 跳过）→ Pipeline 出现来源为「LinkedIn 导出」的申请。
8. 信息源页「添加账号」→ 浏览器授权（界面只需一个等待态）→ 列表出现新账号 → 首次回填进度条。

## 11. 文案规则

- 三语字典：zh（默认）/ ja / en。所有界面字串走字典；用户数据保持原文。
- 品牌字标固定英文「Mita JobPilot」，副标三语（如 zh「你的求职副驾」/ ja「あなたの就活コパイロット」/ en「Your job-hunt copilot」）。
- 语气：温暖、第一人称品牌、不催促、不用感叹号；用「·」做分隔，用「…」做省略。
- 固定术语（四个近义词对应四个不同概念，不得混用）：
  - **待复核**：自动识别置信度低，进入人工复核队列
  - **待确认**：信息缺失的展示占位（如无会议链接），不是状态
  - **待核实**：岗位是否仍在招未经官方页面核对（招聘状态四分之一）
  - **待排期**：面试已确定但时间未定
- 日期：`2026-10-01（水）14:00 JST`；相对时间只在待办里用（「3 天后」）。
- 数字：申请数、天数用 `.num` 手写体；金额用 mono，日元不带小数。

## 12. 交付物与节奏

全部文件名固定如下，便于我落库：

- **A `tokens.css`**：完整 Tailwind v4 `@theme` 块 = 第 5 节原 token + 你新增的全部 token（状态 chip、四分徽标、来源徽标、健康五态、待确认占位），含 `[data-theme="dark"]` 整套；附一张「token → 用途」表。
- **B `ia-and-flows.md`**：侧栏导航树、13 页清单（每页一句目的 + 必备元素）、第 10 节 8 条流程的分步描述（每步写清页面、组件、状态变化）。
- **C 页面原型**：每页一个**自包含 HTML 文件**（`01-dashboard.html`、`02-pipeline.html` … `13-onboarding.html`，手机版 `m1-dashboard-390.html`、`m2-interviews-390.html`），1440 宽，内联 `tokens.css` 与 Google Fonts 引入，用 `data-lang="zh|ja|en"` 属性切换语言（字典嵌在文件里），全部数据虚构。
- **D `components.md`**：求职专用组件规范：状态 chip（12 态 × light / dark 色值）、四分徽标、来源徽标、确认卡片、时间线条目、待排期条目、待复核行、记忆事实卡、信息源状态条、周期切换器、按住说话按钮三态、「待确认」占位、「已手动覆盖」标识、ghosted 行。每个给出结构、class 字串、状态、无障碍要点。
- **E `i18n.json`**：所有出现过的界面字串，`{ key: { zh, ja, en } }`。
- **F `open-questions.md`**：你在设计中遇到的歧义与建议。

**节奏**：先交 A + B，然后停下等我反馈；确认后按 3 到 4 页一批交 C（顺序 1-2-3-7 → 4-5-6 → 8-9-10 → 11-12-13 → 手机版）；最后交 D、E、F。每批只做该批的事，不要一次全出。

## 13. 示例数据（全部虚构，请只用这些或同样明显虚构的名字）

公司：株式会社アクメ（Acme Robotics，机器人）· Nimbus AI（AI 初创）· Kappa Motors（自动驾驶）· Hoshino Consulting（咨询）· Meridian Bank（金融）· Sora Devices（硬件）。
岗位：Applied Research Engineer · Forward Deployed Engineer · Machine Learning Engineer · Software Engineer · AI Product Manager。
求职周期：「2027 新卒」（当前）、「2029 转职」（示例第二周期）。
人名一律不出现；邮箱只用 `example.com` 域名；面试链接只用 `https://meet.example.com/…`。

## 14. 反模式（出现即改）

渐变页面背景（除第 5 节那两层暖黄径向渐变）· emoji 当 UI · 重投影 · 霓虹或饱和红绿 · 通用 SaaS 仪表盘感（大圆环进度、KPI 箭头满屏）· 编造的链接 / 日期 / 会议号 · 任何「申请 / 投递 / 发送 / 回复」按钮 · 把匹配度画成录用概率 · 用真实公司或真实人名做示例 · 中日英混排时行距过紧。

── prompt 结束 ──
