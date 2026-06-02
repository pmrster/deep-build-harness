# Interview Calibration — How to Push Back on Vague Answers

Add examples here when new failure modes appear in real usage. The interviewer skill reads this before starting; every pattern below sharpens follow-up questions.

---

## "Production quality" is not an answer

User: "Just make it production quality"
Wrong: Accept this and move on.
Right: "Production quality means different things. For this project, does that mean:
       (a) 80%+ test coverage, (b) response time under 200ms, (c) no known security
       vulnerabilities, or (d) all of the above? Please be specific."

---

## "Standard REST" is not an answer

User: "Build a standard REST API"
Wrong: Assume you know what that means.
Right: "Which REST conventions specifically — resource URLs with HTTP verbs (REST level 2)?
       JSON:API format? OpenAPI spec required? What pagination style? What auth method?"

---

## "Fast" is not a requirement

User: "It should be fast"
Wrong: Write "performance: good" in context.md.
Right: "Fast under what conditions? Specifically: how many concurrent users,
       and what is the acceptable p95 response time?"

---

## "Don't break anything" is not a constraint

User: "Don't break anything"
Wrong: Write this as a constraint.
Right: "Which specific features must keep working? Name the 3–5 most critical
       user flows that must pass after this change."

---

## Stack guessing after recon

Recon found: pyproject.toml with fastapi, pytest, ruff.
Wrong: Ask "what's your tech stack?"
Right: "I can see you're using FastAPI, pytest, and ruff. I'll use those.
       Is there a database? I see no ORM in the manifest — should I add one,
       or are you using raw SQL / SQLite?"

---

## "Simple" does not scope a feature

User: "I want a simple auth system"
Wrong: Start designing immediately.
Right: "Simple auth can mean many things — session cookies, JWT, OAuth, API keys.
       For your users (who are they?), which fits? And is this greenfield or adding
       to existing login code?"

---

## Non-answer to a binary choice

User (asked about test coverage): "Whatever is standard"
Wrong: Default to 80% silently.
Right: "I'll use 80% — that's a common floor for Python projects. Does that work,
       or do you want stricter / more relaxed?"
       (Derive the default, state it explicitly, require a yes/no. Not open-ended again.)

---

## Confidence score anti-patterns (internal)

These patterns must NOT raise the score; treat them as vague and push back:
- Phrases: "good enough", "best practices", "you know what I mean", "the usual way",
  "nothing special", "basic", "simple", "clean", "reasonable", "whatever works"
- Numeric non-answers: "around X", "maybe X", "approximately X" (require exact or a range with bounds)
- Deferred answers: "we'll figure it out later", "TBD", "to be decided" (push: decide now or mark as explicitly out of scope)
