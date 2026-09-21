# Mita JobPilot · C-1 原型（2026-09-18）

四页自包含 HTML，浏览器直接打开；页面间用侧栏互相跳转。

- 01-dashboard.html    看板（KPI · 今日与本周 · 后续面试 · 最近变化 · 状态分布；「Mita 的提醒」「信息源」为即将推出占位）
- 02-pipeline.html     申请 Pipeline（表格视图 · 添加申请表单 · 状态组 / track / 关键词筛选）
- 03-application.html  申请详情（改状态 → 确认卡片 · 记事件表单 · 低置信待复核事件 · 备注）
- 12-settings.html     信息源（空态）· 设置（周期管理 + 新建 · 时区与语言）

三种态：顶栏周期切换到「2029 转职」（0 条申请）即空周期态；详情页时间线里 2026-09-14 那条为低置信待复核事件。
三语：顶栏 中 / 日 / EN；暗色：月亮图标（<html data-theme="dark">）。设计宽度 1440。
内联：tokens.css v0.1（@theme → :root 机械转换）与页面运行时；字体走 Google Fonts；运行时依赖 React 经 CDN 加载，需联网。
