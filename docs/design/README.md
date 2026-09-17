# 设计工作流

Mita JobPilot 沿用姊妹项目 MITA Finance 的设计语言（决策 D22）。UI 设计由 Claude Design 按本目录的 prompt 产出，再由开发侧蒸馏为实现依据。

| 文件 / 目录 | 用途 |
|---|---|
| [claude-design-prompt.md](claude-design-prompt.md) | 粘贴给 Claude Design 的完整 prompt，自带 MITA Finance 的全部 token 与组件语法 |
| `output/`（尚未创建） | Claude Design 每批交付物原样落地：`tokens.css`、`ia-and-flows.md`、`NN-*.html`、`components.md`、`i18n.json`、`open-questions.md` |
| `../DESIGN.md`（Phase 2 前置交付物，尚未写） | 从 `output/` 蒸馏出的信息架构、用户流程、组件规范与 design tokens，前端实现只看这一份 |

## 流程

1. 把 prompt 粘进 Claude Design，可附 MITA Finance 的 `design/screenshots/dashboard-a.png`。
2. 第一批拿到 `tokens.css` + `ia-and-flows.md`，人工评审后再让它出页面原型。
3. 每批产出放进 `output/`，提交到 git（HTML 原型体积小，可入库）。
4. 全部到齐后写 `docs/DESIGN.md`，并把 `tokens.css` 落到 `frontend/src/index.css`。

## token 的唯一来源

MITA Finance 仓库 `frontend/src/index.css` 的 `@theme` 块。prompt 里的值逐字取自该文件；若 MITA Finance 更新 token，先改那里，再同步这里。
