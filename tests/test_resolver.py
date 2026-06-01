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
