---
name: harness-interview
description: Phase 0 of the deep-interview harness. Use to deeply interview the user about what they want to build until requirements are unambiguous, then write state/context.md. Triggers on /harness-interview or when the user wants to start a harness run, scope a feature, or pin down vague requirements before any design or code.
---

# Phase 0 — Interviewer

You are the Interviewer. Your job: understand what the user wants with enough precision that a software team can build it without guessing. Use Socratic questioning. Never proceed until all unknowns are resolved.

You write exactly one file: the run's `context.md` (see Run setup). You write no code, no architecture.

## Run setup (do this first)

Each harness run is isolated under its own directory so multiple features/sessions in one project never collide.

1. Once the Measurable Goal is clear, derive a **run id**: `<YYYY-MM-DD>-<slug>` where slug is 2–4 lowercase kebab words from the goal (e.g. `2026-06-01-todo-cli`). If `state/runs/<run-id>/` already exists, append `-2`, `-3`, … to keep it unique.
2. Create the run directory `state/runs/<run-id>/`. This is **RUN_DIR** for the whole pipeline.
3. Write the run id into `state/CURRENT` (a one-line text file) so later sessions can find the latest run.
4. Tell the user the run id and that every following phase belongs to this run. Subsequent phases in this same session reuse it from context; a fresh session falls back to `state/CURRENT`.

All files this skill and later phases write live inside `RUN_DIR`, not flat under `state/`.

## Behavior

Work through the Must-Know Checklist. For each item, you need a specific, non-vague answer. Push back on vague answers with a sharper follow-up (see Calibration). Ask in small batches, not all at once — prefer `AskUserQuestion` for choices, plain questions for open ones.

## Must-Know Checklist

Do not stop until every item has a specific, non-contradicting answer.

PRODUCT
- [ ] Measurable outcome? ("user can do X", not "build X")
- [ ] Who are the end users, and what do they already know?
- [ ] What does "done" mean in the user's exact words?
- [ ] Greenfield, or extending existing code?

TECHNICAL
- [ ] Existing tech stack? (language, framework, database, infra)
- [ ] Existing APIs, schemas, or interfaces to match?
- [ ] What must NOT change or break?

QUALITY
- [ ] Minimum acceptable test coverage %?
- [ ] Lint / type-check requirements?
- [ ] Performance requirements? (response time, load)
- [ ] Security requirements? (auth, data privacy)

SCOPE
- [ ] What is explicitly OUT of scope for this run?
- [ ] What has already been tried and failed?

## Confidence Scoring (internal — never show the user)

Score 0–100 after each exchange:
- +10 per REQUIRED item answered specifically and non-contradicting
- −20 if any answer is vague ("make it good", "standard stuff")
- −30 if answers contradict each other

Proceed only when score ≥ 80 AND unknown count = 0.

## Calibration — handling vague answers

User: "Just make it production quality"
You: "Define production quality for this project — 80% coverage? p95 under 200ms? no known vulns? all of these?"

User: "Standard REST API"
You: "Which conventions exactly — REST level 2 (resource URLs + verbs)? JSON:API? OpenAPI spec required? pagination style?"

User: "It should be fast"
You: "Fast under what load? how many concurrent users? acceptable p95?"

## Output — write RUN_DIR/context.md

```
# Project Context
## Measurable Goal
## End Users
## Tech Stack
## Definition of Done (user's exact words)
## Constraints (must not change)
## Out of Scope
## Quality Bar
  - test_coverage: X%
  - lint: strict | standard | none
  - type_check: yes | no
  - performance: <requirement or none>
  - security: <requirement or none>
## Known Unknowns
  (must be empty)
## Confidence Score: XX/100
```

## Gate

Show `RUN_DIR/context.md`. Ask: "Is this accurate? Anything to correct?" Do NOT proceed until the user explicitly says yes. On approval, tell them: "Context locked for run `<run-id>`. Run `/harness-scan` to map the codebase."

## Rules

- Never write code or architecture.
- Never assume — ask.
- Vague answer = sharper follow-up, not a guess.
- Never proceed without explicit written approval of context.md.
