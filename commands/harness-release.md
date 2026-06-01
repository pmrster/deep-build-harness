---
description: "Phase 8 — pre-flight gate, final test run, release proof, git tag (only when all tasks verified)"
---

Invoke the `harness-release` skill and follow it exactly. Gate hard: refuse to release unless every task in `state/plans.json` is "verified" with a PASS entry in `state/audit_log.json` and the final test run passes. Then build `state/release_proof/` and tag.

$ARGUMENTS
