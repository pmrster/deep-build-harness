# Auditor Calibration — Examples That Must Fail

Out of the box, Claude grades LLM output leniently. Treat each pattern below as a hard FAIL. Add new patterns here as new failure modes are discovered — this file is the primary lever for raising output quality.

## Wrong response schema
Criterion: "POST /api/users returns {id, email, created_at}".
Worker output: {user_id, email, timestamp}.
-> FAIL: field names must match architecture.md exactly; other tasks depend on them.

## Coverage threshold
Quality bar 85%, actual 84.9%.
-> FAIL: the threshold is a hard minimum, not an approximation.

## Missing error handling
A DB/network/IO call with no try/except (or equivalent) around it.
-> FAIL: an unhandled error becomes a 500 / crash. Always a blocker.

## Hardcoded secret
A literal that looks like a key/password/token in source.
-> FAIL: automatic blocker regardless of any other score. Must use config/env.

## Test written after code
Worker log says "implemented then wrote tests to verify".
-> FAIL: TDD requires the test to fail first, then implementation makes it pass.

## Integration mismatch
architecture.md says GET /api/users/:id; code implements GET /users/:id.
-> FAIL: path mismatch breaks every caller. Must match exactly.

## Self-reported evidence
Worker log says "tested manually, it works".
-> Not evidence. Run the actual command. If no automated check exists for the criterion: FAIL.
