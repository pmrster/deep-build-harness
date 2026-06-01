"""Deterministic dependency ordering for harness plans.json.

Usage (CLI): python3 orchestrator/resolver.py state/plans.json
Prints task ids in dependency order, one per line.
Exit 0 on success, 2 on cycle, 3 on unknown dependency, 4 on bad input.
"""
import json
import sys


class CycleError(Exception):
    """Raised when tasks form a dependency cycle."""


class UnknownDependencyError(Exception):
    """Raised when a depends_on references an unknown task id."""


class DuplicateTaskIdError(ValueError):
    """Raised when two tasks share the same id."""


def resolve(plans: dict) -> list:
    """Return task ids in dependency order.

    Deterministic: among tasks whose dependencies are all satisfied,
    the lexicographically smallest id is emitted next.
    """
    tasks = plans.get("tasks", [])
    ids = [t["id"] for t in tasks]
    id_set = set(ids)
    if len(ids) != len(id_set):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise DuplicateTaskIdError(f"duplicate task ids: {dupes}")
    deps = {t["id"]: list(t.get("depends_on", []) or []) for t in tasks}

    for tid, dlist in deps.items():
        for d in dlist:
            if d not in id_set:
                raise UnknownDependencyError(
                    f"task {tid!r} depends on unknown task {d!r}"
                )

    resolved = []
    satisfied = set()
    remaining = set(ids)
    while remaining:
        ready = sorted(
            t for t in remaining if all(d in satisfied for d in deps[t])
        )
        if not ready:
            raise CycleError(f"dependency cycle among: {sorted(remaining)}")
        nxt = ready[0]
        resolved.append(nxt)
        satisfied.add(nxt)
        remaining.discard(nxt)
    return resolved


def main(argv: list) -> int:
    if len(argv) != 2:
        print("usage: resolver.py <plans.json>", file=sys.stderr)
        return 4
    try:
        with open(argv[1]) as fh:
            plans = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read plans: {e}", file=sys.stderr)
        return 4
    try:
        for tid in resolve(plans):
            print(tid)
    except CycleError as e:
        print(str(e), file=sys.stderr)
        return 2
    except UnknownDependencyError as e:
        print(str(e), file=sys.stderr)
        return 3
    except DuplicateTaskIdError as e:
        print(str(e), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
