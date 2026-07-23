# CLAUDE.zh.md

供 Claude Code 和其他编码 Agent 在本仓库工作时使用。

英文版见 [CLAUDE.md](CLAUDE.md)。

## 阅读顺序

1. 先读本文件。
2. 所有实施类任务必须遵循 [docs/development/development-workflow.zh.md](docs/development/development-workflow.zh.md)。
3. 应用 [docs/development/spec-kit-policy.zh.md](docs/development/spec-kit-policy.zh.md)，并在实施前声明模式。
4. 通过 [docs/ai/context-loading-guide.zh.md](docs/ai/context-loading-guide.zh.md) 判断本次任务还需要加载哪些文档。
5. 涉及架构或模块职责时，读 [docs/architecture/current-system.md](docs/architecture/current-system.md)。
6. 涉及命令、测试、踩坑时，读 [docs/development/commands-and-testing.md](docs/development/commands-and-testing.md) 和 [docs/development/lessons-learned.md](docs/development/lessons-learned.md)。
7. 涉及 Python 编写、修改或审查时，读 [docs/development/python-coding-standards.zh.md](docs/development/python-coding-standards.zh.md) 和 [docs/development/python-testing-and-review.zh.md](docs/development/python-testing-and-review.zh.md)。
8. 涉及实例创建、飞书路由或运维时，读 [docs/operations/instances.md](docs/operations/instances.md)。

## 项目定位

Digital Life 是事件驱动的自主 LLM Agent 运行时。它把人类消息、定时器、作息、精力变化、主动探索等都放入同一套生命周期事件队列，让数字员工或虚拟伴侣能跨 session、跨天延续目标、记忆和工作状态。

核心不是“聊天机器人”，而是“逻辑上不中断的自主主体脉络”。

## 当前架构

- `gateway/`：运行入口和多实例 supervisor。
- `interfaces/`：外部交互面，包括 CLI、飞书入口、工具注册、技能和 Vue 员工控制台。
- `application/`：用例编排、消息规范化、控制台 API、确定性入口检查和事件服务。
- `domain/`：领域能力，包括生命周期、记忆、编排、执行语义、反馈、身份、项目、精力仿真和流转日志。
- `infrastructure/`：技术设施，包括 AI runtime、HTTP、SQLite 持久化、调度、配置、文件系统、观测和工具选择。
- `apps/{id}/`：具体数字生命实例的人设、配置、记忆和运行数据。

## 硬约束

- 所有实施类任务必须从接单、调研、实现到验证和交付完整遵循 `docs/development/development-workflow.zh.md`。
- Python 改动必须遵循 `docs/development/python-coding-standards.zh.md` 和 `docs/development/python-testing-and-review.zh.md`，只对变更代码增量应用。
- 实施前声明 `Spec Kit Mode: full | lightweight | none` 及原因，只加载当前 feature 产物。`full` 和 `lightweight` 允许创建正式编号的 Spec Kit 功能分支；普通任务除非用户明确要求，否则不创建分支。
- 使用 `digital-life start/restart/stop/status/logs` 管理运行时。不要用旧 Hermes 命令启动本项目。
- 尊重 `application/`、`domain/`、`infrastructure/`、`interfaces/` 分层。领域层不要直接拥有 HTTP、CLI、UI、SQLite 细节，除非现有边界明确允许。
- `domain/orchestration` 只做任务规划和能力缺口判断，不执行工具，不直接调用 runtime engine。
- `domain/execution/semantics` 定义执行语义和端口；runtime 实现放在领域层下面。
- Prompt 和记忆上下文组装必须可审计，不要藏在适配器或 UI handler 里。
- prompt 中出现的工具名必须和 `interfaces/tools/registry.py` 中的实际注册工具一致。
- 切换或新开实例上下文时，相关路径要同时设置 infrastructure 实例 ID 和 lifecycle event channel。
- 除非任务明确要求，不要编辑实例运行期记忆文件。
- 不要为内部代码随手加兼容 shim；只有用户明确要求兼容或外部边界需要时才保留旧路径。

## 常用命令

```bash
digital-life start
digital-life restart
digital-life status
digital-life logs -f
digital-life stop
python3 -m pytest
python3 -m pytest tests/test_orchestration_boundary.py
npm --prefix interfaces/web/employee-console run dev
```

更多命令见 [docs/development/commands-and-testing.md](docs/development/commands-and-testing.md)。

## 测试要求

- 修改哪个模块，就优先运行对应的定向测试。
- 修改架构边界时，运行 `tests/test_*boundary*.py` 中相关测试。
- 修改事件流或控制台展示时，运行 event-flow 和 employee-console 相关测试。
- 如果无法运行测试，最终回复里要明确说明。

## 文档规则

- 根目录文件只做路由，不堆长篇说明。
- 长期有效的项目事实放 `docs/architecture/`，使用和开发命令放 `docs/development/` 或 `docs/operations/`，产品背景放 `docs/product/`，迁移历史放 `docs/migration/`，历史分析或报告放 `docs/analysis/`。
- 优先写命名清晰的短文件，而不是一个巨大的上下文文件。
- 旧迁移文档和源码事实冲突时，以源码和 [docs/architecture/current-system.md](docs/architecture/current-system.md) 为准。
- 不保留空文档分类或占位 README；文档生命周期分类以 [docs/README.md](docs/README.md) 为准。
- 仓库 Spec Kit 管理开发流程；`domain/orchestration/planning/` 是独立的运行时业务代码。
