---
name: harness-integration
description: "Phase 5 standalone — run end-to-end integration tests across all verified tasks. Use when coordinator crashed after tasks verified, or to re-run integration manually. Triggers on /harness-integration."
---

# Harness Integration (standalone)

Run end-to-end integration against a completed run without going through the full coordinator.

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`.

## Preconditions (check in order; stop and report if any fail)

1. `RUN_DIR/plans.json` must exist and `locked` must be `true`. If not → "Run /harness-plan first."
2. Every task in plans.json must have `status: "verified"`. If any are not → list the unverified tasks and say: "Run /harness-work to complete them before integration."
3. `state/.active_role` must not exist (another coordinator may be running). If it does → read it, warn: "Active role detected: <content>. If this is stale, clear it with: rm state/.active_role"

## Dispatch

1. Write `integration <RUN> <timestamp>` to `state/.active_role` (timestamp = current UTC ISO-8601, e.g. `2026-06-02T14:03:00Z`).
2. Dispatch the integration subagent (Agent tool, subagent_type `deep-build-harness:harness-integration`, model `sonnet`) with a prompt giving RUN_DIR.
3. Wait for it to return.
4. Delete `state/.active_role`.

## Result
Read `RUN_DIR/integration_log.json`. Report `overall_verdict` and any `blocking_issues`. If PASS: "Integration passed. Run /harness-docs then /harness-release." If FAIL: list blocking issues and say "Fix the issues and re-run /harness-integration."

## Rules
- Always clear `state/.active_role` after the subagent returns, even if it errors.
- Never modify plans.json or any source file.
