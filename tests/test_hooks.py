"""Tests for the shell hooks — the enforcement layer that was previously untested.

Each hook is invoked as a real subprocess with a temp working directory, so the
relative state/ paths the hooks use resolve into the tmp dir and never touch the
repo's own state/.
"""
import json, os, subprocess
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE = os.path.join(REPO, "hooks", "pre-tool-use.sh")
PRE_BASH = os.path.join(REPO, "hooks", "pre-tool-use-bash.sh")
POST = os.path.join(REPO, "hooks", "post-tool-use.sh")


def run_hook(script, event, cwd, role=None):
    state = cwd / "state"
    state.mkdir(exist_ok=True)
    role_file = state / ".active_role"
    if role is not None:
        role_file.write_text(role + "\n")
    elif role_file.exists():
        role_file.unlink()
    return subprocess.run(
        ["bash", script], input=json.dumps(event),
        cwd=str(cwd), capture_output=True, text=True,
    )


# ---- pre-tool-use.sh: block Write/Edit for read-only roles ----

@pytest.mark.parametrize("role", ["auditor", "integration"])
def test_pre_blocks_write_for_readonly_roles(tmp_path, role):
    r = run_hook(PRE, {"tool_name": "Write"}, tmp_path, role=f"{role} run-1")
    assert r.returncode == 2


def test_pre_allows_write_for_worker(tmp_path):
    r = run_hook(PRE, {"tool_name": "Write"}, tmp_path, role="worker run-1")
    assert r.returncode == 0


def test_pre_allows_when_no_active_role(tmp_path):
    r = run_hook(PRE, {"tool_name": "Write"}, tmp_path, role=None)
    assert r.returncode == 0


# ---- pre-tool-use-bash.sh: block mutating Bash for read-only roles ----

def test_pre_bash_blocks_write_command_for_auditor(tmp_path):
    r = run_hook(PRE_BASH, {"tool_name": "Bash", "tool_input": {"command": "echo x > foo.py"}},
                 tmp_path, role="auditor run-1")
    assert r.returncode == 2


def test_pre_bash_allows_read_command_for_auditor(tmp_path):
    r = run_hook(PRE_BASH, {"tool_name": "Bash", "tool_input": {"command": "pytest -q"}},
                 tmp_path, role="auditor run-1")
    assert r.returncode == 0


def test_pre_bash_ignores_worker(tmp_path):
    r = run_hook(PRE_BASH, {"tool_name": "Bash", "tool_input": {"command": "rm foo.py"}},
                 tmp_path, role="worker run-1")
    assert r.returncode == 0


# ---- post-tool-use.sh: append change log ----

def test_post_logs_write_to_run_dir(tmp_path):
    (tmp_path / "state" / "runs" / "run-1").mkdir(parents=True)
    run_hook(POST, {"tool_name": "Write", "tool_input": {"file_path": "src/a.py"}},
             tmp_path, role="worker run-1")
    log = tmp_path / "state" / "runs" / "run-1" / "file_change_log.jsonl"
    assert log.exists()
    entry = json.loads(log.read_text().strip())
    assert entry["tool"] == "Write"
    assert entry["file"] == "src/a.py"
    assert entry["role"] == "worker"
    assert entry["run"] == "run-1"
    assert entry["ts"].endswith("Z")


def test_post_falls_back_to_flat_log_without_run(tmp_path):
    run_hook(POST, {"tool_name": "Edit", "tool_input": {"file_path": "src/b.py"}},
             tmp_path, role=None)
    log = tmp_path / "state" / "file_change_log.jsonl"
    assert log.exists()
    assert json.loads(log.read_text().strip())["file"] == "src/b.py"


def test_post_ignores_non_write_tools(tmp_path):
    (tmp_path / "state" / "runs" / "run-1").mkdir(parents=True)
    run_hook(POST, {"tool_name": "Bash", "tool_input": {"command": "ls"}},
             tmp_path, role="worker run-1")
    assert not (tmp_path / "state" / "runs" / "run-1" / "file_change_log.jsonl").exists()
    assert not (tmp_path / "state" / "file_change_log.jsonl").exists()


def test_post_handles_path_with_quotes_safely(tmp_path):
    (tmp_path / "state" / "runs" / "run-1").mkdir(parents=True)
    weird = 'src/we"ird.py'
    run_hook(POST, {"tool_name": "Write", "tool_input": {"file_path": weird}},
             tmp_path, role="worker run-1")
    log = tmp_path / "state" / "runs" / "run-1" / "file_change_log.jsonl"
    assert json.loads(log.read_text().strip())["file"] == weird
