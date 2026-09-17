# Mita JobPilot

本地优先、只读接入外部信息源、带 AI 对话与记忆的个人求职工作台。
A local-first, read-only-integrated personal job-hunting workbench with an AI chat and memory layer.

> 状态：需求与架构定稿中，尚无代码（2026-09-16）。

## 它做什么

- 从 Gmail / Google Calendar / LinkedIn 官方导出等**只读**信息源，自动推导每一个选考流程的状态、截止日期与面试日程。
- 用 Claude 或 GPT 对话（含语音）查询进度、评估岗位、操作系统；模型只能「提议」，用户「确认」后才写入。
- 记忆系统记住你的画像、偏好、申请结果，并据此搜索和排序新岗位。
- 首个场景是日本 2027 年卒新卒就活，但求职周期、地区规则都可配置；任何人都能自托管一套。

## 硬约束

**对外部服务只读。** 不发送、不回复、不申请、不改标签、不写日历。这一点由凭据范围、传输层、代码面、工具注册表和测试共同保证。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | 定位、需求全貌、硬约束、日本求职领域基线、调研结论、现状、决策、待决问题 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构原则、技术选型、只读保证、数据模型、接入策略、记忆、对话与语音、部署 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phase 0 到 7 的范围、退出标准与第一周计划 |
| [docs/research/](docs/research/README.md) | 调研附录（集成可行性、架构提案与评审、部署、日本领域） |
| [docs/ref/gpt_design.txt](docs/ref/gpt_design.txt) | 参考原型的产品需求基线 |

## 开发环境

- Python 3.12 + [uv](https://docs.astral.sh/uv/)，Node 22（前端阶段）。
- Windows 11 是首个开发与运行平台；架构按 Linux / 容器可迁移设计。

```bash
uv sync
uv run jobpilot --help   # Phase 0 之后可用
```
