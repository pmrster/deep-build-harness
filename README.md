# Deep Build Harness

A Claude Code plugin that runs your work through a disciplined, multi-agent **expert-team pipeline** instead of a single best-effort pass. It interviews you until requirements are unambiguous, maps the codebase, designs the system, decomposes it into machine-verifiable tasks, builds each one with TDD, and has an **independent auditor** re-run every check before anything is called done.

It uses only native Claude Code primitives — **subagents, skills, hooks, and file-based state** — so it works on any plan. No external orchestrator, no `claude -p` subprocesses, no separate program to run: install it and drive it with slash commands inside a normal Claude Code session.

---

## The problem it solves

A single agent told to "build X" tends to: make silent assumptions, design as it types, mark its own work done, and lose the thread as context fills. The failure usually isn't capability — it's **discipline and verification**. Nothing forced it to pin requirements, nothing designed before coding, and the thing that graded the result was the same thing that wrote it.

The core idea: **simulate an expert software team as a set of isolated agents that communicate only through files, and put an independent skeptic between "done" and "shipped."**

Each role is a separate agent with its own fresh context and its own narrow tool permissions. No role inherits another's conversation; the only thing that crosses a boundary is a file on disk. One role in particular — the **auditor** — never writes source and never trusts a report: it re-runs every acceptance criterion itself, and is calibrated to fail borderline work.

That's the whole bet: **rigor up front (interview → design → plan), isolation during work, and adversarial verification before release.**

## How it improves normal Claude agent work

| Plain agent / ad-hoc subagents | Deep Build Harness |
|---|---|
| Assumes it understood the ask | Interviews until confidence ≥ 80, zero unknowns |
| Designs inline while coding | Dedicated, user-approved architecture step before any code |
| Grades its own output (biased) | **Independent auditor re-runs every criterion** with evidence |
| "Looks done" / "tested manually" | Done only when every machine-checkable criterion passes |
| Everything in one context window (rot) | Each agent is context-isolated; fresh window per role |
| Plan lives in the model's head | Locked `plans.json` with runnable acceptance criteria |
| Work lost when the session dies | File-state, run-namespaced, resumable across sessions |
| Any agent can edit anything | Per-role tool isolation (the auditor literally cannot write) |

## Five principles

1. **Files are the contract, not chat.** Every phase writes one file; the next reads it. State is durable, inspectable, and survives a dead session. Memory is never the source of truth.
2. **Each agent is context-isolated.** Worker, auditor, integration run as native subagents with fresh windows. Context rot can't accumulate, and one role can't quietly lean on another's reasoning.
3. **Acceptance criteria are runnable, not prose.** "Works correctly" is banned. Every criterion is a command with a checkable result (`pytest … exit 0`, `curl … 201`, `coverage ≥ 85`). If running it can't verify it, it isn't a criterion.
4. **Verification is independent and skeptical.** The auditor has no Write/Edit tools, re-executes every criterion itself, and treats "the worker said it works" as zero evidence. When in doubt → FAIL.
5. **Permissions are policy, enforced twice.** Each role's allowed tools are declared once (agent frontmatter) and backstopped by hooks. Read-only roles are read-only by construction, not by good intentions.

---

## Install

### Option A — via Claude Code plugin manager (recommended)

```bash
claude marketplace add github:pmrster/deep-build-harness
claude plugin install deep-build-harness@deep-build-harness
```

Claude Code clones the plugin, registers the hooks automatically, and sets `$CLAUDE_PLUGIN_ROOT` so hooks resolve correctly regardless of where the plugin is cached. Takes effect on next session start.

Verify it loaded:

```
/harness-doctor
```

You should see all checks pass: Claude CLI, hooks (present + executable), resolver, validator.

To update:

```bash
claude plugin update deep-build-harness@deep-build-harness
```

To remove:

```bash
claude plugin remove deep-build-harness@deep-build-harness
```

### Option B — local dev / per-project

Clone the repo anywhere, then symlink into Claude Code's plugin path:

```bash
git clone https://github.com/pmrster/deep-build-harness /path/to/deep-build-harness
ln -s /path/to/deep-build-harness ~/.claude/plugins/deep-build-harness
```

Validate the plugin structure:

```bash
claude plugin validate /path/to/deep-build-harness
```

With this approach, hooks use `${CLAUDE_PLUGIN_ROOT}` which Claude Code sets to the symlink target. Run `/harness-doctor` to confirm.

