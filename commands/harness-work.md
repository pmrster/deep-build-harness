---
description: "Phase 4 — drive implementation: resolve order, dispatch worker+auditor per task, rework loop, integration"
---

Invoke the `harness-work` skill and follow it exactly. Require a locked `state/plans.json` (run `/harness-plan` first if missing). Drive the sequential coordinator loop: per task, dispatch the harness-worker then the harness-auditor subagent, owning all plans.json writes, with the rework loop and integration pass.

$ARGUMENTS
