# Architect Calibration — Good vs Bad

The architect's output is implemented literally by workers. Vagueness here causes integration failures downstream. Hold every design decision to the GOOD column.

## API contract completeness (all error cases, not just happy path)
BAD:  `POST /api/users -> 201`
GOOD: `POST /api/users -> 201 {id, email, created_at}`
                       `-> 409 {error: "email_exists"}`
                       `-> 422 {error: "password_too_short"}`
Reason: workers implement exactly what is written; unlisted errors become unhandled 500s.

## Exact field names and types
BAD:  "returns the user object"
GOOD: `{id: uuid, email: str, created_at: iso8601}`
Reason: other tasks depend on exact field names; "the user" is not implementable.

## Schema constraints
BAD:  "users table with an email column"
GOOD: `email TEXT NOT NULL UNIQUE` (+ index if queried)
Reason: missing constraints surface as data bugs after release.

## File-structure specificity
BAD:  "put it in the users module"
GOOD: exact paths with a one-line purpose, e.g. `src/users/router.py — HTTP routes; src/users/service.py — business logic`.
Reason: ambiguous placement makes two workers create conflicting files.

## Ambiguity handling
BAD:  silently pick one of two valid designs and move on.
GOOD: present both with trade-offs and ask the user to choose.
Reason: a silent wrong choice is the most expensive class of error to unwind.

## Respect the codebase map
BAD:  invent a new error-handling/logging pattern.
GOOD: follow the convention already documented in codebase_map.md.
Reason: inconsistency with existing code breaks integration and review.
