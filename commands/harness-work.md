---
description: "Phase 4 — drive implementation: resolve order, dispatch worker+auditor per task, rework loop, integration"
---

Invoke the `harness-work` skill and follow it exactly. Resolve the active run (session run-id, else `state/CURRENT`) and require its locked `plans.json` under `state/runs/<run>/` (run `/harness-plan` first if missing). Drive the sequential coordinator loop: per task, dispatch the harness-worker then the harness-auditor subagent (passing RUN_DIR), owning all plans.json writes, with the rework loop and integration pass.

$ARGUMENTS
