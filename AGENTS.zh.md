# 仓库 Agent 指南

这是 Digital Life 的简短 AI Agent 入口。

英文版见 [AGENTS.md](AGENTS.md)。详细 Claude 指南见 [CLAUDE.zh.md](CLAUDE.zh.md)。

## 快速背景

Digital Life 是事件驱动的自主 LLM Agent 运行时。系统把人类消息、定时器、作息、精力变化和主动探索都转为生命周期事件，让 Agent 能跨唤醒持续推进任务。

## 渐进式加载

- 先读 [CLAUDE.zh.md](CLAUDE.zh.md)，掌握硬约束和命令。
- 所有实施类任务遵循 [docs/development/development-workflow.zh.md](docs/development/development-workflow.zh.md)。
- 实施前应用 [docs/development/spec-kit-policy.zh.md](docs/development/spec-kit-policy.zh.md)。
- 用 [docs/ai/context-loading-guide.zh.md](docs/ai/context-loading-guide.zh.md) 判断本次任务还要读哪些文档。
- 用 [docs/architecture/current-system.md](docs/architecture/current-system.md) 理解当前模块职责。
- 用 [docs/development/commands-and-testing.md](docs/development/commands-and-testing.md) 查命令和测试。
- 修改 Python 时加载 [docs/development/python-coding-standards.zh.md](docs/development/python-coding-standards.zh.md) 和 [docs/development/python-testing-and-review.zh.md](docs/development/python-testing-and-review.zh.md)。
- 用 [docs/operations/instances.md](docs/operations/instances.md) 查实例运维。

## 实施前声明

声明 `Spec Kit Mode: full | lightweight | none` 及原因。只有当前 `full` 或
`lightweight` 任务才加载对应 `specs/{feature}/`；这两种模式允许创建正式编号的
Spec Kit 功能分支，普通任务除非用户明确要求，否则不创建分支。

Python 编写或重构使用项目级 `python-development` 工作流；Python 审查使用
`python-review`，并按 findings-first 方式输出。

## 架构速览

- `gateway/`：运行入口和实例 supervisor。
- `interfaces/`：CLI、飞书入口、工具、技能、员工控制台前端。
- `application/`：用例、规范化消息工作流、控制台 API、入口检查、事件服务。
- `domain/`：生命周期、记忆、编排、执行语义、反馈、身份、项目、精力仿真、流转日志。
- `infrastructure/`：AI runtime、HTTP、持久化、调度、配置、文件系统、观测。
- `apps/{id}/`：实例人设、配置、记忆和运行数据。

## 常用命令

```bash
digital-life start
digital-life restart
digital-life status
digital-life logs -f
digital-life stop
python3 -m pytest
```

不要用旧 Hermes gateway 命令管理本项目。
