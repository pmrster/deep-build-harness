---
description: "Manually flip a task back to rework so /harness-work rebuilds it: /harness-rework <task-id> [reason]"
---

Invoke the `harness-rework` skill and follow it exactly. Resolve the active run (session run-id, else `state/CURRENT`). Set the named task's status to rework in that run's `plans.json`, append the reason, bump rework_count, then tell me to run `/harness-work`. Only do this between runs, not during a `/harness-work` loop.

$ARGUMENTS
