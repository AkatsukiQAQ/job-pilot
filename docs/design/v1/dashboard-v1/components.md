# Mita JobPilot · components.md（交付物 D · v0.2 · 对应 C-1 四页）

配套 `tokens.css` v0.1、`i18n.json` v0.2。class 字串为 Tailwind v4；`tokens.css` 中的 `--color-*` 自动生成同名工具类（`--color-status-applied-bg` → `bg-status-applied-bg`、`--color-source-manual` → `text-source-manual`）。文案一律走字典，本文只写键名（`action.confirm`）。C-1 原型用内联样式镜像了这些 class，值一一对应。

## 0. 通用约定

- 图标 Lucide，24 视窗，stroke 2，round caps；默认 18px，chip / 徽标内 11–12px。
- 日期、时间、ID、金额 `font-mono`；格式 `2026-10-01（水）14:00 JST`；相对时间（「3 天后」）只在待办里出现，且与绝对时间并列。
- 颜色不是唯一信号：每个 chip / 徽标 / 圆点旁都有文字或 `aria-label`。
- focus：`focus-visible:outline-2 focus-visible:outline-cream-500 focus-visible:outline-offset-2`（全局定义一次）。
- 动效：`transition-colors duration-150`；位移 `duration-200`；面板 `duration-300`；`ease-quiet`；`motion-reduce:transition-none motion-reduce:animate-none`。
- 用户数据（公司名、岗位名、邮件主题、备注）原文显示、不翻译；允许换行的字段加 `[overflow-wrap:anywhere]`，只有系统文案可 `truncate`（配 `title`）。
- 页面上不存在「发送 / 投递 / 回复 / 申请」动作；通往外部的入口只有「前往官方入口」外链按钮。
- 第一版全部手动录入：来源徽标一律 `manual`；自动状态只从用户记录的事件推导（见 §9）。

---

## 1. PaperCard 纸感卡片

用途：所有内容容器。
结构：`<section class="card-paper p-5"> 标题行（h2 text-sm font-semibold text-ink-900 + 右侧 text-xs text-ink-500 说明 / 链接 / 按钮）→ 内容 </section>`

| 变体 | class | 用在 |
|---|---|---|
| 默认 | `card-paper p-5` | 看板各区、详情各区、设置各块（`px-6 py-5`） |
| KPI | `card-paper p-4` | KPI tile |
| 高亮 | `card-paper p-4 bg-cream-200 ring-2 ring-cream-400` | 待复核 KPI |
| 头部 | `card-paper p-6 grid grid-cols-[minmax(0,1fr)_auto] gap-6 items-start` | 申请详情头部 |
| 可点击 | `card-paper lift`（`lift` = `transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[0_2px_4px_rgba(95,75,40,.06),0_14px_28px_-12px_rgba(95,75,40,.18)]`） | 整卡链接 |
| 占位 | 卡内 `pending rounded-[10px] px-3.5 py-4 text-center text-xs leading-[1.7]` + 加粗 `placeholder.coming_soon` + 说明 | 「Mita 的提醒」「信息源」即将推出 |
| 表单区 | 卡内 `mt-3.5 rounded-[10px] border border-dashed border-ink-300 bg-cream-100 p-4 grid gap-3` | 记事件、新建周期（卡内展开的次级表单） |

暗色由 `[data-theme="dark"] .card-paper` 接管，组件不加 `dark:`。
无障碍：整卡可点时用 `<a>` 包卡；卡内另有按钮时卡本身不可点。

## 2. Button 按钮

结构：`<button class="{base} {variant} {size}"> [icon 14–16] 文案 [尾部 icon] </button>`

```
base     inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors
         focus-visible:ring-2 focus-visible:ring-ink-900/30 disabled:cursor-not-allowed
primary  bg-ink-900 text-cream-50 hover:bg-ink-700 disabled:bg-ink-200 disabled:text-ink-500
outline  bg-transparent text-ink-900 border border-ink-200 hover:bg-cream-100
ghost    bg-transparent text-ink-700 hover:bg-cream-100
danger   bg-neg-500 text-cream-50 hover:bg-neg-500/90
sm  h-8 px-3 text-xs   ·   md  h-10 px-4 text-sm   ·   lg  h-12 px-5 text-base
xs  h-[26px] px-2.5 text-xs（行内 接受 / 修正）
icon-only  size 基础上加 w-8 p-0（sm）/ w-10 p-0（md），必须有 aria-label
```

