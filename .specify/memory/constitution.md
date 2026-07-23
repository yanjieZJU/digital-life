<!--
Sync Impact Report
- Version: 1.0.1 -> 1.2.0
- Added principle: IX. Python Quality Is Incremental and Risk-Based
- Modified principle: VI. Documentation Is Part of the Change
- Added sections: none
- Removed sections: none
- Templates updated:
  - .specify/templates/overrides/plan-template.md
  - .specify/templates/overrides/tasks-template.md
  - .specify/templates/overrides/checklist-template.md
- Runtime guidance updated:
  - AGENTS.md and AGENTS.zh.md
  - CLAUDE.md and CLAUDE.zh.md
  - GEMINI.md
  - docs/development/development-workflow.md
  - docs/development/development-workflow.zh.md
  - docs/development/commands-and-testing.md
  - docs/development/python-coding-standards.md
  - docs/development/python-coding-standards.zh.md
  - docs/development/python-testing-and-review.md
  - docs/development/python-testing-and-review.zh.md
- Documentation routing updated:
  - docs/README.md
  - docs/ai/context-loading-guide.md
  - docs/ai/context-loading-guide.zh.md
  - docs category README files
- Deferred items: none
-->
# Digital Life Constitution

## Core Principles

### I. Layer Ownership and Dependency Direction
Changes MUST preserve the responsibilities and dependency direction documented in
`docs/architecture/current-system.md`. Business rules belong in `domain/`, use-case
coordination in `application/`, external adapters in `interfaces/`, and technical
implementations in `infrastructure/`. Domain code MUST NOT depend on HTTP, CLI, UI,
or direct persistence details unless an existing explicit port permits it.

### II. Orchestration Plans; Execution Runs Elsewhere
`domain/orchestration` MUST plan tasks, capability gaps, and assignments without
executing tools or calling runtime engines directly. Execution meaning and ports
belong in `domain/execution/semantics`; concrete execution belongs below the domain
boundary.

### III. Contracts Move Together
Any change to an API, event, prompt, registered tool, skill, configuration, or
persistence shape MUST identify all producers and consumers and update them in the
same change. Prompt tool names MUST match the registry. Multi-instance flows MUST
set every required instance and event context.

### IV. Mutable Runtime Data Is Protected
Agents MUST NOT edit generated or mutable instance data under `apps/{id}/data/`,
runtime state, credentials, or local configuration unless the task explicitly
requires it. Migrations MUST define compatibility, rollback or recovery behavior,
and verification before changing persisted data.

### V. Verification Matches Risk
Every behavioral change MUST include tests or an explicit verification method.
Cross-layer, architecture-boundary, event, persistence, and contract changes MUST
run the relevant boundary or contract checks in addition to focused tests. A failed
check MUST be investigated; tests MUST NOT be weakened to hide a regression.

### VI. Documentation Is Part of the Change
Changes to behavior, architecture, contracts, commands, configuration, operations,
or known limitations MUST update the corresponding durable document in `docs/`.
Root AI guidance files MUST remain concise routers. Feature-specific Spec Kit
artifacts MUST NOT become the sole source of durable project rules. Current facts
MUST live in `docs/architecture/`, normative workflow in `docs/development/`,
operations in `docs/operations/`, and historical material in `docs/migration/` or
`docs/analysis/`. Empty categories, placeholder READMEs, and `.gitkeep` files MUST
NOT be retained without real content. Every non-index document MUST be discoverable
from its nearest category `README.md` with a clear load trigger. Major task-route
changes MUST update `docs/README.md` and the context-loading guides.

### VII. Compatibility Is Intentional
Internal compatibility shims, duplicate paths, and speculative abstractions MUST
NOT be added without an explicit external compatibility requirement or approved
migration need. The smallest coherent change that satisfies the requirement is the
default.

### VIII. Preserve Existing Work and Finish Completely
Agents MUST preserve unrelated user changes and MUST NOT use destructive Git
operations without explicit approval. Delivery is complete only when the requested
outcome exists, verification has run or blockers are disclosed, affected docs are
synchronized, and remaining risks are stated.

### IX. Python Quality Is Incremental and Risk-Based
New or changed Python code MUST follow
`docs/development/python-coding-standards.md` and
`docs/development/python-testing-and-review.md`. Public changed interfaces MUST
have useful types; external data MUST be validated at its owning boundary; errors,
SQL, paths, secrets, async work, concurrency, and mutable runtime data MUST receive
handling proportional to their risk. Agents MUST run focused tests and available
checks for changed code, but MUST NOT mass-format or refactor unrelated legacy
Python merely to satisfy a new rule.

## Repository Constraints

- The current source layout is `gateway/`, `interfaces/`, `application/`, `domain/`,
  and `infrastructure/`; plans MUST use these paths rather than historical layouts.
- Runtime management uses `digital-life start/restart/stop/status/logs`; legacy
  Hermes gateway commands are not valid for this repository.
- Repository development Spec Kit infrastructure lives in `.specify/`, governance
  lives in `docs/development/`, and feature workspaces live in `specs/`.
- Runtime task decomposition in `domain/orchestration/planning/` is product code,
  not the repository development workflow, and MUST be treated separately.

## Development and Delivery Gates

- Every implementation task MUST follow `docs/development/development-workflow.md`
  and declare `Spec Kit Mode` with a reason before implementation.
- `full` and `lightweight` Spec Kit work MAY create the official numbered feature
  branch. Ordinary or `none` work MUST NOT create branches unless explicitly asked.
- Only the Spec Kit feature-branch hook MAY run automatically. Repository
  initialization, staging, commits, pushes, and destructive Git operations require
  explicit user approval.
- Plans MUST perform constitution, architecture-boundary, contract-impact,
  multi-instance, runtime-data, compatibility, verification, and documentation
  checks before implementation.
- Python plans and reviews MUST load the project Python standards, select tests by
  risk, and record unavailable static checks as unverified rather than passed.
- Feature artifacts are tracked while active. After delivery, retain only artifacts
  with durable contract, decision, or maintenance value; remove temporary artifacts.

## Governance

This constitution supersedes conflicting repository development practices.
Amendments MUST explain the reason, update dependent templates and guidance, and
record a semantic version change. MAJOR versions remove or redefine principles,
MINOR versions add or materially expand principles, and PATCH versions clarify
wording without changing obligations. Reviews and Spec Kit plans MUST verify
compliance; exceptions MUST be documented in the plan's complexity or risk record.

**Version**: 1.2.0 | **Ratified**: 2026-06-04 | **Last Amended**: 2026-06-04
