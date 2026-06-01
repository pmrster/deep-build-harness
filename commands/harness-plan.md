---
description: "Phase 3 — decompose architecture into parallel-wave tasks with machine-verifiable AC, write state/plans.json"
---

Invoke the `harness-plan` skill and follow it exactly. Resolve the active run (session run-id, else `state/CURRENT`) and require its approved `context.md` and `architecture.md`; if missing, tell me which phase to run. Write the run's `plans.json` per the plugin's `templates/plans.json.schema`, gate on my approval, then lock.

$ARGUMENTS