| 变体 | 语义 | 例（键名） |
|---|---|---|
| primary | 每屏最多一个：页面主动作（`action.add_application`）、表单保存（`action.save`）、确认卡片的 `action.confirm`、空状态 CTA | 02 标题行、确认卡片 |
| outline | 次要动作、外链、卡内展开（`action.change_status` `action.log_event` `action.new_cycle` `action.set_current` `action.record_outcome` `action.open_portal`） | 03 头部、07 Agenda |
| ghost | 取消、修正、行内轻动作（`action.cancel` `action.correct` `action.accept`） | 表单、待复核行 |
| danger | 只用于不可逆删除，需二次确认；C-1 未出现 | — |

外链按钮：`outline sm` + 尾部 `external-link` 12px + `target="_blank" rel="noopener"`；文案固定 `action.open_portal`。
展开型按钮（添加申请 / 记事件 / 新建周期 / 改状态）：`aria-expanded` 跟随表单开合；表单打开时按钮文案不变，再次点击 = 收起。
状态：hover（变体内）· focus-visible（ring）· disabled（用色不用透明度）· loading：文案换三点（`typing`），`aria-busy="true"`，`min-w` 锁宽。

## 3. NavItem 侧栏项

结构：`<a class="{base} {state}" aria-current="page"?> icon 18 · <span>文案</span> · [<span class=count>N</span> | <span class=soon>Soon</span>] </a>`

```
base      flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
active    bg-cream-300 text-ink-900                      ← 黄色纸面高亮，不是反白
inactive  text-ink-700 hover:bg-cream-200/60
upcoming  text-ink-400（渲染为 <span aria-disabled="true">，不可点）
soon      ml-auto rounded-full bg-cream-200 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-ink-500      nav.soon
count     ml-auto rounded-full bg-cream-200 px-1.5 text-[10px] font-mono text-ink-500（为 0 不渲染；C-1 无计数）
section   px-3 pt-3.5 pb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500     nav.section.work / inbox / system
```

C-1 状态：看板 · 申请 Pipeline · 信息源 · 设置 可点；对话 · 岗位 · 面试 · 记忆收件箱 · 待复核 · 研究请求 为 upcoming + Soon。信息源与设置共用 12 页，用 `#sources` 区分，两项高亮互斥。
收起态（64px）：只留 icon，`title` = 文案；状态存 `localStorage.jp.nav`。
键名：`nav.dashboard` `nav.chat` `nav.pipeline` `nav.jobs` `nav.interviews` `nav.memory` `nav.review` `nav.research` `nav.sources` `nav.settings` `nav.collapse` `nav.soon`。

## 4. KPI tile

结构：`<div class="card-paper p-4"> eyebrow → 数字 → 副文 </div>`

```
eyebrow  text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500
数字     num text-3xl md:text-4xl leading-tight mt-2 + 语义色
副文     mt-1 text-xs text-ink-500
```

语义色固定，不随数值变：进行中 `text-ink-900` · 本周截止 `text-accent-amber` · 7 天内面试 `text-accent-olive` · 待复核 高亮变体 + `text-ink-900`。
数值全部由数据计算（进行中 = 显示状态属「进行中」组；本周截止 = 下一步为截止 / 回复期限且落在本周；7 天内面试 = 已确认面试；待复核 = 带 `review` 标记的事件数），空周期不渲染 KPI，改为空状态。
不做：箭头涨跌、环形进度、与上周对比。
键名：`dashboard.kpi.active` `…active_sub` `…deadlines` `…deadlines_sub` `…interviews` `…interviews_sub`（含 `{n}`）`…review` `…review_sub`。

## 5. Status chip 应聘状态（12 态）

用途：显示状态 = `userStatus ?? autoStatus ?? unrecorded`。同组同色相、三档明度；颜色全部来自 `tokens.css`，不自造。
结构：`<span class="chip {base} bg-status-{key}-bg text-status-{key}-fg border-status-{key}-border">{{ status.{key} }}</span>`

