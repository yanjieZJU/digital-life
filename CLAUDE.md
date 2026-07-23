# CLAUDE.md

Guidance for Claude Code and other coding agents working in this repository.

For the Chinese version, read [CLAUDE.zh.md](CLAUDE.zh.md).

## Read Order

1. Start with this file.
2. For every implementation task, follow [docs/development/development-workflow.md](docs/development/development-workflow.md).
3. Apply [docs/development/spec-kit-policy.md](docs/development/spec-kit-policy.md) and declare the mode before implementation.
4. Load [docs/ai/context-loading-guide.md](docs/ai/context-loading-guide.md) to choose the minimum extra context for the task.
5. For architecture or module work, read [docs/architecture/current-system.md](docs/architecture/current-system.md).
6. For commands, tests, and known pitfalls, read [docs/development/commands-and-testing.md](docs/development/commands-and-testing.md) and [docs/development/lessons-learned.md](docs/development/lessons-learned.md).
7. For Python implementation or review, read [docs/development/python-coding-standards.md](docs/development/python-coding-standards.md) and [docs/development/python-testing-and-review.md](docs/development/python-testing-and-review.md).
8. For instance operations, read [docs/operations/instances.md](docs/operations/instances.md).

## Project Context

Digital Life is an event-driven autonomous LLM agent runtime. It supports long-lived digital employees or companions by routing human messages, timers, schedules, energy changes, and initiative triggers into the same lifecycle queue.

The important product idea is continuity: an agent should resume goals, memory, and work state across wakeups instead of behaving like a single-turn chatbot.

## Current Architecture

- `gateway/` starts the runtime and supervises digital-life instances.
- `interfaces/` owns external surfaces: CLI, Feishu ingress, tool registry, skills, and the Vue employee console.
- `application/` owns normalized message workflows, console API routes, deterministic ingress checks, event services, and use-case coordination.
- `domain/` owns business capabilities: lifecycle, memory, orchestration, execution semantics, feedback, identity, project state, vital simulation, and flow event logs.
- `infrastructure/` owns technical adapters and primitives: AI runtime, HTTP server, SQLite persistence, scheduler, config, filesystem, observability, and tool selection.
- `apps/{id}/` stores concrete instance configuration, persona files, memories, and runtime data.

## Hard Rules

- All implementation tasks must follow `docs/development/development-workflow.md` from intake through verification and delivery.
- Python changes must follow `docs/development/python-coding-standards.md` and `docs/development/python-testing-and-review.md`; apply them incrementally to changed code.
- Before implementation, declare `Spec Kit Mode: full | lightweight | none` and a reason. Load only the active feature artifacts. `full` and `lightweight` authorize the official numbered Spec Kit branch; ordinary tasks do not create branches unless explicitly requested.
- Use `digital-life start/restart/stop/status/logs` for runtime management. Do not use legacy Hermes commands for this project.
- Treat `application/`, `domain/`, `infrastructure/`, and `interfaces/` as separate layers. Keep domain code free of HTTP, CLI, UI, and direct SQLite details unless an existing boundary explicitly allows it.
- `domain/orchestration` plans tasks and capability gaps. It must not execute tools or call runtime engines directly.
- `domain/execution/semantics` defines execution meaning and runtime ports. Runtime implementations live below the domain boundary.
- Prompt and memory context construction should stay auditable in memory/context and lifecycle code, not hidden in adapters or UI handlers.
- Keep tool names in prompts aligned with registered tools in `interfaces/tools/registry.py`.
- When switching or spawning instance work, set both instance context systems where relevant: infrastructure instance ID and lifecycle event channel.
- Do not edit generated or mutable instance memory files unless the task explicitly asks for it.
- Do not add compatibility shims for internal code unless the user explicitly asks for backwards compatibility or an external boundary requires it.

## Commands

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

See [docs/development/commands-and-testing.md](docs/development/commands-and-testing.md) for more.

## Testing Expectations

- Run targeted tests for the modules you touched.
- For architecture boundary changes, run the relevant boundary tests under `tests/test_*boundary*.py`.
- For event or console display changes, run event-flow and employee-console tests.
- If tests cannot be run, state that clearly in the final response.

## Documentation Rules

- Root files are routers, not deep manuals.
- Put durable project facts in `docs/architecture/`, usage in `docs/development/` or `docs/operations/`, product background in `docs/product/`, migration history in `docs/migration/`, and historical analysis or reports in `docs/analysis/`.
- Prefer concise files with clear names over one very large context file.
- When facts differ between old migration docs and source code, source code and `docs/architecture/current-system.md` win.
- Do not keep empty documentation categories or placeholder README files. Use `docs/README.md` for lifecycle classification.
- Repository Spec Kit governs development; `domain/orchestration/planning/` is separate runtime product code.

<!-- SPECKIT START -->
For active `full` or `lightweight` Spec Kit work, read the current feature plan
after applying the Spec Kit gate. Do not load feature plans for ordinary tasks.
<!-- SPECKIT END -->
