---
name: python-development
description: Implement, refactor, or fix Python code in Digital Life using the repository's Python 3.11 coding standards, layer boundaries, security rules, and risk-based pytest workflow. Use whenever a task creates or changes Python production code or Python tests.
---

# Python Development Workflow

Use the project-owned rules below.

## Load

1. Read `docs/development/python-coding-standards.md`.
2. Read `docs/development/python-testing-and-review.md`.
3. Read `docs/architecture/current-system.md` when ownership or dependencies matter.
4. Read only the target modules, their callers or consumers, and related tests.

## Implement

1. Confirm the requested behavior, affected contracts, and owning layer.
2. Preserve unrelated work and mutable `apps/{id}/data/`.
3. Add or update a focused behavior or regression test when behavior changes.
4. Implement the smallest coherent change using existing project patterns.
5. Type new or changed public interfaces and validate external data at boundaries.
6. Synchronize affected contract consumers and durable documentation.
7. Run focused tests first, then expand according to risk.
8. Review the changed Python against the security and completion checklists.

## Mandatory Rules

- Keep domain rules free of HTTP, CLI, UI, and concrete persistence details.
- Use parameterized SQL, safe path handling, safe parsing, and existing secret paths.
- Do not silently swallow exceptions. Broad catches require a deliberate boundary
  and defined fallback.
- Avoid hidden shared mutation; use immutable domain contracts where appropriate.
- Do not block async paths or leak instance context.
- Do not mass-format or refactor unrelated legacy Python.

## Verification

Run relevant available commands:

```bash
python3 -m pytest path/to/relevant_test.py
python3 -m compileall -q path/to/changed_module.py
ruff check path/to/changed.py
ruff format --check path/to/changed.py
```

Do not claim optional tools passed when they are unavailable. Report focused tests,
broader checks, documentation updates, and remaining risks.
