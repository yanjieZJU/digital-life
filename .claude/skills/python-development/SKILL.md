---
name: python-development
description: Implement, refactor, or fix Python code in Digital Life using the repository's Python 3.11 coding standards, layer boundaries, security rules, and risk-based pytest workflow. Use whenever a task creates or changes Python production code or Python tests.
---

# Python Development Workflow

Use the project-owned rules below.

1. Read `docs/development/python-coding-standards.md`.
2. Read `docs/development/python-testing-and-review.md`.
3. Inspect the owning module, callers or consumers, contracts, and related tests.
4. Preserve unrelated work and mutable `apps/{id}/data/`.
5. Add or update a focused behavior or regression test when behavior changes.
6. Implement the smallest coherent change using existing project patterns.
7. Type changed public interfaces and validate external data at boundaries.
8. Synchronize affected contracts and durable documentation.
9. Run focused tests first, then expand according to risk.
10. Review security, error handling, concurrency, persistence, and instance safety.

Do not mass-format or refactor unrelated Python. Do not claim optional tools passed
when they are unavailable.
