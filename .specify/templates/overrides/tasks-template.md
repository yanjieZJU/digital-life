---
description: "Dependency-ordered implementation tasks for Digital Life"
---

# Tasks: [FEATURE NAME]

**Input**: `specs/[###-feature-name]/spec.md` and `plan.md`

## Format

Use `- [ ] T001 [P?] [US?] Action with exact path and observable completion`.
Mark `[P]` only when tasks touch different files and have no dependency.

## Phase 1: Confirm Scope and Safety

- [ ] T001 Re-read spec, plan, constitution, and affected current-system documentation
- [ ] T002 Confirm unrelated work is preserved and record affected contracts and runtime data
- [ ] T003 Confirm verification commands and acceptance evidence
- [ ] T004 For Python changes, load project Python coding, testing, and review standards

## Phase 2: Tests and Contract Guards

Behavior changes MUST include tests or an explicit executable verification task.

- [ ] T005 [P] Add or update focused tests in `tests/`
- [ ] T006 [P] Add or update boundary and contract checks in `tests/` when applicable
- [ ] T007 Verify migration, compatibility, or recovery behavior when applicable

## Phase 3: Implementation by User Scenario

### User Scenario 1 - [Title] (Priority: P1)

**Independent verification**: [Command or observable result]

- [ ] T008 [US1] Implement the smallest coherent change in the owning layer
- [ ] T009 [US1] Synchronize affected API/event/prompt/tool/config/persistence consumers
- [ ] T010 [US1] Run focused verification and resolve failures

### User Scenario 2 - [Title] (Priority: P2)

**Independent verification**: [Command or observable result]

- [ ] T011 [US2] Implement the scenario in the owning layer
- [ ] T012 [US2] Run focused verification and resolve failures

## Phase 4: Documentation and Delivery

- [ ] T013 Update durable documentation in the correct `docs/` lifecycle category, its nearest category README/load trigger, and major cross-category routes when applicable
- [ ] T014 For Python changes, run focused pytest and available Python quality checks
- [ ] T015 Run required boundary, contract, and broader checks
- [ ] T016 Re-check constitution compliance and acceptance criteria
- [ ] T017 Decide whether feature artifacts retain durable value; retain or remove accordingly
- [ ] T018 Report changes, verification, remaining risks, and artifact lifecycle decision

## Dependencies

- Safety and scope confirmation precede tests and implementation.
- Contract guards precede contract implementation where practical.
- Each scenario must pass its independent verification before final delivery.
- Documentation and final acceptance follow implementation verification.
