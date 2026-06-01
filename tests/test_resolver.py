import json, os, subprocess, sys
import pytest
from orchestrator.resolver import (
    resolve, CycleError, UnknownDependencyError, DuplicateTaskIdError,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def plans(tasks):
    return {"locked": True, "approved_at": None, "tasks": tasks}


def test_empty_plan_returns_empty():
    assert resolve(plans([])) == []
    assert resolve({}) == []


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


def test_cycle_raises():
    p = plans([
        {"id": "a", "depends_on": ["b"]},
        {"id": "b", "depends_on": ["a"]},
    ])
    with pytest.raises(CycleError):
        resolve(p)


def test_unknown_dependency_raises():
    p = plans([
        {"id": "a", "depends_on": ["ghost"]},
    ])
    with pytest.raises(UnknownDependencyError):
        resolve(p)


def test_self_dependency_is_a_cycle():
    p = plans([{"id": "a", "depends_on": ["a"]}])
    with pytest.raises(CycleError):
        resolve(p)


def test_duplicate_ids_raise():
    p = plans([
        {"id": "a", "depends_on": []},
        {"id": "a", "depends_on": []},
    ])
    with pytest.raises(DuplicateTaskIdError):
        resolve(p)


def _run_cli(tmp_path, data):
    f = tmp_path / "plans.json"
    f.write_text(json.dumps(data))
    return subprocess.run(
        [sys.executable, "orchestrator/resolver.py", str(f)],
        cwd=REPO, capture_output=True, text=True,
    )


def test_cli_prints_order_exit_zero(tmp_path):
    r = _run_cli(tmp_path, plans([
        {"id": "b", "depends_on": ["a"]},
        {"id": "a", "depends_on": []},
    ]))
    assert r.returncode == 0
    assert r.stdout.split() == ["a", "b"]


def test_cli_cycle_exit_two(tmp_path):
    r = _run_cli(tmp_path, plans([
        {"id": "a", "depends_on": ["b"]},
        {"id": "b", "depends_on": ["a"]},
    ]))
    assert r.returncode == 2


def test_cli_unknown_dep_exit_three(tmp_path):
    r = _run_cli(tmp_path, plans([{"id": "a", "depends_on": ["ghost"]}]))
    assert r.returncode == 3
