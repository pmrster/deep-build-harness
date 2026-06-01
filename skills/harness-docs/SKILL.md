---
name: harness-docs
description: Phase 7 of the deep-build harness. Use after all tasks reach "verified" to write user-facing docs (README, CHANGELOG, API docs) describing what was actually built, not what was planned. Triggers on /harness-docs.
---

# Phase 7 — Documentation Writer

You write documentation after all tasks are verified. You describe what was actually built — read the real source, not just the plan.

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`. All state files below live in RUN_DIR.

## Preconditions
Read RUN_DIR/plans.json. If any task's status is not "verified", tell the user which tasks remain and to run /harness-work first. Stop.

## Behavior

### Step 1 — Read state and code
Read RUN_DIR/context.md (original requirements), RUN_DIR/architecture.md (design decisions), RUN_DIR/plans.json (tasks + status), and the actual source files that were created/modified (per files_expected). Where the implementation diverged from architecture.md, document what exists.

### Step 2 — Write README.md (project root)
Sections:
- What this does (one paragraph, plain language)
- Prerequisites
- Setup and installation
- How to run (dev + production)
- How to run tests
- API reference (every endpoint with a copy-pasteable example)
- Configuration reference

### Step 3 — Write CHANGELOG.md
- Version and date
- Added (from task titles)
- Changed (if extending existing code)

### Step 4 — API docs (if applicable)
If the project exposes API endpoints, write docs/api.md: every endpoint — method, path, auth required, request schema, response schema, examples.

## Rules
- Document what actually exists in code, not what was planned.
- Every code example must be copy-pasteable and correct (verify against the source).
- If something in architecture.md changed during implementation, document the real behavior.

On completion: "Docs written. Run /harness-release to package the release."
