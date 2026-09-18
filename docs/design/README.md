# 设计工作流

Mita JobPilot 沿用姊妹项目 MITA Finance 的设计语言（决策 D22）。UI 设计由 Claude Design 按本目录的 prompt 产出，前端直接以产出为实现依据。

| 文件 / 目录 | 用途 |
|---|---|
| [claude-design-prompt.md](claude-design-prompt.md) | 第一轮 prompt：完整愿景、MITA Finance 全部 token 与组件语法、13 + 2 页清单、交付物 A 到 F |
| [claude-design-prompt-batch2.md](claude-design-prompt-batch2.md) | 第二轮 prompt：基于 A / B，先出第一步四页 HTML（01 / 02 / 03 / 12），再出 D 组件规范与 E 三语字典 |
| `v1/` | Claude Design 交付物原样落地。已到：`tokens.css`（A）、`ia-and-flows.md`（B）。待到：`NN-*.html`（C）、`components.md`（D）、`i18n.json`（E）、`open-questions.md`（F） |

## 流程

1. 把 prompt 粘进 Claude Design（第二轮在同一对话里继续）。
2. 每批产出放进 `v1/`，提交到 git（HTML 原型体积小，可入库）。
3. 前端实现直接读 `v1/`：`tokens.css` 拷贝为 `frontend/src/tokens.css`；`ia-and-flows.md` 是导航树与页面结构的依据；`components.md` 到齐后对照校正组件 class；`i18n.json` 到齐后合并进 `frontend/src/i18n/`。
4. 不再单独维护 `docs/DESIGN.md`。

## token 的唯一来源

`docs/design/v1/tokens.css`。它的 MITA Finance 部分逐字取自 MITA Finance 仓库 `frontend/src/index.css` 的 `@theme` 块；JobPilot 新增部分（12 态状态色、四分徽标、来源徽标、健康五态等）由 Claude Design 交付。改 token 先改这里，再同步到 `frontend/src/tokens.css`。
