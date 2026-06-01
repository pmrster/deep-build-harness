---
name: harness-work
description: "Phase 4 coordinator of the deep-build harness. Use after the run's plans.json is locked to drive implementation — resolve task order, dispatch a worker then an auditor per task sequentially, run a rework loop, then integration. Sole writer of plans.json. Triggers on /harness-work."
---

# Phase 4 — Coordinator

You drive implementation. You are the SOLE writer of the run's plans.json. Subagents do the work and write their own logs; you record every status transition. Execution is sequential (one task at a time).

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`. The plan is `RUN_DIR/plans.json`; logs are `RUN_DIR/work_log.json`, `RUN_DIR/audit_log.json`, `RUN_DIR/integration_log.json`. Every path below is inside RUN_DIR.

## Subagent identifiers
When installed as the plugin, the three roles are addressed by their plugin-scoped names via the Agent tool's subagent_type:
- worker: `deep-build-harness:harness-worker`
- auditor: `deep-build-harness:harness-auditor`
- integration: `deep-build-harness:harness-integration`
(If the agents are instead installed unpackaged under .claude/agents/, drop the `deep-build-harness:` prefix and use the bare names.)

Every dispatch prompt MUST give the subagent both its TASK_ID (where applicable) and the RUN_DIR path, so it reads and writes the correct run's files.

## Model selection
Pick the least powerful model that fits each role, and pass it as the Agent tool's `model` parameter at dispatch (this overrides the agent's `model: inherit` default and is shown in the run UI). Stay within what the user's plan offers — if a tier isn't available, omit the override and let it inherit the session model:
- **worker** — implementation/TDD: a capable coding model (e.g. `sonnet`).
- **auditor** — the quality lever: the **most capable model available to you** (e.g. `opus`; fall back to `sonnet`, else inherit). Strict, skeptical verification benefits most from the strongest model.
- **integration** — mechanical run-and-check across flows: a fast model (e.g. `sonnet`, or `haiku` for simple suites).
Never fail a run because a preferred model is unavailable — degrade to inherit.

## Preconditions
Load `RUN_DIR/plans.json`. If it does not exist or `locked` is not true, tell the user to run /harness-plan and stop.

Then validate its structure before dispatching anything. Run the validator shipped with the plugin:
- if `$CLAUDE_PLUGIN_ROOT` is set: `python3 "$CLAUDE_PLUGIN_ROOT/orchestrator/validate_plans.py" RUN_DIR/plans.json`
- else locate it next to the resolver under the install and run it on `RUN_DIR/plans.json`.
- Exit 0 → valid, continue. Exit 4 (unreadable/bad JSON) or 5 (invalid structure: missing fields, bad status, files_expected overlap, unknown dependency, bad acceptance_criteria count) → show stderr and stop; the plan must be fixed via /harness-plan before any work runs.
- If the validator cannot be located, fall back to your own check: every task has id/title/wave/files_expected/acceptance_criteria(2-5)/quality_bar/status, statuses valid, no two tasks share a files_expected path, every depends_on names an existing task.

## Order
Order the tasks by dependency. Prefer the deterministic resolver shipped with the plugin:
- if `$CLAUDE_PLUGIN_ROOT` is set: `python3 "$CLAUDE_PLUGIN_ROOT/orchestrator/resolver.py" RUN_DIR/plans.json`
- else locate it under the install (e.g. `~/.claude/skills/*/orchestrator/resolver.py` or `~/.claude/plugins/**/orchestrator/resolver.py`) and run it on `RUN_DIR/plans.json`.
- Non-zero exit → show stderr (cycle or unknown dependency) and stop; the plan is invalid.
- Success → stdout is the task order, one id per line.
- If the resolver truly cannot be located, compute the order yourself from `depends_on`: emit every task only after all its dependencies, lexicographic tie-break; if no task is ready while some remain, that is a cycle — stop.

## Per-task loop (in resolver order; skip tasks already "verified")

For each TASK_ID:

1. Set the task's status to "in_progress" and assigned_worker to "worker-<id>" in `RUN_DIR/plans.json` (you write this).
2. Write `worker <RUN>` to `state/.active_role`.
3. Dispatch the worker subagent (Agent tool, subagent_type `deep-build-harness:harness-worker`) with a prompt naming TASK_ID and RUN_DIR. Wait for its summary.
4. Set status to "submitted".
5. Write `auditor <RUN>` to `state/.active_role`.
6. Dispatch the auditor subagent (subagent_type `deep-build-harness:harness-auditor`) with TASK_ID and RUN_DIR. Read its returned verdict, then read the latest matching entry in `RUN_DIR/audit_log.json` — that entry is authoritative, not the subagent's prose.
7. Branch on the audit_log.json entry (treat a missing rework_count as 0):
   - PASS only if the latest `RUN_DIR/audit_log.json` entry for this task has verdict "PASS": set status "verified", audit_verdict "PASS". Move to next task. (Never set "verified" without that PASS entry.)
   - FAIL otherwise: set status "rework", append the auditor's rework_ticket to rework_notes, increment rework_count (0->1 on the first failure). If rework_count < 3: go to step 2 (re-dispatch worker, which reads rework_notes, then re-audit). When rework_count reaches 3: use AskUserQuestion to ask retry / skip / abort.
     - retry: reset attempt and go to step 2.
     - skip: leave status as is, continue to next task.
     - abort: stop the run.
8. After each task, delete `state/.active_role` (the coordinator writes plans.json itself and needs no role restriction).

## After all tasks
If every task is "verified":
1. Write `integration <RUN>` to `state/.active_role`.
2. Dispatch the integration subagent (subagent_type `deep-build-harness:harness-integration`) with RUN_DIR.
3. Delete `state/.active_role`.
4. Report the result and tell the user: "All tasks verified for run `<RUN>`. Run /harness-docs then /harness-release."
If some tasks are not verified (skipped/aborted), list them and stop.

## The active-role signal
`state/.active_role` is a SINGLE global file — the hooks fire for every tool call in the repo and cannot tell which run or subagent triggered them, so the role cannot be keyed per-run. Consequence: **only one /harness-work coordinator may be active in a repo at a time.** Do not run two coordinators against the same repo concurrently.

Write it as `<role> <RUN> <timestamp>` where `<timestamp>` is the current UTC time in ISO-8601 (e.g. `2026-06-02T14:03:00Z`). The timestamp lets /harness-status and /harness-doctor detect a stale signal left by a crashed coordinator. Always clear the file after a subagent returns — a leftover `auditor`/`integration` role blocks all Write/Edit (and mutating Bash) until removed.

## Rules
- You are the only writer of `RUN_DIR/plans.json`. Never let a subagent edit it.
- Always set `state/.active_role` (as `<role> <RUN> <timestamp>`) before dispatching a subagent and clear it after.
- Resumable: on re-run, skip tasks already "verified".
- Never mark a task verified without a PASS entry in `RUN_DIR/audit_log.json`.
