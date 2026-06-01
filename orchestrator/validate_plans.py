"""Structural validation for harness plans.json.

Dependency-free (stdlib only) so it runs anywhere the plugin is installed.
Checks the rules templates/plans.json.schema expresses, PLUS the cross-task
rule a JSON schema cannot state: files_expected must not overlap between tasks.

Usage (CLI): python3 orchestrator/validate_plans.py state/runs/<id>/plans.json
Exit 0 valid, 4 bad input (unreadable/not JSON), 5 validation failed.
"""
import json
import sys

VALID_STATUS = {"pending", "in_progress", "submitted", "verified", "rework"}
TOP_REQUIRED = ("locked", "approved_at", "tasks")
TASK_REQUIRED = (
    "id", "title", "description", "wave",
    "files_expected", "acceptance_criteria", "quality_bar", "status",
)


class ValidationError(Exception):
    """Raised when plans.json violates the structural contract."""


def _check_task(t, idx, errors):
    where = f"task[{idx}]"
    if not isinstance(t, dict):
        errors.append(f"{where}: not an object")
        return
    tid = t.get("id", f"<{idx}>")
    for field in TASK_REQUIRED:
        if field not in t:
            errors.append(f"task {tid!r}: missing required field {field!r}")

    if "status" in t and t["status"] not in VALID_STATUS:
        errors.append(f"task {tid!r}: bad status {t['status']!r} (allowed: {sorted(VALID_STATUS)})")

    if "wave" in t and (not isinstance(t["wave"], bool)) and isinstance(t["wave"], int):
        if t["wave"] < 1:
            errors.append(f"task {tid!r}: wave must be >= 1, got {t['wave']}")
    elif "wave" in t:
        errors.append(f"task {tid!r}: wave must be an integer")

    ac = t.get("acceptance_criteria")
    if ac is not None:
        if not isinstance(ac, list):
            errors.append(f"task {tid!r}: acceptance_criteria must be a list")
        else:
            if not (2 <= len(ac) <= 5):
                errors.append(f"task {tid!r}: acceptance_criteria needs 2-5 items, got {len(ac)}")
            for c in ac:
                if not isinstance(c, str) or not c.strip():
                    errors.append(f"task {tid!r}: each acceptance criterion must be a non-empty string")
                    break

    fe = t.get("files_expected")
    if fe is not None:
        if not isinstance(fe, list) or not fe:
            errors.append(f"task {tid!r}: files_expected must be a non-empty list")
        elif not all(isinstance(f, str) and f.strip() for f in fe):
            errors.append(f"task {tid!r}: files_expected entries must be non-empty strings")


def validate(plans):
    """Validate a parsed plans.json dict. Raise ValidationError listing every problem."""
    errors = []
    if not isinstance(plans, dict):
        raise ValidationError("plans.json must be a JSON object")
    for field in TOP_REQUIRED:
        if field not in plans:
            errors.append(f"missing top-level field {field!r}")

    tasks = plans.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be a list")
        raise ValidationError("; ".join(errors))

    for idx, t in enumerate(tasks):
        _check_task(t, idx, errors)

    # cross-task rules (not expressible in JSON schema)
    ids = [t.get("id") for t in tasks if isinstance(t, dict)]
    dupes = sorted({i for i in ids if ids.count(i) > 1 and i is not None})
    if dupes:
        errors.append(f"duplicate task ids: {dupes}")

    id_set = set(ids)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for d in t.get("depends_on", []) or []:
            if d not in id_set:
                errors.append(f"task {t.get('id')!r}: depends_on unknown task {d!r}")

    owner = {}
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for f in t.get("files_expected", []) or []:
            if f in owner and owner[f] != t.get("id"):
                errors.append(f"files_expected overlap: {f!r} owned by both {owner[f]!r} and {t.get('id')!r}")
            else:
                owner[f] = t.get("id")

    if errors:
        raise ValidationError("; ".join(errors))


def main(argv):
    if len(argv) != 2:
        print("usage: validate_plans.py <plans.json>", file=sys.stderr)
        return 4
    try:
        with open(argv[1]) as fh:
            plans = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read plans: {e}", file=sys.stderr)
        return 4
    try:
        validate(plans)
    except ValidationError as e:
        print(f"plans.json invalid: {e}", file=sys.stderr)
        return 5
    print("plans.json valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