```
base  inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap
md    px-3 text-[13px] leading-[26px]     （详情页头部）
```

| 组 | key | 文案 | fg light / dark | bg light / dark | border light / dark |
|---|---|---|---|---|---|
| 未开始 · 暖灰 | `unrecorded` | 未记录 | `#635546` / `#CDC2B6` | `transparent` / `transparent` | `#E5DCD4` / `#4C4741` |
| 未开始 · 暖灰 | `considering` | 考虑中 | `#594A3A` / `#D8CBBD` | `#EEE6DE` / `#3D3731` | `#D7CCBF` / `#5C544B` |
| 未开始 · 暖灰 | `preparing` | 准备申请 | `#423527` / `#E9DCCD` | `#D9CBBC` / `#50463B` | `#B7A897` / `#796C5E` |
| 进行中 · 琥珀 | `applied` | 已申请 | `#7F490C` / `#E6BB96` | `#FFF1E5` / `#3A2E23` | `#F7D7BD` / `#584331` |
| 进行中 · 琥珀 | `assessment` | 笔试或课题 | `#763C00` / `#F4C398` | `#FFE2CA` / `#49331F` | `#F0C49F` / `#6D4E31` |
| 进行中 · 琥珀 | `interviewing` | 面试中 | `#5B2800` / `#FFD3A8` | `#F7C294` / `#643D17` | `#D89C67` / `#946233` |
| 成功终态 · 橄榄 | `offer` | Offer | `#3A6433` / `#AECFA9` | `#EDF7EB` / `#2A3329` | `#CEE6CA` / `#3D4D3A` |
| 成功终态 · 橄榄 | `accepted` | 已承诺 | `#2B5A23` / `#B5DAAE` | `#DAEFD6` / `#2C3D29` | `#B8D9B2` / `#455D41` |
| 成功终态 · 橄榄 | `joined` | 已入职 | `#194312` / `#C5EBBE` | `#B3DBAC` / `#33512E` | `#8BB984` / `#547B4D` |
| 结束终态 · 干玫瑰 | `unsuitable` | 不合适 | `#714A60` / `#DAB9CB` | `#FBF0F5` / `#362D32` | `#EED6E3` / `#52424B` |
| 结束终态 · 干玫瑰 | `withdrawn` | 主动放弃 | `#673D56` / `#E7C1D5` | `#F7E1EC` / `#43323B` | `#E4C3D4` / `#654D5A` |
| 结束终态 · 干玫瑰 | `rejected` | 已落选 | `#4E2A3F` / `#F7D1E6` | `#E8C1D6` / `#5A3E4D` | `#C89CB4` / `#876276` |

- `unrecorded` 空心：`bg` 为 `transparent`。
- ghosted 行内：父级 `.ghosted` 使 chip `saturate-[.35] opacity-80`。
- 旁随「已手动覆盖」图标（§9）时 `gap-1.5` 并排。
- 表格分组头：chip + `font-mono text-xs text-ink-500` 计数；空组不渲染，表尾一行列出 `pipeline.empty_rest · 状态名…`。
- 在 `<select>` 里（添加申请的初始状态、改状态目标）只用文字，不用色。
- 键名：`status.unrecorded` … `status.rejected`；组名 `status_group.notstarted / active / success / closed`。

## 6. Source badge 来源徽标（7 种，C-1 只出现 manual）

结构：`<span class="{base}"> <svg class="h-[11px] w-[11px] text-source-{key}"/> <span>{{ source.{key} }}</span> </span>`

```
base  inline-flex items-center gap-1 rounded-full bg-source-bg text-source-fg pl-[5px] pr-[7px] text-[10.5px] font-semibold leading-[18px] whitespace-nowrap
```

| key | 图标 | 图标色 | 键名 | C-1 |
|---|---|---|---|---|
| manual | pencil-line | `text-source-manual` | `source.manual` | 全部记录 |
| gmail | mail | `text-source-gmail` | `source.gmail` | 信息源空态预告 |
| calendar | calendar | `text-source-calendar` | `source.calendar` | 信息源空态预告 |
| linkedin | archive | `text-source-linkedin` | `source.linkedin` | 信息源空态预告 |
| chat | message-circle | `text-source-chat` | `source.chat` | 后续 |
| import | file-input | `text-source-import` | `source.import` | 后续 |
| research | flask-conical | `text-source-research` | `source.research` | 后续 |