### Requirements

- **Claude Code** (any plan — Pro, Team, Free, Max, Enterprise)
- **Python 3** standard library — used by `orchestrator/resolver.py` and `hooks/post-tool-use.sh`; no third-party packages
- **pytest** — only needed to run the resolver's unit tests (`python3 -m pytest tests/`)
- Your target project must provide its own test / lint / type-check commands; the interviewer captures them into `context.md` and the worker/auditor run them

---

## How it works — the 8 phases

Each run is isolated under `state/runs/<run-id>/` (referred to as **RUN_DIR**), so multiple features or sessions in one repo never collide.

```text
                                  ┌──────────────┐
                                  │  USER: goal  │
                                  └──────┬───────┘
                                         ▼
┌─ PHASES 0–3 · interactive — you approve each gate ─────────── writes ────────────┐
│                                                                                   │
│  Phase 0  /harness-interview ─────────────────────────────▶  context.md          │
│              └─gate─ confidence ≥ 80 AND unknowns = 0 ? ──no──▶ keep interviewing │
│                                         │ approve                                 │
│  Phase 1  /harness-scan ──────────────────────────────────▶  codebase_map.md     │
│                                         │                                         │
│  Phase 2  /harness-architecture ──────────────────────────▶  architecture.md     │
│              └─gate─ approve ? ──no──▶ revise                                      │
│                                         │ approve                                 │
│  Phase 3  /harness-plan ──────────────────────────────────▶  plans.json          │
│              └─gate─ approve ? ──no──▶ revise                                      │
│                                         │ approve  →  plans.json LOCKED            │
└─────────────────────────────────────────│─────────────────────────────────────────┘
                                           ▼
┌─ PHASE 4 · /harness-work coordinator — automated build loop ──────────────────────┐
│                                                                                   │
│   resolver.py --waves  ──▶  order tasks into dependency waves                      │
│                                         │                                         │
│        ┌────────────────────────────────▼─────────────────────────────────┐      │
│        │  per wave:                                                         │      │
│        │   WORKERS  (parallel · 1 task each · TDD)                          │      │
│        │     write: source + work_logs/<task-id>.json + commits            │      │
│        │        │                                                          │      │
│        │        ▼                                                          │      │
│        │   AUDITORS (parallel · independent · NO Write/Edit)                │      │
│        │     re-run every acceptance criterion ─▶ audit_log.json           │      │
│        │        │                                                          │      │
│        │        ▼                                                          │      │
│        │   verdict ?                                                       │      │
│        │     ├─ FAIL ─▶ rework loop ── attempt < 3 ──▶ back to WORKERS      │      │
│        │     │                         attempt = 3 ──▶ [HITL] AskUserQ:     │      │
│        │     │                            retry / skip / abort              │      │
│        │     └─ verified ─▶ more waves? ──yes (deps gate next wave)──┐      │      │
│        └────────────────────────────────────────────────────────────┘      │      │
│                                          │ no more waves                    │      │
└──────────────────────────────────────────│────────────────────────────────────────┘
                                           ▼
   Phase 5  integration  ── end-to-end across tasks ──▶  integration_log.json
                                           │
                                           ▼
   Phase 7  /harness-docs  ── from real code ──▶  README / CHANGELOG / API docs
                                           │
                                           ▼
                          final gate: ALL tasks verified ? ──no──▶ rework loop
                                           │ yes
                                           ▼
   Phase 8  /harness-release  ──▶  release_proof/ + git tag  ──▶  SHIPPED

   Legend:  gate = decision you approve   ·   HITL = human-in-the-loop prompt
            arrows show the one file each phase writes for the next to read
```

Each phase writes one file; the next reads it. Agents never share memory — **files are the only channel.** Phases 0–3 and 7–8 are interactive skills you approve at a gate; phase 4 is the automated build loop.

### Phase 4 — the coordinator

`/harness-work` runs in your session and, per dependency wave:

1. Groups tasks into waves with `orchestrator/resolver.py --waves` (deterministic; stops on cycles / unknown deps)
2. Within each wave, dispatches **worker** subagents **in parallel** (one per task; each writes its own `work_logs/<task-id>.json`, so no shared-log contention)
3. Once all wave workers return, dispatches **auditor** subagents **in parallel** (re-runs every acceptance criterion itself, writes `audit_log.json`)
4. On FAIL runs a **rework loop** (max 3 attempts per task, then asks you: retry / skip / abort)
5. Gates the next wave: if any task in a wave is not verified, dependent waves are blocked
6. When all tasks are verified, runs an **integration** subagent end-to-end

