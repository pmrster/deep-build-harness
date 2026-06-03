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

### Option A — clone and symlink (recommended for now)

```bash
git clone https://github.com/pmrster/deep-build-harness ~/.claude/plugins/deep-build-harness
```

Claude Code loads plugins from `~/.claude/plugins/` automatically on next session start. Verify:

```
/plugin list
/agents
```

You should see `deep-build-harness` and its three agents (`harness-worker`, `harness-auditor`, `harness-integration`).

To remove:

```bash
rm -rf ~/.claude/plugins/deep-build-harness
```

### Option B — local dev / per-project

```bash
ln -s /path/to/deep-build-harness ~/.claude/skills/deep-build-harness
```

Validate without loading:

```bash
claude plugin validate /path/to/deep-build-harness
```

### Requirements

- **Claude Code** (any plan — Pro, Team, Free, Max, Enterprise)
- **Python 3** standard library — used by `orchestrator/resolver.py` and `hooks/post-tool-use.sh`; no third-party packages
- **pytest** — only needed to run the resolver's unit tests (`python3 -m pytest tests/`)
- Your target project must provide its own test / lint / type-check commands; the interviewer captures them into `context.md` and the worker/auditor run them

---

## How it works — the 8 phases

Each run is isolated under `state/runs/<run-id>/` (referred to as **RUN_DIR**), so multiple features or sessions in one repo never collide.

```
/harness-interview     Phase 0  → RUN_DIR/context.md              interview until unambiguous (creates the run)
/harness-scan          Phase 1  → RUN_DIR/codebase_map.md         map existing code first
/harness-architecture  Phase 2  → RUN_DIR/architecture.md         schema + exact API contracts
/harness-plan          Phase 3  → RUN_DIR/plans.json              tasks with machine-verifiable AC
/harness-work          Phase 4  → coordinator drives build per task (worker → auditor)
                       Phase 5  → RUN_DIR/integration_log.json    end-to-end across tasks
                       Phase 6  → RUN_DIR/audit_log.json          independent verdict per task
/harness-docs          Phase 7  → README / CHANGELOG / docs
/harness-release       Phase 8  → RUN_DIR/release_proof/ + git tag (only if all verified)
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