并排 `flex flex-wrap gap-1`；表格列最多 3 个，其余 `+N`（`title` 列全）。预告用途加 `opacity-70`。
无障碍：`aria-label` = `source.aria_prefix` + 名称。

## 7. 「待确认」占位

用途：信息缺失的展示占位（无会议链接 / 无时间 / 无工具），**不是状态**；绝不画假链接、假日期。
结构：`<span class="pending {base}">{{ pending.link }}</span>`

```
base  inline-flex items-center gap-1 rounded-lg border border-dashed border-pending-border bg-pending-bg text-pending-fg px-2 text-[11px] font-medium leading-5 whitespace-nowrap
```

变体：`pending.time` · `pending.link` · `pending.tool` · `pending.date` · `pending.generic`。
放置：占据原本放该信息的位置（链接位、时间列）。「即将推出」占位块（§1）复用同一 `.pending` 样式，块级 + 居中。

## 8. 「待复核」标记

用途：置信度低的事件（C-1 中作为状态演示保留在详情页与看板「最近变化」）。
结构：`<span class="{base}"> circle-alert 12 · {{ review.tag }} </span> [接受] [修正…]`

```
base     inline-flex items-center gap-1 rounded-full border border-review-border bg-review-bg text-review-fg px-2 text-[11px] font-semibold leading-5
accept   Button outline xs        action.accept
correct  Button ghost xs          action.correct
done     inline-flex items-center gap-1 text-xs text-pos-500 + check 14   review.confirmed_by_user + " · " + mono 日期
```

前置 `event.confidence` + 两位小数（`text-xs text-ink-500`）。接受 → 直接变 `done`（不出确认卡片）；修正 → 确认卡片（§10）。
键名：`review.tag` `review.confirmed_by_user` `event.confidence` `action.accept` `action.correct`。

## 9. 「已手动覆盖」图标

用途：`userStatus` 与 `autoStatus` 都存在且不同的申请。第一版没有外部源，`autoStatus` 只从用户记录的事件推导（如「申请确认」→ 已申请、「面试邀请」→ 面试中）；没有可推导事件时 `autoStatus` 为空，此时**不显示**图标（没有被覆盖的东西）。
结构：`<span class="{base}" tabindex="0" role="img" aria-label="{tooltip}" title="{tooltip}"> pencil-line 11 </span>`

```
base  inline-grid place-items-center h-[18px] w-[18px] rounded-full bg-override-bg text-override-fg cursor-help
md    h-[22px] w-[22px]（图标 12，详情页头部）
```

tooltip：`override.label` + ` · ` + `status.auto` + `: ` + 自动状态名。详情页头部另有两行小字：`status.user` + 状态 + `status.set_on` + mono 时间 + 来源；`status.auto` + 状态 + `status.derived_from` + 「事件主题」+ mono 时间。
出现位置：Pipeline 行状态列、详情头部、时间线「状态变更（用户）」条目、看板「最近变化」。

## 10. 确认卡片

用途：一切本地数据改动的提议，确认前界面不变。C-1 出现于详情页「改状态」（行内）。后续：对话页 AI 气泡下方、待复核修正 / 批量、记忆收件箱、岗位侧板、研究请求导入。
结构：

