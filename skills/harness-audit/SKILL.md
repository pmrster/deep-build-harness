---
name: harness-audit
description: "Manually audit one task: dispatch the independent auditor subagent for a specific TASK_ID, update plans.json with the verdict. Use when coordinator crashed mid-run or to re-audit a task. Triggers on /harness-audit <task-id>."
---

# Harness Audit (standalone)

Audit one task independently without running the full coordinator. Useful when the coordinator crashed after a worker committed but before the auditor ran.

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`.

## Resolve TASK_ID
If a task id was given in $ARGUMENTS, use it. If none was given:
1. Read RUN_DIR/plans.json.
2. List all tasks with status `submitted` or `rework` (these are auditable).
3. Use AskUserQuestion to ask which task to audit, showing the id + title for each candidate.
4. If no tasks are in those states → say "No tasks need auditing. All are pending, in_progress, or already verified."

## Preconditions (check after resolving TASK_ID)

1. `RUN_DIR/plans.json` must exist and `locked` must be `true`. If not → "Run /harness-plan first."
2. The task must exist in plans.json.
3. `state/.active_role` must not exist. If it does → warn and stop: "Active role detected: <content>. Clear with: rm state/.active_role"

## Dispatch

1. Write `auditor <RUN> <timestamp>` to `state/.active_role` (timestamp = current UTC ISO-8601).
2. Dispatch the auditor subagent (Agent tool, subagent_type `deep-build-harness:harness-auditor`, model `opus` if available else `sonnet`) with a prompt giving TASK_ID and RUN_DIR.
3. Wait for it to return.
4. Delete `state/.active_role`.

## Update plans.json (you are the writer, not the auditor)

Read the latest entry in `RUN_DIR/audit_log.json` for this TASK_ID. The entry is authoritative — not the subagent's prose.

- Entry verdict `"PASS"` → set task `status: "verified"`, `audit_verdict: "PASS"` in plans.json.
- Entry verdict `"FAIL"` → set task `status: "rework"`, append `rework_ticket` from the entry to `rework_notes`, increment `rework_count`.
- No matching entry found → warn: "Auditor did not write an audit_log.json entry. Check for errors above." Do not change plans.json.

## Report
PASS: "Task <id> verified. Run /harness-work to continue remaining tasks, or /harness-integration if all tasks are now verified."
FAIL: list blocking issues from the audit entry and say "Fix the rework_ticket issues and re-run /harness-audit <task-id> or /harness-work."

## Rules
- You are the sole writer of plans.json. The auditor subagent never touches it.
- Always clear `state/.active_role` after the subagent returns, even if it errors.
- Never mark a task verified without a PASS entry in audit_log.json.
