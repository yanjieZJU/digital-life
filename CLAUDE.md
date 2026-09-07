# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Chinese version: [CLAUDE.zh.md](CLAUDE.zh.md). Concise cross-agent entry point: [AGENTS.md](AGENTS.md).

## Project Context

Digital Life is an event-driven autonomous LLM agent runtime. It supports long-lived digital employees or companions by routing human messages, timers, schedules, energy changes, and initiative triggers into the same lifecycle queue.

The important product idea is continuity: an agent should resume goals, memory, and work state across wakeups instead of behaving like a single-turn chatbot. See [README.md](README.md) for the product thesis and [docs/design/digital-life-system-design.md](docs/design/digital-life-system-design.md) for the system design.

## How This Repo Is Organized

- **Standards live in skills, not docs.** Python coding standards and review rules are enforced by the `.claude/skills/python-development` and `.claude/skills/python-review` skills — invoke them (`/python-development`, `/python-review`) when creating/reviewing Python. Spec Kit workflow lives in the `.claude/skills/speckit-*` skills. There is no `docs/development/`, `docs/ai/`, `docs/architecture/`, or `specs/` directory in this repo; do not assume those paths exist.
- `docs/` holds design, operations, philosophy, blog, and showcase material only. `docs/design/digital-life-system-design.md` is the closest thing to an architecture reference; `docs/operations/instances.md` covers instance lifecycle.
- Root files (`README.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) are routers, not deep manuals. Prefer concise files over one large context file.

## Current Architecture

Layered runtime; treat each top-level package as a separate layer:

- `gateway/` starts the runtime and supervises digital-life instances. `main.py` runs in **master** mode (HTTP server + `InstanceSupervisor` managing child processes; no Feishu WS, no cron) or **instance** mode (`--instance <uuid>`: runs that instance's Feishu adapter + cron only; no HTTP server).
- `interfaces/` owns external surfaces: CLI (`cli/cli.py`), Feishu ingress, tool registry (`tools/registry.py`), skills, and the Vue employee console (`web/employee-console`).
- `application/` owns normalized message workflows, console API routes, deterministic ingress checks, event services, and use-case coordination.
- `domain/` owns business capabilities: `lifecycle`, `memory`, `orchestration`, `execution`, `feedback`, `identity`, `project`, `todos`, `vital`, `conversations`, `messages`, `contacts`, `social_context`, `flow_event_log`, `capability`, `runtime`, `persistence`, `core`.
- `infrastructure/` owns technical adapters and primitives: AI runtime (`ai/`), HTTP server, SQLite persistence, scheduler, config, filesystem, observability, queue, budget, tool selection, bootstrap.
- `apps/{id}/` stores concrete instance configuration, persona files, memories, and runtime data. `apps/instances.yaml` is the instance registry.
- `shared/` holds cross-cutting `capabilities`, `skills`, `tools`.

## Hard Rules

- Treat `application/`, `domain/`, `infrastructure/`, and `interfaces/` as separate layers. Keep domain code free of HTTP, CLI, UI, and direct SQLite details unless an existing boundary explicitly allows it.
- `domain/orchestration` (incl. `planning/`) plans tasks and capability gaps. It must not execute tools or call runtime engines directly.
- `domain/execution/semantics` defines execution meaning and runtime ports. Runtime implementations live below the domain boundary (in `infrastructure/`).
- Prompt and memory context construction should stay auditable in `domain/memory`/context and `domain/lifecycle` code, not hidden in adapters or UI handlers.
- Keep tool names in prompts aligned with registered tools in `interfaces/tools/registry.py`.
- When switching or spawning instance work, set both instance context systems where relevant: infrastructure instance ID and lifecycle event channel.
- Do not edit generated or mutable instance memory files under `apps/{id}/` unless the task explicitly asks for it.
- Do not add compatibility shims for internal code unless the user explicitly asks for backwards compatibility or an external boundary requires it.
- For Python implementation or review, use the `python-development` / `python-review` skills rather than improvising standards.

## Spec Kit

Spec Kit (`speckit-*` skills) governs feature work. Before implementation, declare `Spec Kit Mode: full | lightweight | none` and a reason. `full` and `lightweight` authorize the official numbered Spec Kit branch; ordinary tasks do not create branches unless explicitly requested. Load only the active feature's artifacts. `domain/orchestration/planning/` is separate runtime product code, not Spec Kit.

## Commands

Runtime management uses the `digital-life` CLI (entry point `interfaces.cli/cli.py:main`, installed in `venv/`). Use the venv Python (`venv/bin/python`); the project requires Python ≥ 3.11.

```bash
digital-life init --display-name "Zero"   # bootstrap a new instance under apps/{uuid}/
digital-life start                          # start the runtime (master + supervised instances)
digital-life restart
digital-life status
digital-life logs -f
digital-life stop

python3 -m pytest                           # run the full suite (testpaths = ["tests"])
python3 -m pytest tests/test_orchestration_boundary.py   # one test file
python3 -m pytest tests/test_event_flow_contract.py -k name   # one test by name

npm --prefix interfaces/web/employee-console run dev   # Vue employee console dev server
```

Do not use legacy Hermes commands for runtime management.

## Testing Expectations

- Run targeted tests for the modules you touched.
- For architecture boundary changes, run the relevant boundary tests under `tests/test_*boundary*.py` (e.g. `test_orchestration_boundary.py`).
- For event or console display changes, run event-flow and employee-console tests.
- If tests cannot be run, state that clearly in the final response.
