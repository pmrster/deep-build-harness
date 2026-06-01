---
name: harness-runs
description: List all deep-build-harness runs under state/runs/ with a status summary, and switch the active run by updating state/CURRENT. Triggers on /harness-runs (optionally with a run-id to switch to).
---

# Harness Runs

You list runs and, on request, switch which run is active. The only file you ever write is `state/CURRENT`.

## List (no argument)
1. List directories under `state/runs/`. If none, say "No runs yet. Run /harness-interview." and stop.
2. For each run id, if `state/runs/<id>/plans.json` exists, report task counts by status (e.g. 3 verified / 1 rework / 1 pending) and whether it is `locked`; otherwise report which phase files exist.
3. Mark the run whose id matches `state/CURRENT` as the current one.

## Switch (`/harness-runs <run-id>`)
1. Verify `state/runs/<run-id>/` exists. If not, list the valid ids and stop — do not create anything.
2. Write `<run-id>` to `state/CURRENT`.
3. Confirm: "Active run is now `<run-id>`."

## Rules
- Never delete a run or any state file.
- The only write you make is the single line in `state/CURRENT`.