```
<section role="group" aria-labelledby="cc-title" class="card-paper px-5 py-[18px] grid grid-cols-[minmax(0,1fr)_auto] gap-4 items-start">
  <div>
    <div class="flex items-center gap-2"> eyebrow {{ confirm.eyebrow }} · SourceBadge（提议来源）</div>
    <p id="cc-title" class="mt-2 flex flex-wrap items-center gap-2.5 text-sm font-semibold text-ink-900">公司 · 岗位 <span class="font-normal text-ink-500">{{ confirm.change_to }}</span> <select class="input h-8 text-[13px]">12 态</select></p>
    <div class="mt-3.5 grid grid-cols-[auto_auto_auto] gap-3.5 items-end justify-start">
      <div> eyebrow {{ confirm.before }} → <StatusChip class="line-through opacity-65"/> </div>
      <span class="text-ink-400 pb-1"> arrow-right 18 </span>
      <div> eyebrow {{ confirm.after }} → <span class="inline-flex rounded-[10px] bg-diff-after-bg px-1.5 py-[3px]"><StatusChip/></span> </div>
    </div>
    <p class="mt-2.5 text-xs text-ink-500">{{ confirm.note_override }} · {{ status.auto }} …</p>
  </div>
  <div class="flex gap-2"> Button primary h-9 {{ action.confirm }} · Button ghost h-9 {{ action.cancel }} </div>
</section>
```

- 变化前 / 后：状态放 chip，文本放 `text-sm`；差异高亮只用 `bg-diff-after-bg`（cream-200），不用红绿。
- 状态：`idle` → `confirmed`：整卡收起，其位置出现 `inline-flex items-center gap-2 rounded-lg border border-pos-500/30 bg-pos-50 text-pos-500 px-3 py-1.5 text-sm` + check 14 + `confirm.done` + ` · ` + mono 日期；同时头部状态 chip 更新、时间线顶部追加「状态变更（用户）」条目并带 §9 图标；`cancelled`：卡片移除，无痕。
- 无障碍：`role="group"` + `aria-labelledby`；确认按钮不自动聚焦；`Esc` = 取消；确认后焦点移到结果条。
- 键名：`confirm.eyebrow` `confirm.before` `confirm.after` `confirm.change_to` `confirm.note_override` `confirm.done` `action.confirm` `action.cancel`。

## 11. Table 表格

用途：Pipeline 表格、设置页周期列表。grid 行 + `role="table" / "row" / "cell" / "columnheader"`。

```
container   overflow-x-auto rounded-2xl border border-cream-200 bg-cream-100
header      grid {cols} gap-3 px-4 py-2.5 bg-cream-200/60 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500
group row   flex items-center gap-2 px-4 py-2 border-t border-cream-200 bg-cream-100   → StatusChip + font-mono text-xs text-ink-500 计数
row         grid {cols} gap-3 px-4 py-3 border-t border-cream-200 bg-cream-50 items-center
cell 主文   text-sm font-semibold text-ink-900 · 次行 text-xs text-ink-500
cell 日期   font-mono text-[13px] text-ink-900 · 次行 text-xs text-ink-500 truncate
cell 数字   num text-xl text-right（周期列表申请数）
open cell   Button icon-only ghost sm，arrow-right，aria-label action.open
```

Pipeline 列：`grid-cols-[minmax(150px,1.1fr)_minmax(150px,1.1fr)_150px_minmax(200px,1.6fr)_168px_104px_40px]`（公司 · 岗位 · 状态 · 最近事件 · 下一步 / 截止 · 来源 · 打开）。
周期列表列：`grid-cols-[minmax(160px,1.4fr)_100px_100px_190px_90px_130px]`（名称 · 类型 · 区域包 · 起止 · 申请数 · 动作）。
ghosted 行：`row ghosted`（`.ghosted, .ghosted * { color: ink-400 }`）+ 公司名下 `italic text-[11px]` + ghost 12 + `ghosted.label · N unit.days`。
键名：`table.company` `table.role` `table.status` `table.latest_event` `table.next` `table.sources` `action.open` `pipeline.empty_rest`。

## 12. EmptyState 空状态

结构：`<div class="card-paper py-14 px-5 flex flex-col items-center text-center gap-2"> icon 28 text-ink-500 → <h3 class="text-lg font-semibold text-ink-900"> → <p class="max-w-md text-sm text-ink-500"> → [Button primary md] </div>`

| 场景 | 图标 | 键名 | CTA |
|---|---|---|---|
| 空周期（看板 / Pipeline / 详情） | file-text | `empty.cycle_title` `empty.cycle_body` | `action.add_application`（详情页改为 `application.switch_to` + 周期名） |
| 筛选无结果 | file-text | `empty.pipeline_title` `empty.pipeline_body` | outline `filter.all`（清除筛选） |
| 信息源未接入 | plug-zap | `empty.sources_title` `empty.sources_body` | 无按钮；下方预告徽标（gmail / calendar / linkedin，`opacity-70`）+ `placeholder.coming_soon` 占位 |

