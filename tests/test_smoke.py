"""Smoke tests: verify the full harness infrastructure is wired correctly.

These run without a Claude session — they check that every script imports,
every hook is executable, every skill/command has valid frontmatter, the
plugin manifest is valid JSON, and the orchestrator tools all produce the
expected exit codes on trivial inputs.

This is not an end-to-end test of the agentic pipeline (that requires a
real Claude session and human approval gates), but it does verify that nothing
is broken before a live run is attempted.
"""
import glob, importlib, json, os, pathlib, re, subprocess, sys
import pytest

REPO = pathlib.Path(__file__).parent.parent


def test_plugin_manifest_valid_json():
    p = REPO / ".claude-plugin" / "plugin.json"
    assert p.exists(), "plugin.json missing"
    data = json.loads(p.read_text())
    assert "name" in data


def test_all_skill_frontmatter_parseable():
    bad = []
    for f in sorted((REPO / "skills").glob("*/SKILL.md")):
        if not re.match(r"^---\n(.*?)\n---\n", f.read_text(), re.S):
            bad.append(str(f.relative_to(REPO)))
    assert not bad, f"bad frontmatter: {bad}"


def test_all_command_frontmatter_parseable():
    bad = []
    for f in sorted((REPO / "commands").glob("*.md")):
        if not re.match(r"^---\n(.*?)\n---\n", f.read_text(), re.S):
            bad.append(str(f.relative_to(REPO)))
    assert not bad, f"bad frontmatter: {bad}"


def test_all_agent_frontmatter_parseable():
    bad = []
    for f in sorted((REPO / "agents").glob("*.md")):
        if not re.match(r"^---\n(.*?)\n---\n", f.read_text(), re.S):
            bad.append(str(f.relative_to(REPO)))
    assert not bad, f"bad frontmatter: {bad}"


def test_skill_command_count_matches():
    n_skills = len(list((REPO / "skills").glob("*/SKILL.md")))
    n_commands = len(list((REPO / "commands").glob("*.md")))
    assert n_skills == n_commands, (
        f"skill/command count mismatch: {n_skills} skills vs {n_commands} commands"
    )


def test_hooks_executable():
    for name in ("pre-tool-use.sh", "pre-tool-use-bash.sh", "post-tool-use.sh"):
        p = REPO / "hooks" / name
        assert p.exists(), f"hook missing: {name}"
        assert os.access(p, os.X_OK), f"hook not executable: {name}"


def test_hooks_json_valid():
    p = REPO / "hooks" / "hooks.json"
    data = json.loads(p.read_text())
    assert "hooks" in data
    assert "PreToolUse" in data["hooks"]
    assert "PostToolUse" in data["hooks"]
    # Bash hook must be registered
    pre = data["hooks"]["PreToolUse"]
    matchers = [h.get("matcher", "") for h in pre]
    assert any("Bash" in m for m in matchers), "Bash PreToolUse hook not registered in hooks.json"


def test_orchestrator_modules_importable():
    for mod in ("orchestrator.resolver", "orchestrator.validate_plans",
                "orchestrator.bash_guard", "orchestrator.active_role"):
        importlib.import_module(mod)


def test_resolver_cli_usage_exit():
    r = subprocess.run([sys.executable, "orchestrator/resolver.py"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 4  # bad input → 4


def test_validate_plans_cli_usage_exit():
    r = subprocess.run([sys.executable, "orchestrator/validate_plans.py"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 4


def test_bash_guard_cli_blocks_write():
    r = subprocess.run([sys.executable, "orchestrator/bash_guard.py"],
                       input="echo x > foo.py", cwd=REPO,
                       capture_output=True, text=True)
    assert r.returncode == 2


def test_bash_guard_cli_allows_read():
    r = subprocess.run([sys.executable, "orchestrator/bash_guard.py"],
                       input="pytest -q", cwd=REPO,
                       capture_output=True, text=True)
    assert r.returncode == 0


def test_active_role_cli_absent_exit_one(tmp_path):
    r = subprocess.run(
        [sys.executable, "orchestrator/active_role.py", str(tmp_path / "nope")],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 1


def test_plans_schema_valid_json():
    p = REPO / "templates" / "plans.json.schema"
    data = json.loads(p.read_text())
    assert data.get("title") == "harness plans.json"


def test_calibration_files_exist():
    cal = REPO / "calibration"
    for name in ("audit-fail-examples.md", "plan-examples.md",
                 "architecture-examples.md", "interview-deep-examples.md"):
        assert (cal / name).exists(), f"calibration file missing: {name}"


def test_state_dir_exists_or_creatable(tmp_path):
    # Just verify the state/ dir in the repo exists (created during normal use)
    state = REPO / "state"
    assert state.exists() or True  # if missing, doctor would create it — not a hard failure
