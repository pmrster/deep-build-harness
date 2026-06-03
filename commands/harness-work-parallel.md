---
description: "Phase 4+6 (parallel, opt-in) — fan-out write-only build + adversarial audit via a dynamic Workflow; serial commit, plans.json writes, and active_role stay in the coordinator. Alternative to /harness-work."
---

Invoke the `harness-work-parallel` skill and follow it exactly. This is the opt-in dynamic-workflow alternative to `/harness-work` (which stays the default, unchanged). Resolve the active run (session run-id, else `state/CURRENT`) and require its locked `plans.json` under `state/runs/<run>/` (run `/harness-plan` first if missing).

Drive the split coordinator: per wave, dispatch the build fan-out and the canonical+adversarial audit through the Workflow tool (script `workflows/harness-build-parallel.js`), while you keep every harness singleton serial — you own all `plans.json` writes, and you commit each task one at a time (workers run with `COMMIT_MODE: defer`). The Workflow **script** never writes `state/.active_role`; **you** set it per phase exactly as `/harness-work` does (`worker` before the build fan-out, `auditor` before the audit fan-out, `integration` before integration) and clear it after each phase returns. Run the rework loop and the final serial integration pass exactly as the skill describes. Confirm with the user before starting, since dynamic workflows can use substantially more tokens.

$ARGUMENTS