The coordinator is the **sole writer of `plans.json`**. Workers and the auditor write only their own logs and return results. Runs are **resumable** — re-running skips already-verified tasks.

#### Phase 4 — parallel path (opt-in: `/harness-work-parallel`)

`/harness-work-parallel` is an opt-in alternative that drives the **parallel-safe** work through Claude Code's **dynamic Workflow tool** while keeping every shared singleton serial in the coordinator. It produces the same end state as `/harness-work` — same commits on the same branch, same `audit_log.json`, same verified tasks — and reuses the same worker and auditor subagents:

- **Build fan-out:** per wave, workers run in parallel as *write-only* (dispatched with `COMMIT_MODE: defer`); they edit their disjoint `files_expected` and write logs but do **not** commit. The coordinator then commits each task **serially** (one git writer → no index race).
- **Adversarial audit:** each task gets the canonical auditor (run **one at a time**, since it read-modify-writes the single `audit_log.json`) plus N read-only "refuter" agents that fan out in parallel and try to disprove the task passed — a `PASS` survives only if no refuter majority blocks it.
- **Singletons stay with the coordinator:** git commits, `plans.json` writes, and `state/.active_role` (set per phase, exactly like `/harness-work`). The Workflow script itself never touches them.

**When to use it:** worth it when a wave has roughly **3+ independent tasks** that each take real work — the build fan-out cuts wall-clock at the cost of higher parallel token use, and dynamic workflows ask you to confirm before running. For plans with 1–2 tasks per wave, or on a tight token budget, plain `/harness-work` is just as fast and cheaper. `/harness-work` remains the default and is unchanged; a user who never runs the parallel command sees identical behavior.

### Roles and permissions

| Agent | Can write | Purpose |
|---|---|---|
| worker | source, `work_logs/<task-id>.json`, commits | implement one task with TDD |
| auditor | `audit_log.json` only | independently verify; **no Write/Edit** |
| integration | `integration_log.json` only | end-to-end flows; **no Write/Edit** |

