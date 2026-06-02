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

## Order — compute waves
Group tasks into dependency layers ("waves") so independent tasks in a layer can be built in parallel. Use the deterministic resolver shipped with the plugin with the `--waves` flag:
- if `$CLAUDE_PLUGIN_ROOT` is set: `python3 "$CLAUDE_PLUGIN_ROOT/orchestrator/resolver.py" --waves RUN_DIR/plans.json`
- else locate it under the install (e.g. `~/.claude/skills/*/orchestrator/resolver.py` or `~/.claude/plugins/**/orchestrator/resolver.py`) and run it with `--waves` on `RUN_DIR/plans.json`.
- Non-zero exit → show stderr (cycle or unknown dependency) and stop; the plan is invalid.
- Success → stdout is one wave per line, task ids space-separated, in execution order. Every task in a wave has all its dependencies satisfied by earlier waves and none on its wave-mates, so the wave is parallel-safe. (Waves are computed from `depends_on`, not the advisory `wave` field in plans.json.)
- If the resolver truly cannot be located, compute waves yourself: wave index of a task = 1 + max wave index of its dependencies (no deps → wave 1); group by index, ascending.

## Per-wave loop (in wave order; skip tasks already "verified")

Process waves in order. Within a wave, dispatch the not-yet-verified tasks **in parallel** — issue all their worker Agent calls in a single message, then all their auditor Agent calls in a single message. Worker and audit phases never overlap, so the global `state/.active_role` signal stays consistent. If your environment cannot run subagents in parallel, degrade gracefully to one task at a time — the result is identical, only slower.

For each wave, let TASKS = its tasks whose status is not "verified". If TASKS is empty, skip to the next wave.

1. For every task in TASKS: set status "in_progress" and assigned_worker "worker-<id>" in `RUN_DIR/plans.json` (you are the sole writer).
2. Write `worker <RUN> <timestamp>` to `state/.active_role`.
3. Dispatch one worker subagent per task **in parallel** (Agent tool, subagent_type `deep-build-harness:harness-worker`), each prompt naming its TASK_ID and the RUN_DIR. Wait for all to return. (Each worker writes only its own `RUN_DIR/work_logs/<task-id>.json`, so parallel workers never contend on a shared file.)
4. Set every returned task's status to "submitted".
5. Write `auditor <RUN> <timestamp>` to `state/.active_role`.
6. Dispatch one auditor subagent per task **in parallel** (subagent_type `deep-build-harness:harness-auditor`), each with its TASK_ID and RUN_DIR. After they return, for each task read the latest matching entry in `RUN_DIR/audit_log.json` — that entry is authoritative, not the subagent's prose.
7. For each task, branch on its audit_log.json entry (treat a missing rework_count as 0):
   - PASS (latest entry verdict "PASS"): set status "verified", audit_verdict "PASS". (Never set "verified" without that PASS entry.)
   - FAIL otherwise: set status "rework", append the auditor's rework_ticket to rework_notes, increment rework_count (0->1 on first failure).
8. Rework sub-loop for the wave: while any task in the wave is "rework" with rework_count < 3, re-run steps 2–7 **for that failing subset only** (re-dispatch those workers in parallel — they read rework_notes and fix only listed blockers — then re-audit that subset). When a task's rework_count reaches 3, use AskUserQuestion to ask retry / skip / abort for it:
   - retry: reset its attempt and keep it in the sub-loop.
   - skip: leave its status as is, drop it from the sub-loop.
   - abort: clear `state/.active_role` and stop the whole run.
9. After the wave settles, delete `state/.active_role`. **Gate before the next wave:** if any task in this wave is not "verified" (skipped/aborted), do NOT start later waves that depend on it — stop and report which tasks blocked, since dependents cannot be built on an unverified base.

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
