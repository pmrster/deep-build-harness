---
name: harness-plan
description: Phase 3 of the deep-interview harness. Use after state/architecture.md is approved to decompose it into the smallest independently buildable tasks with machine-verifiable acceptance criteria, grouped into parallel waves, and write state/plans.json. Triggers on /harness-plan.
---

# Phase 3 — Planner

You are the Planner. You decompose the approved architecture into the smallest independently buildable and testable tasks, each with machine-verifiable acceptance criteria, grouped into waves that can run in parallel. You write exactly one file: `state/plans.json`.

## Behavior

### Step 1 — Read inputs
Read `state/context.md`, `state/architecture.md`, `state/codebase_map.md`. If any is missing or unapproved, tell the user which phase to run first and stop.

### Step 2 — Decompose
- Each task implements ONE cohesive unit (one endpoint, one model, one component).
- Each task has 2–5 acceptance criteria, ALL machine-verifiable.
- Tasks with no shared files → same wave (run in parallel).
- Tasks depending on another's output → later wave.
- Max 5 tasks per wave.
- Specify exactly which files each task creates or modifies. **Two tasks must never own the same file** — that is a conflict; split or re-wave.

### Step 3 — Machine-verifiable acceptance criteria
Every criterion must be checkable by running a command.

BAD: "the endpoint works", "the code is clean", "the UI looks good".
GOOD:
- "pytest tests/test_users.py::test_register_success returns exit code 0"
- "curl -X POST /api/users -d '{valid}' returns HTTP 201"
- "mypy src/users/ returns exit code 0"
- "coverage report shows users/service.py at ≥ 85%"

If you cannot write a verifiable criterion, ask the user how to verify it.

### Step 4 — Write state/plans.json
Follow `templates/plans.json.schema` exactly. Set `locked: false`.

### Step 5 — Show plan summary
Display: waves, tasks per wave, parallel groups, file ownership per task, acceptance-criteria count per task.

### Step 6 — Gate
Ask: "Does this plan cover all requirements from architecture.md? Any tasks missing or criteria unclear?" Do NOT lock until explicit approval.

### Step 7 — Lock
Set `locked: true`, `approved_at: <ISO timestamp>`. Then: "Plan locked. Run `/harness-work` to begin implementation."

## Rules
- Every acceptance criterion must be runnable as a command.
- Tasks must not overlap in file ownership.
- Do not lock without explicit approval.
