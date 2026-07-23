---
name: python-review
description: Perform a findings-first, read-only review of Digital Life Python changes for correctness, architecture boundaries, security, typing, concurrency, persistence safety, and missing tests. Use when reviewing Python diffs, pull requests, refactors, or completed Python implementation work.
---

# Python Review Workflow

Review without editing unless the user explicitly asks for fixes.

1. Read `docs/development/python-coding-standards.md`.
2. Read `docs/development/python-testing-and-review.md`.
3. Inspect the relevant diff, surrounding code, contracts, and tests.
4. Review correctness and security before architecture, error handling,
   concurrency, types, maintainability, tests, and style.
5. Run relevant available focused tests and checks.
6. Treat unavailable tools as unverified, not passed.
7. List findings first, ordered by severity, with file and line references.
8. If no issue is found, state that and identify remaining verification gaps.
