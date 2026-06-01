---
name: harness-rework
description: Manually flip one task in the current run's plans.json back to rework (append a reason, bump rework_count) so the next /harness-work rebuilds it. Use between runs, never while /harness-work is executing. Triggers on /harness-rework <task-id> [reason].
---

# Harness Rework (manual control)

You push one task back to rework so the coordinator rebuilds it on the next /harness-work.

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`.

## Input
The command gives you a TASK_ID and an optional reason. If no TASK_ID is given, print the task ids from `RUN_DIR/plans.json` and ask which one.

## Steps
1. Load `RUN_DIR/plans.json`. Find the task with id == TASK_ID. If absent, list the valid ids and stop.
2. Set its `status` to `"rework"`.
3. Append the reason (or `"manual rework requested"` if none) to its `rework_notes` array.
4. Increment its `rework_count` (treat missing as 0).
5. Save `RUN_DIR/plans.json`.
6. Tell the user: "Task <TASK_ID> set to rework. Run /harness-work to rebuild and re-audit."

## Rules
- Edit only `RUN_DIR/plans.json`, and only the three fields above on the one task.
- This is a between-runs control. Do NOT use it while `/harness-work` is running — the coordinator is the sole writer of plans.json during a run, and a concurrent edit would race.
