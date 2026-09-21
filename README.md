# Mita JobPilot

本地优先、只读接入外部信息源、带 AI 对话与记忆的个人求职工作台。
A local-first, read-only-integrated personal job-hunting workbench with an AI chat and memory layer.

> 状态（2026-09-21）：骨架、追踪域 schema、Google 只读连接器已完成；**第 1 步「基础网页看板（手动录入）」已验收通过**（两轮 UAT，含编辑 / 删除、事件卡片、看板待办与已过期组）。下一步：第 2a 步 Gmail 接入（分支 `step2a-gmail`）。下一步接 Gmail。顺序见 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 它做什么

- 从 Gmail / Google Calendar / LinkedIn 官方导出等**只读**信息源，自动推导每一个选考流程的状态、截止日期与面试日程。
- 用 Claude 或 GPT 对话查询进度、评估岗位、操作系统；模型只能「提议」，用户「确认」后才写入。
- 记忆系统记住你的画像、偏好、申请结果，并据此搜索和排序新岗位。
- 首个场景是日本 2027 年卒新卒就活，但求职周期、地区规则都可配置；任何人都能自托管一套。

## 硬约束

**对外部服务只读。** 不发送、不回复、不申请、不改标签、不写日历。这一点由凭据范围、传输层、代码面、工具注册表和测试共同保证。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | 定位、需求全貌、硬约束、日本求职领域基线、调研结论、现状、决策、待决问题 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构原则、技术选型、只读保证、数据模型、接入策略、记忆、对话、部署 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 步 0 到 7 的范围、状态与退出标准 |
| [docs/design/](docs/design/README.md) | Claude Design 的 prompt 与交付物（`v1/`：tokens、信息架构与流程） |
| [docs/research/](docs/research/README.md) | 调研附录（集成可行性、架构提案与评审、部署、日本领域） |
| [docs/ref/gpt_design.txt](docs/ref/gpt_design.txt) | 参考原型的产品需求基线 |

## 开发环境

- Python 3.12 + [uv](https://docs.astral.sh/uv/)，Node 22 + npm（前端）。
- Windows 11 是首个开发与运行平台；架构按 Linux / 容器可迁移设计。

```bash
uv sync                                   # 安装运行与开发依赖（uv 0.10.x）
uv run jobpilot --help
uv run jobpilot doctor                    # 环境、schema、时区、密钥后端、区域包
cd frontend && npm install && npm run build && cd ..   # 构建网页（产物 frontend/dist 不入库）
uv run jobpilot serve                     # http://127.0.0.1:8765 ：看板 / 申请 / 详情 / 设置
```

前端开发时另开 `cd frontend && npm run dev`（5173 端口，`/api` 代理到 8765）。

配置通过 `JOBPILOT_*` 环境变量或 `.env` 文件提供，全部键见 `env.example`。数据目录默认在平台用户数据目录（Windows 为 `%LOCALAPPDATA%\JobPilot`），可用 `JOBPILOT_DATA_DIR` 覆盖。

提交前检查（pre-commit 会自动跑同一组）：

```bash
uv run pytest
uv run ruff check --fix . && uv run ruff format .
uv run pyright
uv run python scripts/check_pii.py
uv run pre-commit install                 # 一次性；本机也可用 prek 跑同一份配置
cd frontend && npm run lint && npm run build
```
