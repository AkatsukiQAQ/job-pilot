# Claude Design 第二轮 prompt（2026-09-18，已发送）

在第一轮对话里接着粘贴。目的：基于已采纳的 A（tokens.css v0.1）与 B（ia-and-flows.md v0.1），先拿到第一步要实现的四页 HTML，再拿组件规范与三语字典。

---

接着上一轮继续。A（tokens.css v0.1）和 B（ia-and-flows.md v0.1）已被采纳，以它们为准，不要回头改 token 与导航树。

## 这一轮要交付什么

先交付 C 的前四页，停下等我反馈；反馈后再出 D 和 E。

### 批次 C-1：四页 HTML 原型

1. `01-dashboard.html` 看板（IA 第 3 节 01）
2. `02-pipeline.html` 申请 Pipeline（02，只做「表格」视图，看板视图先不画）
3. `03-application.html` 申请详情（03）
4. `12-settings.html` 设置（12 的「设置」段：求职周期管理 · 时区与语言；「信息源」段留空态即可）

每页要求：
- 自包含单文件，1440 宽桌面，内联 tokens.css v0.1 的全部内容，字体用 Google Fonts link（Kalam / Indie Flower / Klee One / Fraunces / JetBrains Mono / Noto Sans JP）。
- 完整应用外壳：左侧栏按 B 第 2 节导航树（三组 eyebrow、Lucide 图标、当前页高亮），未做的导航项右侧带「Soon」小徽标；顶栏含 周期切换器 · 语言 zh/ja/en · 主题切换。**没有右下角 FAB，没有聊天浮层**（B 已取消）。
- 三语：页面内嵌 zh / ja / en 字典，顶栏切换语言时用 `data-lang` 切换全部界面文案；数据原文（公司名、岗位名、邮件主题）不翻译。默认显示 zh。
- 暗色模式：主题切换在 `<html data-theme="dark">` 上生效，两套都能看。
- 每页至少画出三种态：有数据 · 空周期 · （详情页）低置信待复核事件。

### 本轮特别注意：这是第一版，数据全靠手动录入

第一版还没有接 Gmail，所以：
- 01 看板：不画「信息源健康条」和「Mita 的提醒」AI 卡（位置留空白卡片写「即将推出」即可）；KPI 四格、今日与本周待办、后续面试、最近变化、状态分布条照 B 画。
- 02 Pipeline：顶部要有「添加申请」按钮和它展开的表单（公司 · 岗位 · track · 初始状态 · 岗位链接 · 备注），来源徽标一律「手动」。
- 03 申请详情：要有「改状态」→ 行内确认卡片（变化前 line-through → 变化后高亮，确认 / 取消），「记事件」表单（事件类型 · 时间 · 摘要），备注区。事件时间线的来源徽标一律「手动」。
- 12 设置：周期列表（名称 · 类型 · 区域包 · 起止 · 申请数 · 「设为当前」）+ 新建周期表单；时区与语言两个下拉。

### 批次 D：components.md

第一版用到的组件先写全：PaperCard · Button 四变体三尺寸 · NavItem 三态 + Soon 徽标 · KPI tile · 状态 chip 12 态（引用 tokens 里的 status-* 变量）· 来源徽标 · 「待确认」占位 · 「待复核」标记 · 「已手动覆盖」图标 · 确认卡片 · Table · EmptyState · Input / Select · 周期切换器。每个组件给：用途 · 结构 · 精确 Tailwind class 字串 · 状态变体 · 三语文案键名。其余组件（岗位卡、四分徽标、记忆事实卡等）列名字和一句话即可，下轮再细。

### 批次 E：i18n.json

四页 HTML 与 components.md 里出现过的全部界面字串，结构 `{ "key": { "zh": "", "ja": "", "en": "" } }`，键名用点分层（`nav.pipeline`、`status.interviewing`、`action.confirm`）。品牌字标 Mita JobPilot 不翻译。日期示例统一 `2026-10-01（水）14:00 JST` 风格。

## 不变的规则（复述以防遗漏）

- 示例数据全部虚构：Acme Robotics / 株式会社アクメ、Nimbus AI、Kappa Motors、Hoshino Consulting；不要真实公司名、真实人名、真实邮箱。
- 页面上不存在「发送 / 投递 / 回复 / 申请」按钮，官方入口一律外链图标。
- 不编造链接和日期：信息缺失处用「待确认」虚线占位。
- 状态 chip 用 tokens 的 12 态变量，不自造颜色；不用渐变背景、emoji、重阴影。
- 用户状态覆盖自动状态时显示「已手动覆盖」图标与 tooltip。
