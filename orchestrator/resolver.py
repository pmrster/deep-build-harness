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


def resolve(plans: dict) -> list:
    """Return task ids in dependency order.

    Deterministic: among tasks whose dependencies are all satisfied,
    the lexicographically smallest id is emitted next.
    """
    tasks = plans.get("tasks", [])
    ids = [t["id"] for t in tasks]
    id_set = set(ids)
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