## 13. Input / Select / Textarea

```
label     block mb-1.5 text-xs font-semibold uppercase tracking-[0.04em] text-ink-500
input     w-full rounded-lg border border-ink-200 bg-cream-50 px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-ink-900/20
size md   h-10（页级表单：添加申请、时区与语言）
size sm   h-9 text-[13px]（卡内次级表单：记事件、新建周期）· h-[34px] text-xs（筛选行）
select    input 同款 + appearance-none pr-7 bg-[url(chevron-down)] bg-no-repeat bg-[right_8px_center]
textarea  input 同款 + leading-[1.75] resize-y；备注专用 font-hand-body text-[15px]
mono      日期 / 链接 / 时区输入加 font-mono（time_placeholder = 2026-10-01（水）14:00）
search    flex items-center gap-2 h-[34px] rounded-lg border border-ink-200 bg-cream-50 px-2.5 text-ink-500 + search 16 + 裸 input
error     border-neg-500/50 + 行内 Alert：rounded-lg border border-neg-500/30 bg-neg-50 text-neg-500 px-3 py-1 text-[13px]，role="alert"
success   rounded-lg border border-pos-500/30 bg-pos-50 text-pos-500 px-3 py-1.5 text-[13px]，role="status"（已添加 · 已确认 · 已创建周期）
disabled  bg-cream-100 text-ink-400 cursor-not-allowed
```

表单布局：页级 `grid grid-cols-4 gap-4`（公司 / 岗位各占 2 列，备注占 4 列）；卡内次级 `grid gap-3` 列宽按字段定，动作行 `col-span-full flex items-center gap-2.5`：primary 保存 · ghost 取消 · `text-xs text-ink-500` 说明（`form.source_note`）· 错误 Alert。
校验：必填缺失不提交，显示 `form.required_note`；不做实时校验。
键名：`form.company_placeholder` `form.role_placeholder` `form.initial_status` `form.job_url` `form.url_placeholder` `form.event_type` `form.event_time` `form.event_summary` `form.time_placeholder` `form.summary_placeholder` `form.required_note` `form.source_note` `form.added` `filter.keyword_placeholder` `filter.all` `filter.track` `application.notes_placeholder` `settings.cycle_name_placeholder` `settings.month_placeholder`。

## 14. 周期切换器

用途：顶栏切换求职周期；全站数据按周期归属，当前周期存 `localStorage.jp.cycle`（四页同步）。
结构：

```
trigger  inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg border border-ink-200 bg-cream-50 text-xs font-semibold text-ink-900 hover:bg-cream-100
         calendar 14 · 周期名 · chevron-down 14        aria-haspopup="listbox" aria-expanded
menu     card-paper absolute right-0 top-10 w-[340px] p-1.5 z-20          role="listbox"
row      flex items-center gap-2.5 rounded-lg px-2.5 py-2 hover:bg-cream-100 cursor-pointer      role="option" aria-selected
         text-sm font-semibold 周期名 · text-xs text-ink-500 「类型 · 区域包 · 起止 · N unit.applications」· 当前项尾随 check 14 text-accent-olive
footer   border-t border-cream-200 mt-1 px-2.5 py-2 text-[13px] text-ink-700   {{ cycle.manage }} → 12 设置
```

行为：选择 → 关闭 → 全站按周期过滤；0 条申请的周期 → 各页空状态；详情页显示「这条申请属于 X」+ `application.switch_to`。设置页「设为当前」与此同源。
键盘：↑↓ 移动、Enter 选择、Esc 关闭。
键名：`cycle.manage` `cycle.current` `track.newgrad` `track.intern` `track.mid` `region.jp/us/eu/generic` `unit.applications`。

---

## 15. C-1 已出现、简述

