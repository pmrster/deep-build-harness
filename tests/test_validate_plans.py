import json, os, subprocess, sys
import pytest
from orchestrator.validate_plans import validate, ValidationError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def task(tid, **kw):
    base = {
        "id": tid,
        "title": f"task {tid}",
        "description": "do the thing",
        "wave": 1,
        "files_expected": [f"src/{tid}.py"],
        "acceptance_criteria": ["pytest -q", "ruff check ."],
        "quality_bar": {"test_coverage": 85},
        "status": "pending",
    }
    base.update(kw)
    return base


def plans(tasks, **kw):
    p = {"locked": True, "approved_at": None, "tasks": tasks}
    p.update(kw)
    return p


def test_valid_plan_passes():
    validate(plans([task("1.1"), task("1.2")]))  # no raise


def test_missing_top_level_field_raises():
    p = plans([task("1.1")])
    del p["tasks"]
    with pytest.raises(ValidationError):
        validate(p)


def test_missing_task_field_raises():
    t = task("1.1")
    del t["acceptance_criteria"]
    with pytest.raises(ValidationError):
        validate(plans([t]))


def test_bad_status_enum_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", status="done")]))


def test_too_few_acceptance_criteria_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", acceptance_criteria=["only one"])]))


def test_too_many_acceptance_criteria_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", acceptance_criteria=["a", "b", "c", "d", "e", "f"])]))


def test_empty_acceptance_criterion_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", acceptance_criteria=["pytest -q", "   "])]))


def test_wave_below_one_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", wave=0)]))


def test_files_expected_overlap_across_tasks_raises():
    a = task("1.1", files_expected=["src/shared.py"])
    b = task("1.2", files_expected=["src/shared.py"])
    with pytest.raises(ValidationError):
        validate(plans([a, b]))


def test_empty_files_expected_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", files_expected=[])]))


def test_duplicate_ids_raise():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1"), task("1.1")]))


def test_unknown_dependency_raises():
    with pytest.raises(ValidationError):
        validate(plans([task("1.1", depends_on=["ghost"])]))


def _run_cli(tmp_path, data):
    f = tmp_path / "plans.json"
    f.write_text(json.dumps(data))
    return subprocess.run(
        [sys.executable, "orchestrator/validate_plans.py", str(f)],
        cwd=REPO, capture_output=True, text=True,
    )


def test_cli_valid_exit_zero(tmp_path):
    r = _run_cli(tmp_path, plans([task("1.1")]))
    assert r.returncode == 0


def test_cli_invalid_exit_five(tmp_path):
    r = _run_cli(tmp_path, plans([task("1.1", status="bogus")]))
    assert r.returncode == 5


def test_cli_bad_json_exit_four(tmp_path):
    f = tmp_path / "plans.json"
    f.write_text("{not json")
    r = subprocess.run(
        [sys.executable, "orchestrator/validate_plans.py", str(f)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 4
