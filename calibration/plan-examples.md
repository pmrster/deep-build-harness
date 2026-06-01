# Planner Calibration — Good vs Bad

Every acceptance criterion must be a command someone can run and check. Every task must own a disjoint set of files. Hold the plan to the GOOD column.

## Machine-verifiable acceptance criteria
BAD:  "the endpoint works correctly"
GOOD: `pytest tests/test_users.py::test_register_success returns exit code 0`
Reason: the auditor re-runs criteria; prose cannot be run.

## The criterion names a runnable command
BAD:  "the code is clean"
GOOD: `ruff check src/users returns exit code 0`
Reason: "clean" is unverifiable; a lint command is.

## File-ownership is disjoint
BAD:  task 2.1 and task 2.2 both list `src/users/service.py` in files_expected.
GOOD: each task owns different files; if they must share one, merge them into a single task.
Reason: two workers editing one file collide.

## Task granularity (one cohesive unit)
BAD:  one task: "build the whole user API".
GOOD: one task per endpoint/model/component, each with 2–5 criteria.
Reason: small tasks are independently buildable, testable, and auditable.

## Wave / dependency correctness
BAD:  a wave-1 task depends_on a wave-2 task.
GOOD: every dependency appears in an earlier (or equal-but-non-circular) position; dependents come after.
Reason: the resolver stops on a task whose dependency has not been built yet.

## Coverage criterion is exact
BAD:  "good test coverage"
GOOD: `coverage report --include=src/users/service.py shows >= 85%`
Reason: a threshold is a hard number the auditor checks; "good" is not.