- **Segmented control**（实现：`frontend/src/components/ui/Segmented.tsx`，三处共用）：`inline-flex rounded-full border border-cream-200 bg-cream-100 p-1`（sm：`p-0.5 text-xs`，选项 `h-7 px-2.5`；md：`text-sm`，选项 `h-8 px-3`）；选中 `bg-cream-300 text-ink-900 font-medium`，未选中 `text-ink-500 hover:text-ink-700`；语义用 `role="group"` + 每个按钮 `aria-pressed`（不是 tablist——没有对应的 tabpanel，假 tab 语义会误导读屏）；选项尾随可选 mono 计数。用于语言 中 / 日 / EN、状态组筛选、信息源 · 设置。
- **Toast**（实现：`frontend/src/lib/toast.tsx` + `components/ui/Toast.tsx`；C-1 未出现，2026-09-20 加入）：右下角 `fixed bottom-4 right-4 z-30` 常驻 `aria-live="polite"` 容器（先于内容存在，读屏才会播报）；每条 `card-paper px-3 py-2 text-sm`，成功态 `bg-pos-50 text-pos-500` + 勾图标，可带一个行内链接（如「打开」新建的申请）；3 秒自动消失，最多叠 3 条。只用于成功反馈；错误仍走行内 `Alert`。
- **时间线条目**（03）：左竖线 `border-l-[1.5px] border-dashed border-ink-200`；20px 圆节点 `bg-cream-50 border-[1.5px] border-ink-300` 内 11px 类型图标；行首 mono 时间 · `text-xs font-semibold text-ink-700` 类型 · 来源徽标 · [覆盖图标]；正文 `text-sm`；邮件主题引块 `border-l-2 border-cream-400 bg-cream-100 rounded-r-lg px-2.5 py-1.5`（`event.subject` eyebrow + 原文）；置信度 + 待复核。新在上；条目是可点的卡片（`role="button"`，hover `bg-cream-100`）：点开在下方展开行内编辑表单（类型 / 时间 / 摘要）+ 可见的「删除」按钮（ghost + `text-neg-500`，删除再走确认卡）。自动同步进来的事件同样可被用户修正或删除，改动写审计（D33）。
- **待办条目**（01）：`grid-cols-[18px_minmax(0,1fr)_auto]`；类型 eyebrow `text-accent-amber`（`todo.deadline / interview / followup / portal`）+ 公司 + 岗位；详情 + 来源徽标；右列 mono 时间 + 相对时间；门户待查看行尾 `action.open_portal`（外链）+ `action.record_outcome`（→ 详情页记事件，类型预设「门户结果」）。
- **面试条目**（01 后续面试 / 03 面试子区）：`grid-cols-[150px_minmax(0,1fr)_auto]`；mono 日期 + 时间 `JST`；轮次 pill `rounded-full bg-cream-200 text-ink-700 px-2 text-[11px] font-semibold leading-5`；video / map-pin + 线上 / 线下 + 工具；链接 mono 下划线或 `pending.link`；待排期条目时间位放 `pending.time`，工具位放 `pending.tool`，附邮件原文 + `interview.reply_by` + mono 日期。
- **状态分布条**（01）：手绘 SVG 横向堆叠（四组色 = 各组第 3 档 `bg`，描边 ink-900 1.2，顶点抖动 ±0.9px），虚线基线 `ink-200 "3 4"`；图例行 = 旋转 −5° 小方块 + 组名 + 各态计数 + `.num` 总数。不用饼图。
- **面包屑**（03）：`text-xs text-ink-500 flex items-center gap-1.5`，分隔 `›`，末项 `text-ink-700`。
- **页面标题行**：eyebrow（周期名 · 计数 / 日期 · 周期名）+ `serif text-3xl font-medium tracking-tight`；看板改用 `hand-body text-[40px]` 问候 + 琥珀 ✦。右侧放页面主动作或分段控件。

## 16. 未出现、只列名（后续批次细化）

岗位卡 · 四分徽标（`listing-*` token 已备）· 匹配度「分析判断」标注 · 岗位详情侧板 · 比较表 · 对话页动作卡 / 预览侧板 / 会话列表 · 记忆事实卡 · 待复核行与批量栏 · 健康 pill（`health-*`）· 进度条 · Modal · 步骤条（引导向导）· 月份概览格与手绘圆圈 · Agenda 卡 · 侧栏计数徽标。