Each role has `model: inherit` by default, so it works on any plan. The coordinator picks a model per dispatch — least-powerful-that-fits, with the **auditor getting the most capable model available** (it's the quality lever) — and never fails a run if a preferred tier isn't on your plan.

For changes to existing or legacy code, the worker self-checks four **accuracy guardrails** before submitting — it changed only its assigned files, the neighboring code's existing tests still pass, it followed the codebase's conventions, and it didn't break a contract a caller depends on — and the auditor independently re-verifies all four before a task is verified.

Read-only roles are enforced twice: the agent's `tools` / `disallowedTools` frontmatter omits Write/Edit (authoritative), and a `PreToolUse` hook blocks them as a backstop (signalled by `state/.active_role`). A `PostToolUse` hook logs every Write/Edit to the run's `file_change_log.jsonl`. See `hooks/README.md`.

---

## Usage

Start in any folder — greenfield is fine. Use a git repo so workers can commit and the release phase can tag.

Works the same whether you are building something new or changing a big/existing/legacy repo, and you do not need to be a coder. The interview quietly inspects the project to detect the stack and test commands, asks you only plain-language questions (what you want, who it's for, what must not break), and proposes where the change should live — you just confirm. On a large repo the scan maps only that change area plus the code directly connected to it, so it scales with the size of your change, not the size of the repo.

```bash
mkdir my-app && cd my-app && git init
claude                       # the plugin loads automatically after install
```

Drive the pipeline from inside the session. You can pass your idea straight to the interview:

```
/harness-interview build a Python CLI todo app with add, list, and done commands
```

The interviewer asks until requirements are unambiguous, **creates a run** `state/runs/<run-id>/` (the id is a date + slug of your goal), writes its `context.md`, and records the id in `state/CURRENT`. Approve it, then run each phase as it prompts you:

```
/harness-scan            # maps existing code (marks greenfield if empty) → RUN_DIR/codebase_map.md
/harness-architecture    # schema + exact contracts → RUN_DIR/architecture.md   (you approve)
/harness-plan            # tasks with verifiable criteria → RUN_DIR/plans.json  (you approve → locks)
/harness-work            # builds each task: worker (TDD) → auditor, with rework loop
/harness-work-parallel   # opt-in alternative to /harness-work: parallel build + adversarial audit via the dynamic Workflow tool (higher token cost; confirm before use)
/harness-docs            # README/CHANGELOG/API from the real code
/harness-release         # final gate + git tag, only if every task is verified
```

Operational commands (any time):

```
/harness-status            # read-only: phase progress + per-task status table for the current run
/harness-runs [run-id]     # list runs with status; with an id, switch the active run (state/CURRENT)
/harness-rework <id> [why] # flip a task back to rework so /harness-work rebuilds it
/harness-audit <task-id>   # manually re-audit one task with the independent auditor
/harness-integration       # manually trigger integration tests after all tasks are verified
/harness-doctor            # environment check: Python, hooks, resolver, stale state
```

All phases in the same session reuse that run automatically; a fresh session falls back to `state/CURRENT`. Run a second, unrelated feature in the same repo by starting another `/harness-interview` — it gets its own isolated run dir. Inspect progress anytime: `cat state/runs/<run-id>/plans.json`, `cat state/runs/<run-id>/audit_log.json`, `git log`.

To start over, delete `state/` (it is gitignored), or delete a single `state/runs/<run-id>/`.

### Fast path for small changes

For a small bounded change — a bug fix, a tweak, a one-function addition — the full eight-phase pipeline is overkill. Use the fast path instead:

```
/harness-quick fix the off-by-one in resolver pagination
```

`/harness-quick` asks a couple of plain-language questions, confirms the change once, then runs the **same worker and independent auditor with the full accuracy guardrails** — it just skips the architecture document, multi-wave planning, and the long interview. If the change turns out to be large (new schema, new API, many files), it stops and tells you to run `/harness-interview` for the full pipeline instead. Quick runs are normal runs: they show up in `/harness-status` and `/harness-runs`.

### Which Claude Code permission mode to use

The harness writes files every phase (state, then real code), so the permission mode matters:

| Mode | Works? | Notes |
|---|---|---|
| **Normal / accept-edits** | ✅ best | Recommended for `/harness-work` — workers edit, commit, and write logs without a prompt on every step. |
| **Ask (default prompts)** | ✅ but noisy | Every worker Write/Edit/commit asks for permission. Fine for the interactive phases; tedious during the build loop. |
| **Plan mode** | ❌ not compatible | Plan mode blocks Write/Edit, so even `/harness-interview` can't write `context.md`. It is also redundant — the harness has its own planning phases (interview → architecture → plan). Don't wrap the harness in Plan mode. |

In short: run the interactive phases in any mode you like; run `/harness-work` in **normal/accept-edits**.

### Avoid mid-run stalls

The harness fires many tool calls (scan, tests, lint, git, the resolver). If one needs a permission you haven't granted — especially inside a subagent — the run can **hang waiting on a prompt that never gets answered**. Two ways to prevent it:

1. **Run `/harness-work` (and ideally the whole pipeline) in accept-edits mode** so edits don't prompt.
2. **Allowlist the read-only / expected commands** in the target project's `.claude/settings.json` (or your user settings). A safe starting set:

```json
{
  "permissions": {
    "allow": [
      "Bash(ls:*)", "Bash(cat:*)", "Bash(find:*)", "Bash(grep:*)",
      "Bash(git status:*)", "Bash(git ls-files:*)", "Bash(git diff:*)",
      "Bash(git log:*)", "Bash(git add:*)", "Bash(git commit:*)",
      "Bash(python3:*)", "Bash(pytest:*)", "Bash(coverage:*)",
      "Bash(npm test:*)", "Bash(ruff:*)", "Bash(eslint:*)", "Bash(mypy:*)"
    ]
  }
}
```

Trim it to your stack. Or generate one automatically from your own usage with the `/fewer-permission-prompts` helper.

If a run stalls on a prompt: press `Esc` to cancel, grant the permission (or add it above), and re-run the phase — every phase is resumable (it re-reads the run's state and skips finished work).

---

## State files

All per-run files live under `state/runs/<run-id>/`. A top-level `state/CURRENT` holds the latest run id (the default a fresh session falls back to). `state/.active_role` is a transient `"<role> <run-id>"` marker the coordinator sets per dispatch (the hook's role signal).

| File (under `state/runs/<run-id>/`) | Writer | Notes |
|---|---|---|
| `context.md` | interviewer | locked after your approval |
| `codebase_map.md` | scanner | |
| `architecture.md` | architect | locked after your approval |
| `plans.json` | coordinator | `locked: true` after you approve the plan |
| `work_logs/<task-id>.json` | workers (one file per task) | parallel-safe |
| `audit_log.json` | auditor | append-only, immutable entries |
| `integration_log.json` | integration | per run |
| `file_change_log.jsonl` | post-tool hook | append-only |

`state/` is created at runtime and gitignored. Each run is isolated, so concurrent runs in one repo never clobber each other.

---

## The quality lever

`calibration/audit-fail-examples.md` trains the auditor to treat specific patterns as hard failures (wrong response schema, coverage one point short, missing error handling, hardcoded secrets, tests-after-code, path mismatches, self-reported evidence). Out of the box, models grade LLM output leniently; **adding examples here is the primary way to raise output quality over time.**

Similarly, `calibration/interview-deep-examples.md` trains the interviewer to push back on vague answers ("production quality", "standard REST", "fast"). Add a pattern whenever you see the interview accept something it shouldn't.

---

## What uses Python (and why)

The harness is almost entirely prompt-driven (skills + agents). Python appears in exactly three places, all **stdlib-only** — no packages to install beyond Python 3 itself:

| Where | What | Why Python, not a prompt |
|---|---|---|
| `orchestrator/resolver.py` | Deterministic dependency ordering of plan tasks (topological sort) + cycle / unknown-dep / duplicate-id detection | Ordering is the one place a silent LLM mistake — running a task before its dependency — corrupts a whole run. Code makes it deterministic and unit-testable. |
| `hooks/post-tool-use.sh` | A one-line `python3 -c` parses the hook event JSON and builds the change-log entry | Parsing JSON with embedded paths in pure bash is fragile; `python3` stdlib `json` handles quotes and backslashes correctly. |
| `tests/test_resolver.py` | pytest unit tests for the resolver | The resolver is the only component with real logic, so it's the only thing worth a test suite. |

Everything else — the 8 phases, the coordinator loop, the role agents — is plain prompting over file-based state.

---

## When to use it

- Multi-step features where a wrong assumption or a broken interface is expensive.
- Work that must be genuinely *verified*, not "looks done."
- Long-running or team builds where durable, resumable, auditable state matters.

## When not to

- One-line fixes, throwaway scripts, exploration. The ceremony costs more than it saves — use `/harness-quick` or a plain agent.

---

## Extending and customizing

### Calibration (recommended)

Add examples to `calibration/audit-fail-examples.md` and `calibration/interview-deep-examples.md` whenever you find a new failure mode. This is the lowest-effort, highest-leverage way to improve quality over time.

### Adding a role or phase

- Skills live in `skills/<name>/SKILL.md` with YAML frontmatter.
- Commands live in `commands/<name>.md` with YAML frontmatter.
- Agents live in `agents/<name>.md` — the `tools:` and `disallowedTools:` frontmatter sets that role's permissions.
- Keep the invariants: agents write only their own files, the auditor never writes source, every acceptance criterion stays a runnable command, permissions are declared once and backstopped by hooks.

---

## Example output

[`examples/todo-cli/`](examples/todo-cli/) shows a complete run on a toy Python CLI project — the interview output ([`context.md`](examples/todo-cli/context.md)), the locked plan ([`plans.json`](examples/todo-cli/plans.json)), and the auditor's verdict for each task ([`audit_log.json`](examples/todo-cli/audit_log.json)). Real runs live under `state/runs/<run-id>/` and are gitignored.

---

## Development

```bash
python3 -m pytest tests/        # 108 tests across resolver, hooks, bash guard, active-role, validation, smoke
claude plugin validate .        # validate plugin structure
```

---

## Contributing

Bug reports and calibration examples are the most useful contributions right now. Open an issue with the failure mode and (if possible) a minimal reproducer. PRs that add calibration examples, fix hook edge cases, or improve the resolver are welcome; PRs that add new phases or change the state contract need a discussion first.

Please don't submit PRs that remove the auditor's independence, relax the "runnable AC only" rule, or allow agents to share context. Those are load-bearing invariants, not style preferences.

---

## License

MIT — see [LICENSE](LICENSE).
