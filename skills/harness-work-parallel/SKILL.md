---
name: harness-work-parallel
description: "Phase 4 (parallel) coordinator — opt-in alternative to /harness-work. Drives implementation via the dynamic Workflow tool: fan-out write-only worker subagents per wave, serialize commits, then canonical + adversarial audit, rework loop, integration. Keeps every harness singleton (git, plans.json, active_role) serial in the coordinator. Triggers on /harness-work-parallel."
---

# Phase 4 — Parallel coordinator (dynamic-workflow path)

This is an **opt-in** alternative to `/harness-work`. Same phase-4 job — build every task, audit every task, rework loop, integration — but it dispatches the **parallel-safe** work (the build fan-out and the adversarial audit) through the **Workflow tool**, while you (the main loop) stay the coordinator for everything race-prone.

`/harness-work` is unchanged and remains the default. Use this only when you want larger-scale parallel build + adversarial verification (it can use substantially more tokens — confirm with the user before starting).

## What stays SERIAL in you (the coordinator), never in the workflow
- **git commits** — workers run with `COMMIT_MODE: defer` and never commit; you commit each task yourself, one at a time (single git writer → no index race).
- **`RUN_DIR/plans.json`** — you are the sole writer of every status transition. The workflow never writes it.
- **`state/.active_role`** — the **workflow script never touches it**, but YOU (one coordinator) set it per phase exactly like `/harness-work`: `worker` around the build fan-out, `auditor` around the audit fan-out, `integration` around integration. This is safe because the two phases never overlap and only one coordinator runs (precondition 3) — it restores the `hooks/` backstop and routes worker Write events to the run-scoped `file_change_log.jsonl` (which the auditor's accuracy guardrail cross-references). Setting it from the single coordinator is NOT the parallel-agent collision the harness warns about; that collision is many agents flipping one global file, which the script deliberately never does.

## Canonical-auditor serialization (why the audit fan-out is partly serial)
Each canonical `harness-auditor` does a read-modify-write on the single shared `RUN_DIR/audit_log.json`, so the workflow script dispatches canonical auditors **one at a time** (the read-only refuters still fan out in parallel). You do not need to manage this — it is enforced inside `harness-build-parallel.js` — but know that audit wall-clock scales with task count, while the build phase is fully parallel.

## Run directory
Resolve RUN: session run-id, else read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`. Every path below is inside RUN_DIR.

## Preconditions (stop on any failure)
1. Load `RUN_DIR/plans.json`. If missing or `locked` is not true → tell the user to run `/harness-plan` and stop.
2. Validate structure with the shipped validator (same as `/harness-work`):
   - `$CLAUDE_PLUGIN_ROOT` set → `python3 "$CLAUDE_PLUGIN_ROOT/orchestrator/validate_plans.py" RUN_DIR/plans.json`
   - else `find ~/.claude/plugins/cache -name "validate_plans.py" -path "*/orchestrator/*" 2>/dev/null | head -1`, else `orchestrator/validate_plans.py` relative to CWD.
   - Exit 0 → continue. Exit 4/5 → show stderr and stop.
3. **Concurrency guard:** if `state/.active_role` exists, a coordinator may already be running against this repo (or one crashed). Show its contents and stop; tell the user to finish that run or, if stale, clear it (`rm state/.active_role`) — see `/harness-doctor`. Do not proceed while it exists.
4. **Clean tree check (deferred-commit needs it):** run `git status --porcelain`. Intersect the dirty paths with the union of all tasks' `files_expected`. If any overlap, stop and **list the specific conflicting files** so the user knows exactly what to commit or stash — otherwise the per-task commit below cannot cleanly scope a task's diff.

## Locate the workflow script
Find `harness-build-parallel.js` the same way the validator is found:
- `$CLAUDE_PLUGIN_ROOT` set → `$CLAUDE_PLUGIN_ROOT/workflows/harness-build-parallel.js`
- else `find ~/.claude/plugins/cache -name "harness-build-parallel.js" -path "*/workflows/*" 2>/dev/null | head -1`
- else `workflows/harness-build-parallel.js` relative to CWD (local dev install).
Call the resulting path SCRIPT below. You will invoke the Workflow tool with `{ scriptPath: SCRIPT, args: {...} }`.

## Compute waves
Same resolver as `/harness-work`, with `--waves`:
- `python3 "<resolver.py>" --waves RUN_DIR/plans.json` (locate resolver.py via the same `$CLAUDE_PLUGIN_ROOT` / plugin-cache / CWD fallback).
- Non-zero exit → show stderr (cycle / unknown dep) and stop.
- stdout = one wave per line, space-separated task ids, in execution order. Each wave is dependency-safe to build in parallel.

## Model selection (optional, passed into the workflow)
Mirror `/harness-work`: worker → a capable coding model (e.g. `sonnet`); auditor → the most capable available (e.g. `opus`, else `sonnet`, else omit); refuters → a fast model is fine (e.g. `sonnet`/`haiku`). Pass these as `workerModel`/`auditorModel`/`refuterModel` in args; omit any tier the user's plan lacks (the agent then inherits the session model). Never fail a run over an unavailable model.

## Per-wave loop (in wave order; skip tasks already `verified`)
Let TASKS = the wave's tasks whose status is not `verified` (each as `{ id, title }` from plans.json). If empty, skip to the next wave. Keep a transient (in-memory, NOT in plans.json) `build_fail[id]` counter per task; `rework_count` in plans.json is reserved for AUDIT failures so its semantics match `/harness-work`.

1. **Mark in_progress.** In `RUN_DIR/plans.json` set each TASK's `status` = `in_progress`, `assigned_worker` = `worker-<id>`. (You are the sole writer.)
2. **Build fan-out.** Set `state/.active_role` = `worker <RUN> <ISO-8601-UTC-timestamp>` (so the post-tool hook routes worker Write events to the run-scoped `file_change_log.jsonl`). Then invoke the Workflow tool:
   `Workflow({ scriptPath: SCRIPT, args: { runDir: RUN_DIR, mode: "build", tasks: TASKS, workerModel } })`
   It dispatches one write-only worker per task in parallel (each told `COMMIT_MODE: defer`) and returns `{ results: [{ id, ok, summary | error }] }`. **Delete `state/.active_role`** after it returns (before you commit — committing must not be gated by the auditor backstop).
3. **Serialize commits (you, one task at a time).** For each `ok: true` result, in task order: read that task's `files_expected` from plans.json and run `git add <files_expected>` (this stages ONLY that task's owned paths) then commit, choosing the message by what kind of retry this is: first successful build → `git commit -m "task <id>: <title>"`; a re-commit after a BUILD failure (`build_fail[id] > 0`, no prior commit) → `git commit -m "task <id>: <title> (build-retry <build_fail[id]>)"`; a re-commit after an AUDIT failure (`rework_count > 0`) → `git commit -m "task <id>: <title> (rework <rework_count>)"`. Set the task's `status` = `submitted`. For any `ok: false` result: it is a BUILD failure — increment `build_fail[id]`, set `status` = `rework`, append the error to `rework_notes`, skip its commit (do NOT touch `rework_count`).
   **Stray-file scope check.** After committing the wave's tasks, run `git status --porcelain`. Because each commit staged only its task's `files_expected`, any path still showing as changed/untracked is a **stray** — a worker wrote outside its `files_expected` (a scope violation). A stray is never committed (it was never staged), so it cannot corrupt a task's commit diff; surface it to the user with a scope-violation warning naming the path, and leave it for the next-wave clean-tree gate. The independent auditor also catches out-of-scope writes via the run-scoped `file_change_log.jsonl` (which is now populated because step 2 set the `worker` role).
4. **Audit fan-out.** Set `state/.active_role` = `auditor <RUN> <ISO-8601-UTC-timestamp>` (this re-arms the bash backstop and is what permits the canonical auditor's single allowed `audit_log.json` redirect). For the tasks now `submitted`, invoke:
   `Workflow({ scriptPath: SCRIPT, args: { runDir: RUN_DIR, mode: "audit", tasks: <submitted tasks>, refuters: 2, auditorModel, refuterModel } })`
   Each task gets the canonical `harness-auditor` (dispatched **one at a time** inside the script, so writes to `RUN_DIR/audit_log.json` — the authoritative record — never race) plus N read-only adversarial refuters that fan out in parallel and write nothing. It returns `{ results: [{ id, canonical, refuter_count, refuter_blocking, refuter_majority_blocking, refuter_findings }] }`. **Delete `state/.active_role`** after it returns.
5. **Record verdicts (you, sole plans.json writer).** For each submitted task, read the latest matching entry in `RUN_DIR/audit_log.json` — that entry is authoritative, not workflow prose:
   - **verified** — canonical entry verdict is `PASS` **and** `refuter_majority_blocking` is false → set `status` = `verified`, `audit_verdict` = `PASS`.
   - **rework** — canonical `FAIL`, OR canonical `PASS` but the refuter majority found a real blocker → set `status` = `rework`, append the auditor's `rework_ticket` (and any `refuter_findings`) to `rework_notes`, increment `rework_count`. (A passing canonical overruled by refuters is a strengthened catch — record the refuter evidence so the next worker fixes it.)
6. **Rework sub-loop.** While any wave task is `rework` AND (`rework_count < 3` for audit failures) AND (`build_fail[id] < 3` for build failures), re-run steps 1–5 for that failing subset only (workers read `rework_notes` and fix only listed blockers). **Before re-dispatching a task that had no successful commit yet** (a build failure / scope violation — its files were written but never committed), restore a clean base first: `git checkout -- <files_expected>` for tracked paths, `git clean -fd <files_expected>` for untracked paths inside its scope, AND `git clean -fd -- <stray paths reported for this attempt>` for any out-of-scope files that worker left (those live outside `files_expected`, so the scoped clean above will not remove them). Then the rework worker starts on a clean tree and never builds on a half-written one. (A task that WAS committed and then audit-failed keeps its commit; the rework worker edits on top and you re-commit per step 3.) When a task reaches the limit, use `AskUserQuestion` to ask retry / skip / abort:
   - retry → reset its counters, keep it in the sub-loop.
   - skip → leave status as is, drop from the sub-loop.
   - abort → `rm -f state/.active_role` (defensive — normally already cleared by step 2/4) and stop the whole run.
7. **Gate before the next wave.** If any task in this wave is not `verified` (skipped/aborted/failed), do NOT start later waves that depend on it — stop and report which tasks blocked. Before starting the next wave, re-run `git status --porcelain`: if anything dirty intersects the next wave's `files_expected`, clean or report it (a prior wave's uncommitted leftover must not contaminate the next wave's commit scope).

## After all tasks
If every task is `verified`:
1. Write `integration <RUN> <ISO-8601-UTC-timestamp>` to `state/.active_role` (this single, serial step uses the role signal exactly like `/harness-work`).
2. Dispatch the integration subagent in the main loop (Agent tool, `subagent_type: deep-build-harness:harness-integration`) with RUN_DIR. (Integration is one agent end-to-end across task boundaries — keep it serial, not in the workflow.)
3. Delete `state/.active_role`.
4. Report and tell the user: "All tasks verified for run `<RUN>`. Run `/harness-docs` then `/harness-release`."

If some tasks are not verified, list them and stop.

## Rules
- You are the only writer of `RUN_DIR/plans.json`. The workflow and its subagents never edit it.
- Workers commit nothing (deferred); you commit, serially, one task at a time.
- The **workflow script** never touches `state/.active_role`; **you** set/clear it per phase (`worker` → build, `auditor` → audit, `integration` → integration), exactly as `/harness-work` does, and always clear it before committing and after a phase returns. A leftover `auditor`/`integration` role blocks all writes until removed.
- Never mark a task `verified` without a `PASS` entry in `RUN_DIR/audit_log.json`.
- `rework_count` counts AUDIT failures only (matching `/harness-work`); build failures use the transient `build_fail` counter.
- Resumable: on re-run, skip tasks already `verified`.
