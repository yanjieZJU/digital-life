# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `specs/[###-feature-name]/spec.md`

## Summary

[Primary requirement, intended value, and technical approach]

## Technical Context

**Language/Version**: Python 3 / Vue 3 where applicable
**Primary Dependencies**: [Existing dependencies used by the change]
**Storage**: [SQLite/files/config or N/A]
**Testing**: pytest and applicable frontend checks
**Affected Layers**: [gateway/interfaces/application/domain/infrastructure/docs]
**Constraints**: [Performance, security, compatibility, or operational constraints]

## Constitution Check *(mandatory gate)*

Record `PASS`, `N/A`, or a justified exception for each item:

- **Layer ownership and dependency direction**: [result]
- **Orchestration versus execution boundary**: [result]
- **Contract synchronization**: [result]
- **Mutable runtime data safety**: [result]
- **Risk-based verification**: [result]
- **Documentation synchronization**: [result]
- **Compatibility and simplicity**: [result]
- **Python quality standards**: [PASS/N/A; coding, testing, review, and available checks]
- **Unrelated work preservation**: [result]

Exceptions MUST be recorded in Complexity and Risk Tracking before implementation.

## Impact Analysis *(mandatory)*

- **Architecture Boundary Check**: [owners, dependencies, boundary tests]
- **Contract Impact**: [producers, consumers, and synchronized changes]
- **Multi-instance Impact**: [instance/event contexts or N/A]
- **Runtime Data Safety**: [mutable data and migration handling or N/A]
- **Migration and Compatibility**: [external compatibility, rollback, recovery, or N/A]
- **Documentation Impact**: [durable documents, lifecycle category, nearest category README/load triggers, and cross-category routes to update]
- **Python Quality Impact**: [changed Python surfaces, type/error/security risks, tests, and available checks or N/A]

## Project Structure

Use only affected paths from the current repository:

```text
gateway/
interfaces/
application/
domain/
infrastructure/
docs/
tests/
```

**Structure decision**: [Affected paths and why ownership belongs there]

## Implementation Approach

1. [Dependency-ordered implementation step]
2. [Dependency-ordered implementation step]

## Verification Plan *(mandatory)*

- **Focused checks**: [tests or document checks]
- **Python checks**: [focused pytest, compile/static/security checks, or N/A with reason]
- **Boundary/contract checks**: [tests or N/A with reason]
- **Broader checks**: [full suite/runtime/browser check or N/A with reason]
- **Acceptance evidence**: [how success criteria will be demonstrated]

## Complexity and Risk Tracking

| Exception or Risk | Why Needed | Mitigation and Verification |
| --- | --- | --- |
| None | N/A | N/A |
