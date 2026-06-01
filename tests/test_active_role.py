import json, os, subprocess, sys
from orchestrator.active_role import parse_role

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_parse_none_when_missing(tmp_path):
    assert parse_role(str(tmp_path / "nope")) is None


def test_parse_role_run_only(tmp_path):
    f = tmp_path / "r"
    f.write_text("auditor run-1\n")
    info = parse_role(str(f))
    assert info["role"] == "auditor"
    assert info["run"] == "run-1"
    assert info["ts"] is None
    assert info["age_seconds"] is None


def test_parse_with_timestamp_gives_age(tmp_path):
    f = tmp_path / "r"
    f.write_text("worker run-2 2026-06-02T00:00:00Z\n")
    info = parse_role(str(f))
    assert info["role"] == "worker"
    assert info["run"] == "run-2"
    assert info["ts"] == "2026-06-02T00:00:00Z"
    assert isinstance(info["age_seconds"], (int, float))


def test_parse_empty_file_is_none(tmp_path):
    f = tmp_path / "r"
    f.write_text("\n")
    assert parse_role(str(f)) is None


def test_cli_prints_json(tmp_path):
    f = tmp_path / "r"
    f.write_text("auditor run-1 2026-06-02T00:00:00Z\n")
    r = subprocess.run(
        [sys.executable, "orchestrator/active_role.py", str(f)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["role"] == "auditor"


def test_cli_absent_exit_one(tmp_path):
    r = subprocess.run(
        [sys.executable, "orchestrator/active_role.py", str(tmp_path / "nope")],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 1
