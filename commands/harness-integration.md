---
description: "Phase 5 — run integration tests across all verified tasks end-to-end"
---

Invoke the `harness-integration` skill and follow it exactly. Resolve the active run (session run-id, else `state/CURRENT`), require all tasks to be "verified", dispatch the integration subagent with RUN_DIR, and report the result.

$ARGUMENTS
