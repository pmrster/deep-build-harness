# Principles & Concept

## The problem

A single agent asked to "build X" makes silent assumptions, designs as it types, marks its own work done, and loses the thread as context fills. The failure isn't capability — it's **discipline and verification**. Nobody forced it to pin requirements, nobody designed before coding, and the thing that graded the result was the same thing that wrote it.

## The core idea

**Simulate an expert software team as a set of isolated agents that communicate only through files, and put an independent skeptic between "done" and "shipped."**

Each role is a separate agent with its own fresh context and its own narrow tool permissions. No role inherits another's conversation. The only thing that crosses a boundary is a file on disk. One role in particular — the **auditor** — never writes source and never trusts a report; it re-runs every acceptance criterion itself and is calibrated to fail borderline work.

That's the whole bet: **rigor up front (interview → design → plan), isolation during work, and adversarial verification before release.**

## Five principles

1. **Files are the contract, not chat.** Every phase writes one file; the next reads it. State is durable, inspectable, and survives a dead session. Memory is never the source of truth.

2. **Each agent is context-isolated.** Worker, auditor, integration run as native subagents with fresh windows. Context rot can't accumulate, and one role can't quietly lean on another's reasoning.

3. **Acceptance criteria are runnable, not prose.** "Works correctly" is banned. Every criterion is a command with a checkable result (`pytest … exit 0`, `curl … 201`, `coverage ≥ 85`). If it can't be verified by running it, it isn't a criterion.

4. **Verification is independent and skeptical.** The auditor has no Write/Edit tools, re-executes every criterion itself, and treats "the worker said it works" as zero evidence. A calibration file (`calibration/audit-fail-examples.md`) teaches it to hard-fail the patterns LLMs grade leniently. When in doubt → FAIL.

5. **Permissions are policy, enforced twice.** Each role's allowed tools are declared once (agent frontmatter) and backstopped by hooks. The read-only roles are read-only by construction, not by good intentions.

## How it works (8 phases)

```
0 Interview     confidence-gated questions → context.md        (don't build the wrong thing)
1 Scan          map existing code          → codebase_map.md   (don't duplicate or break)
2 Architecture  exact schema + contracts   → architecture.md   (workers implement literally)
3 Plan          tasks + verifiable AC      → plans.json         (locked after you approve)
4 Work          coordinator → worker (TDD) then auditor, per task, with a rework loop
5 Integration   end-to-end across tasks    → integration_log.json
6 Audit         independent per-task verdict → audit_log.json   (immutable, evidence-based)
7 Docs          document what was built, not what was planned
8 Release       ship only when every task is auditor-verified  → release_proof/ + git tag
```

Phases 0–3 and 7–8 are interactive skills you gate. Phase 4 is driven by the **coordinator** skill: it orders tasks by dependency, dispatches a worker then an auditor per task, runs a rework loop (max 3 → it asks you what to do), then an integration pass. The coordinator is the single writer of `plans.json`; subagents only write their own append-only logs.

Each run is isolated under `state/runs/<run-id>/`, so multiple features or sessions in one repo never collide, and any run resumes after an interruption (verified tasks are skipped).

## Why a heavy process is the point

The ceremony is the value. The expensive failures in agent coding are *upstream* — wrong assumptions, inconsistent interfaces, unverified "done." Front-loading interview/scan/architecture kills the interface-mismatch class of bugs before a line is written. The independent auditor kills the "passes its own vibe check" class. Everything else (files, isolation, runnable criteria) exists to make those two guarantees real and resumable.

## Where it sits

Most Claude Code workflow tooling falls into two camps, and this harness deliberately goes past both:

- **Behavioral skill collections** — a toolbox of process skills (brainstorm, plan, TDD, review) the main agent invokes ad hoc. Flexible and broad, but nothing is *enforced*: the same agent that builds also grades, and discipline is opt-in per step.
- **Lightweight plan/work/ship loops** — keep a plan and work bounded to it with source-of-truth files. Good structure, but verification is usually a review step *adjacent to* the implementer, not an independent authority.

This harness goes further on three axes at once: front-loaded design rigor (confidence-gated **interview** → **scan** → **architecture** before planning), **machine-verifiable criteria** carried as data in a locked `plans.json`, and an **independent, read-only auditor** that re-runs every criterion itself rather than reviewing the implementer's word.

Our moat is the combination: **front-loaded design rigor + machine-verifiable criteria + an adversarial, evidence-only auditor.**

## When to use it

- Multi-step features where a wrong assumption or a broken interface is expensive.
- Work that must be genuinely *verified*, not "looks done."
- Long-running builds across sessions where durable, resumable state matters.

## When not to

- One-line fixes, throwaway scripts, exploration. The ceremony costs more than it saves. Use a plain agent.

## Non-negotiables (if you extend this)

- An agent writes only its own file(s); never hand state agent-to-agent in memory.
- The auditor never writes source and never accepts self-reported evidence.
- Every acceptance criterion stays a runnable command.
- Tool permissions remain declared once and enforced by hooks too.
- Calibration examples are how you raise quality over time — add to them when you find a new failure mode.
