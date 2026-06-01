---
description: "List harness runs (status each) or switch the active run: /harness-runs [run-id]"
---

Invoke the `harness-runs` skill and follow it exactly. With no argument, list every run under `state/runs/` with a status summary and mark the current one. With a run-id argument, switch `state/CURRENT` to that run after verifying it exists.

$ARGUMENTS
