---
name: harness-status
description: Read-only status of the current deep-build-harness run — which phases are done, a per-task table (status, audit verdict, rework count), and the next command. Triggers on /harness-status.
---

# Harness Status (read-only)

You report the state of the current run. You modify nothing.

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`. If neither a session run nor `state/CURRENT` exists, say "No harness run found. Run /harness-interview to start one." and stop.

## Report
1. Phase progress — check which files exist in RUN_DIR and report the furthest reached:
   context.md (Phase 0) → codebase_map.md (1) → architecture.md (2) → plans.json (3) → audit_log.json entries (4–6).
2. If `RUN_DIR/plans.json` exists, print a table, one row per task: id · title · status · audit_verdict · rework_count. Note whether `locked` is true.
3. Tally: N verified / M total.
4. Stale active-role check. Read `state/.active_role` (via `python3 "$CLAUDE_PLUGIN_ROOT/orchestrator/active_role.py"` if available, else read the file directly: format `<role> <run> <timestamp>`). If it exists AND no /harness-work coordinator is currently running, it is stale — a crashed coordinator left it and it now blocks all Write/Edit (and mutating Bash for auditor/integration roles). Warn: `⚠️ Stale active role: "<contents>" (age <Xm>). It blocks file writes. Clear it: rm state/.active_role`. If `age_seconds` is large (> a few minutes), say so explicitly.
5. Suggest the next command: not locked → `/harness-plan`; locked with pending/rework tasks → `/harness-work`; all verified → `/harness-docs` then `/harness-release`.

## Rules
- Never write or edit any file. (You have no Write/Edit tools.)
- Report only what the files actually say; do not infer success.
