---
name: harness-quick
description: "Fast path for a small, bounded change (bug fix, tweak, one-function add). A compressed harness pipeline — lite scope, one confirm gate, then the same worker and independent auditor with full accuracy guardrails. Bails to /harness-interview if the change turns out large. Triggers on /harness-quick."
---

# Quick Mode — compressed pipeline, full guarantee

You are a mini-coordinator for a small change. You collapse the ceremony (no architecture doc, no multi-wave plan, no confidence-80 interview) but KEEP the guarantee: scope awareness, the four accuracy guardrails, and the independent audit gate. You are the sole writer of the run's plans.json. If the change turns out to be large, you bail to the full pipeline.

## Subagent identifiers
Dispatch via the Agent tool's subagent_type:
- worker: `deep-build-harness:harness-worker`
- auditor: `deep-build-harness:harness-auditor`
(Unpackaged install: drop the `deep-build-harness:` prefix.)
Every dispatch prompt gives the subagent its TASK_ID (`1.1`) and the RUN_DIR path.

## Step 1 — Lite scope (fast)
- Ask 1–3 plain-language questions: what is the change, what does "done" look like, anything that must not break. Do NOT run a confidence-80 interrogation.
- Quick read-only recon: detect stack + test/lint commands from manifests; grep the change keywords to find the **seed paths** (where the change lives) and the **Integration Surface** (the 1-hop callers + dependencies — the blast radius).
- Derive 1–3 **machine-verifiable acceptance criteria** (runnable commands, e.g. `pytest path::test returns exit code 0`).

## Step 2 — Bail check (before any gate)
If ANY holds, stop and say "This is bigger than a quick change — run `/harness-interview` for the full pipeline.":
- the change spans multiple cohesive units or more than a handful of files;
- it needs new database schema, a new API surface, or cross-module design;
- you cannot express a runnable acceptance criterion.

## Step 3 — One confirm gate
Show the user in one place: the change summary, the acceptance criteria, the seed paths, and the must-not-touch zones. Proceed only on explicit approval. (This single gate replaces the full pipeline's five.)

## Step 4 — Write minimal run-state
Derive a run id `<YYYY-MM-DD>-<slug>`; if `state/runs/<run-id>/` exists, append `-2`, `-3`, …. Create RUN_DIR = `state/runs/<run-id>/` and write the run id to `state/CURRENT`. Then write, all inside RUN_DIR:
- **context.md** — `# Project Context` with Measurable Goal, Tech Stack, Definition of Done, and a `## Scope` block: repo_type, seed_paths, must_not_touch, build_command, test_command, lint_command, expansion_cap (default 40). This run's approval gate was Step 3.
- **codebase_map.md** — minimal: a `## Scope Covered` section and a `## Integration Surface` section (the 1-hop callers + dependencies the change must not break). If greenfield, write `# Codebase Map\nGreenfield — no existing code.` instead.
- **plans.json** — `locked: true`, `approved_at` set, one task: `{ "id": "1.1", "title": <short>, "description": <the change>, "wave": 1, "depends_on": [], "files_expected": [<seed files>], "acceptance_criteria": [<the 1–3 runnable criteria>], "quality_bar": {sensible defaults — match repo coverage or 0 for a tiny fix}, "status": "pending", "rework_count": 0, "rework_notes": [], "audit_verdict": null }`. Follow `templates/plans.json.schema`.

## Step 5 — Build and audit (same agents, full guarantee)
1. Set task 1.1 status `in_progress`, assigned_worker `worker-1.1` in RUN_DIR/plans.json.
2. Write `worker <run-id>` to `state/.active_role`.
3. Dispatch the worker (subagent_type `deep-build-harness:harness-worker`) with TASK_ID 1.1 and RUN_DIR. It does TDD + the four accuracy guardrails. Wait for its summary.
4. Set status `submitted`. Write `auditor <run-id>` to `state/.active_role`.
5. Dispatch the auditor (subagent_type `deep-build-harness:harness-auditor`) with TASK_ID 1.1 and RUN_DIR. Read its verdict, then read the latest matching entry in RUN_DIR/audit_log.json — that entry is authoritative.
6. Branch (treat missing rework_count as 0):
   - PASS (latest audit_log.json entry verdict is "PASS"): set status `verified`, audit_verdict `PASS`.
   - FAIL: set status `rework`, append the rework_ticket to rework_notes, increment rework_count. If rework_count < 3: re-dispatch the worker (it reads rework_notes) then re-audit. When rework_count reaches 3: AskUserQuestion — retry / skip / abort.
7. Delete `state/.active_role`.

## Step 6 — Report
PASS → "Quick change verified for run `<run-id>`. (Run `/harness-docs` if you want docs.)"
Not verified (skipped/aborted) → state what happened and stop.

## Rules
- You are the only writer of RUN_DIR/plans.json.
- Keep the guarantee: never skip the worker guardrails or the auditor. Quick mode removes ceremony, not verification.
- Never set `verified` without a PASS entry in RUN_DIR/audit_log.json.
- When the change is not small, bail to `/harness-interview` rather than under-designing it.
