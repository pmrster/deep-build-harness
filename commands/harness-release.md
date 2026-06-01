---
description: "Phase 8 — pre-flight gate, final test run, release proof, git tag (only when all tasks verified)"
---

Invoke the `harness-release` skill and follow it exactly. Resolve the active run (session run-id, else `state/CURRENT`). Gate hard: refuse to release unless every task in the run's `plans.json` is "verified" with a PASS entry in its `audit_log.json` and the final test run passes. Then build `state/runs/<run>/release_proof/` and tag.

$ARGUMENTS
