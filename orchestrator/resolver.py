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


def waves(plans: dict) -> list:
    """Return tasks grouped into dependency layers for parallel dispatch.

    Layer index = length of the longest dependency path to the task. All tasks
    in one returned wave have every dependency satisfied by earlier waves and
    none on each other, so they are safe to dispatch in parallel. Ids are sorted
    within each wave for determinism. Raises CycleError / UnknownDependencyError
    / DuplicateTaskIdError on bad input (validated via resolve()).
    """
    order = resolve(plans)  # also raises on cycle / unknown dep / dup id
    tasks = plans.get("tasks", [])
    deps = {t["id"]: list(t.get("depends_on", []) or []) for t in tasks}
    level = {}
    for tid in order:  # topological order guarantees deps are seen first
        level[tid] = 1 + max((level[d] for d in deps[tid]), default=-1)
    layers = {}
    for tid, lvl in level.items():
        layers.setdefault(lvl, []).append(tid)
    return [sorted(layers[lvl]) for lvl in sorted(layers)]


def main(argv: list) -> int:
    want_waves = "--waves" in argv[1:]
    args = [a for a in argv[1:] if a != "--waves"]
    if len(args) != 1:
        print("usage: resolver.py [--waves] <plans.json>", file=sys.stderr)
        return 4
    try:
        with open(args[0]) as fh:
            plans = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read plans: {e}", file=sys.stderr)
        return 4
    try:
        if want_waves:
            for wave in waves(plans):
                print(" ".join(wave))
        else:
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
