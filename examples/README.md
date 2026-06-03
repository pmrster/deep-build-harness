# Examples

Synthetic but schema-accurate output from a complete harness run on a toy Python CLI project.
These show what each phase produces — useful for understanding the format before running your own.

| File | Phase | Written by |
|---|---|---|
| `todo-cli/context.md` | 0 — Interview | Interviewer skill |
| `todo-cli/plans.json` | 3 — Plan | Planner skill (locked after user approval) |
| `todo-cli/audit_log.json` | 4/6 — Audit | Auditor agent (one entry per task, all PASS) |

Real runs live under `state/runs/<run-id>/` and are gitignored — they're per-user, not part of the plugin.
