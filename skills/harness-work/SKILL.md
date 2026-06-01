---
name: harness-work
description: Phase 4 coordinator of the deep-interview harness. Use after state/plans.json is locked to drive implementation: resolve task order, dispatch a worker then an auditor per task sequentially, run a rework loop, then integration. Sole writer of plans.json. Triggers on /harness-work.
---

# Phase 4 — Coordinator

You drive implementation. You are the SOLE writer of state/plans.json. Subagents do the work and write their own logs; you record every status transition. Execution is sequential (one task at a time).

## Subagent identifiers
When installed as the plugin, the three roles are addressed by their plugin-scoped names via the Agent tool's subagent_type:
- worker: `deep-interview-harness:harness-worker`
- auditor: `deep-interview-harness:harness-auditor`
- integration: `deep-interview-harness:harness-integration`
(If the agents are instead installed unpackaged under .claude/agents/, drop the `deep-interview-harness:` prefix and use the bare names.)

## Preconditions
Load state/plans.json. If it does not exist or "locked" is not true, tell the user to run /harness-plan and stop.

## Order
Run: `python3 orchestrator/resolver.py state/plans.json`
- Non-zero exit: show stderr (cycle or unknown dependency) and stop — the plan is invalid.
- Success: stdout is the task order, one id per line.

## Per-task loop (in resolver order; skip tasks already "verified")

For each TASK_ID:

1. Set the task's status to "in_progress" and assigned_worker to "worker-<id>" in plans.json (you write this).
2. Write "worker" to state/.active_role.
3. Dispatch the worker subagent (Agent tool, subagent_type `deep-interview-harness:harness-worker`) with a prompt naming TASK_ID. Wait for its summary.
4. Set status to "submitted".
5. Write "auditor" to state/.active_role.
6. Dispatch the auditor subagent (subagent_type `deep-interview-harness:harness-auditor`) with TASK_ID. Read its returned verdict, then read the latest matching entry in state/audit_log.json — that entry is authoritative, not the subagent's prose.
7. Branch on the audit_log.json entry (treat a missing rework_count as 0):
   - PASS only if the latest audit_log.json entry for this task has verdict "PASS": set status "verified", audit_verdict "PASS". Move to next task. (Never set "verified" without that PASS entry.)
   - FAIL otherwise: set status "rework", append the auditor's rework_ticket to rework_notes, increment rework_count (0->1 on the first failure). If rework_count < 3: go to step 2 (re-dispatch worker, which reads rework_notes, then re-audit). When rework_count reaches 3: use AskUserQuestion to ask retry / skip / abort.
     - retry: reset attempt and go to step 2.
     - skip: leave status as is, continue to next task.
     - abort: stop the run.
8. After each task, delete state/.active_role (the coordinator writes plans.json itself and needs no role restriction).

## After all tasks
If every task is "verified":
1. Write "integration" to state/.active_role.
2. Dispatch the integration subagent (subagent_type `deep-interview-harness:harness-integration`).
3. Delete state/.active_role.
4. Report the result and tell the user: "All tasks verified. Run /harness-docs then /harness-release."
If some tasks are not verified (skipped/aborted), list them and stop.

## Rules
- You are the only writer of plans.json. Never let a subagent edit it.
- Always set state/.active_role before dispatching a subagent and clear it after.
- Resumable: on re-run, skip tasks already "verified".
- Never mark a task verified without a PASS entry in audit_log.json.
