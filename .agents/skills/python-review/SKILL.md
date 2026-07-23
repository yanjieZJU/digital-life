---
name: python-review
description: Perform a findings-first, read-only review of Digital Life Python changes for correctness, architecture boundaries, security, typing, concurrency, persistence safety, and missing tests. Use when reviewing Python diffs, pull requests, refactors, or completed Python implementation work.
---

# Python Review Workflow

Review the requested scope without editing unless the user explicitly asks for fixes.

## Load

1. Read `docs/development/python-coding-standards.md`.
2. Read `docs/development/python-testing-and-review.md`.
3. Read `docs/architecture/current-system.md` for affected ownership boundaries.
4. Inspect the relevant diff, surrounding code, producers or consumers, and tests.

## Review Order

1. Correctness, regressions, data loss, and broken contracts.
2. Security: injection, traversal, unsafe parsing, secrets, authorization, and
   mutable runtime data.
3. Architecture ownership and dependency direction.
4. Error handling, concurrency, async blocking, and multi-instance isolation.
5. Type contracts, mutation, performance, and maintainability.
6. Missing or weak tests and verification evidence.
7. Style only when it materially harms readability or violates project rules.

## Evidence

Run the closest available tests and focused checks when useful:

```bash
python3 -m pytest path/to/relevant_test.py
python3 -m compileall -q path/to/changed_module.py
ruff check path/to/changed.py
mypy path/to/changed_module.py
bandit -r path/to/security_sensitive_package
```

Treat unavailable tools as unverified, not passed. Do not weaken tests or review
unrelated files unless the scope requires it.

## Output

List findings first, ordered `CRITICAL`, `HIGH`, `MEDIUM`, then `LOW`. For each:

```text
[SEVERITY] Short title
File: path/to/file.py:line
Risk: Observable failure or maintenance impact
Fix: Smallest appropriate correction
```

After findings, state open questions and verification gaps. If no issue is found,
say so explicitly and identify residual risk.
