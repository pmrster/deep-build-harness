# Deep Interview Harness

A Claude Code plugin that runs your work through a disciplined, multi-agent **expert-team pipeline** instead of a single best-effort pass. It interviews you until requirements are unambiguous, designs the system, decomposes it into machine-verifiable tasks, builds each one with TDD, and has an **independent auditor** re-run every check before anything is called done.

It uses only native Claude Code primitives — **subagents, skills, hooks, and file-based state** — so it works on any plan. No external orchestrator, no `claude -p` subprocesses.

## Why

| Plain subagents | This harness |
|---|---|
| Claude assumes it understood the ask | Interview until confidence ≥ 80, zero unknowns |
| Architecture decided inline | Dedicated, user-approved design step |
| Self-evaluation (biased) | Independent auditor re-runs every criterion |
| Context rot in one window | Each agent is context-isolated |
| "Looks done" | Done only when the auditor verifies it with evidence |

## The pipeline

```
/harness-interview     Phase 0  → state/context.md         interview until unambiguous
/harness-scan          Phase 1  → state/codebase_map.md    map existing code first
/harness-architecture  Phase 2  → state/architecture.md    schema + exact API contracts
/harness-plan          Phase 3  → state/plans.json         tasks with machine-verifiable AC
/harness-work          Phase 4  → coordinator drives build per task (worker → auditor)
                       Phase 5  → state/integration_log.json  end-to-end across tasks
                       Phase 6  → state/audit_log.json     independent verdict per task
/harness-docs          Phase 7  → README / CHANGELOG / docs
/harness-release       Phase 8  → state/release_proof/ + git tag (only if all verified)
```

Each phase writes one file. The next phase reads it. Agents never share memory — **files are the only channel.**

## Install

Add the plugin to Claude Code (from this directory or your plugin marketplace), then run the commands inside a normal Claude Code session in your target project:

```
/harness-interview
```

Follow the gate at the end of each phase. Phases 0–3 and 7–8 are interactive; `/harness-work` runs the build loop.

## Quickstart

Start in any folder — greenfield is fine. Use a git repo so workers can commit and the release phase can tag.

```bash
mkdir my-app && cd my-app && git init
claude                       # the plugin loads automatically (see Install)
```

Then drive the pipeline from inside the session. You can pass your idea straight to the interview:

```
/harness-interview build a Python CLI todo app with add, list, and done commands
```

The interviewer asks until requirements are unambiguous and writes `state/context.md`. Approve it, then run each phase as it prompts you:

```
/harness-scan            # maps existing code (marks greenfield if empty) → state/codebase_map.md
/harness-architecture    # schema + exact contracts → state/architecture.md   (you approve)
/harness-plan            # tasks with verifiable criteria → state/plans.json   (you approve → locks)
/harness-work            # builds each task: worker (TDD) → auditor, with rework loop
/harness-docs            # README/CHANGELOG/API from the real code
/harness-release         # final gate + git tag, only if every task is verified
```

Each phase reads the previous phase's file and tells you the next command. Inspect progress anytime: `cat state/plans.json`, `cat state/audit_log.json`, `git log`.

To start over, delete `state/` (it is gitignored).

### Local install for testing

```bash
# Symlink the plugin into your user skills dir, then restart claude:
ln -s /path/to/claude-agents-harness ~/.claude/skills/deep-interview-harness
# It loads next session as deep-interview-harness@skills-dir.
# Verify with /plugin and /agents. Remove with: rm ~/.claude/skills/deep-interview-harness
```

## How phase 4 works

`/harness-work` (the coordinator) runs in your session and, **sequentially** for each task in dependency order:

1. orders tasks with `orchestrator/resolver.py` (deterministic; stops on cycles/unknown deps),
2. dispatches a **worker** subagent (TDD, implements one task, commits, writes `work_log.json`),
3. dispatches an **auditor** subagent (re-runs every acceptance criterion itself, writes `audit_log.json`),
4. on FAIL runs a **rework loop** (max 3, then asks you: retry / skip / abort),
5. when all tasks are verified, runs an **integration** subagent end-to-end.

The coordinator is the **sole writer of `plans.json`**. Workers and the auditor write only their own append-only logs and return results. Runs are **resumable** — re-running skips already-verified tasks.

## Roles and permissions

| Agent | Can write | Purpose |
|---|---|---|
| worker | source, `work_log.json`, commits | implement one task with TDD |
| auditor | `audit_log.json` only | independently verify; **no Write/Edit** |
| integration | `integration_log.json` only | end-to-end flows; **no Write/Edit** |

Read-only roles are enforced twice: the agent's `tools:` frontmatter omits Write/Edit, and a `PreToolUse` hook blocks them as a backstop (signalled by `state/.active_role`). A `PostToolUse` hook logs every Write/Edit to `state/file_change_log.jsonl`.

## State files

| File | Writer | Notes |
|---|---|---|
| `context.md` | interviewer | locked after your approval |
| `codebase_map.md` | scanner | |
| `architecture.md` | architect | locked after your approval |
| `plans.json` | coordinator | run-state; `locked: true` after you approve the plan |
| `work_log.json` | workers | append-only |
| `audit_log.json` | auditor | append-only, immutable entries |
| `integration_log.json` | integration | per run |
| `file_change_log.jsonl` | post-tool hook | append-only |

`state/` is created at runtime and gitignored.

## Quality lever

`calibration/audit-fail-examples.md` trains the auditor to treat specific patterns as hard failures (wrong response schema, coverage one point short, missing error handling, hardcoded secrets, tests-after-code, path mismatches, self-reported evidence). **Add examples here to raise output quality over time** — it is the main tuning knob.

## Requirements

- Claude Code (any plan).
- Python 3 (only for `orchestrator/resolver.py`; stdlib only).
- Your target project must provide its own test / lint / type-check commands; the interviewer captures them into `context.md` and the worker/auditor run them.

## Development

```
python3 -m pytest tests/        # resolver unit tests
```

## Status

All 8 phases implemented. Sequential execution (parallel-within-wave is a planned enhancement). The resolver and hooks are unit-tested; a full live end-to-end run on a real project is the next validation step.
