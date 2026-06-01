import json, subprocess, sys
import pytest
from orchestrator.resolver import resolve, CycleError, UnknownDependencyError


def plans(tasks):
    return {"locked": True, "approved_at": None, "tasks": tasks}


def test_linear_chain_orders_dependencies_first():
    p = plans([
        {"id": "c", "depends_on": ["b"]},
        {"id": "b", "depends_on": ["a"]},
        {"id": "a", "depends_on": []},
    ])
    assert resolve(p) == ["a", "b", "c"]


def test_independent_tasks_sorted_by_id():
    p = plans([
        {"id": "2.2", "depends_on": []},
        {"id": "2.1", "depends_on": []},
        {"id": "1.1", "depends_on": []},
    ])
    assert resolve(p) == ["1.1", "2.1", "2.2"]


def test_diamond_dependencies():
    p = plans([
        {"id": "d", "depends_on": ["b", "c"]},
        {"id": "b", "depends_on": ["a"]},
        {"id": "c", "depends_on": ["a"]},
        {"id": "a", "depends_on": []},
    ])
    out = resolve(p)
    assert out[0] == "a"
    assert out[-1] == "d"
    assert set(out[1:3]) == {"b", "c"}
    assert out[1] == "b"
