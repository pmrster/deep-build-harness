---
description: "Manually audit one task: /harness-audit <task-id>"
---

Invoke the `harness-audit` skill and follow it exactly. Resolve the active run (session run-id, else `state/CURRENT`), audit the named task with the independent auditor subagent, and update plans.json with the verdict.

$ARGUMENTS
