import os, subprocess, sys
import pytest
from orchestrator.bash_guard import is_write_command

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Commands the read-only auditor/integration roles must be ALLOWED to run.
ALLOW = [
    "pytest -q",
    "ruff check .",
    "python3 -m mypy src",
    "git diff --name-only",
    "git log --oneline -5",
    "git status",
    "git show HEAD",
    "git ls-files",
    "cat src/foo.py",
    "grep -rn TODO .",
    "ls -la",
    "pytest tests/ 2>&1",
    "echo done > /dev/null",
    "python3 -c 'import x' 2>&1 | tail -5",
    "coverage report",
    # the read-only roles' own logs — they have no Write/Edit tool, so Bash append is legit
    "echo '{}' >> state/runs/r1/audit_log.json",
    "cat entry.json >> state/runs/r1/integration_log.json",
]

# Commands that mutate the working tree — must be BLOCKED for read-only roles.
BLOCK = [
    "echo malicious > src/foo.py",
    "cat a >> src/foo.py",
    "sed -i 's/a/b/' src/foo.py",
    "perl -i -pe 's/a/b/' f.py",
    "cp /tmp/x src/foo.py",
    "mv a.py b.py",
    "rm src/foo.py",
    "rm -rf build",
    "tee src/foo.py",
    "truncate -s 0 f.py",
    ": > f.py",
    "git checkout -- src/foo.py",
    "git commit -am wip",
    "git add .",
    "git reset --hard HEAD~1",
    "git restore src/foo.py",
    "git stash",
    "git apply patch.diff",
    "chmod +x script.sh",
    "mkdir newdir",
    "touch newfile",
    "pytest -q && echo ok > result.txt",
]


# Heredoc writes to an allowed log file. The body can hold arbitrary JSON —
# apostrophes, nested quotes, pipes, semicolons — which must NOT trip the guard,
# because the auditor/integration roles write their logs this way.
ALLOW_HEREDOC = [
    "cat > state/runs/r/audit_log.json <<'JSONEOF'\n"
    '{"entries":[{"task_id":"1.1","rework_ticket":"don\'t hardcode; it\'s wrong","verdict":"FAIL"}]}\n'
    "JSONEOF",
    "cat > state/runs/r/integration_log.json <<'JSONEOF'\n"
    '{"steps":[{"actual":"a|b; c","result":"pass"}]}\n'
    "JSONEOF",
    "cat > RUN_DIR/audit_log.json <<EOF\n{}\nEOF",
]

# Heredoc whose redirect target is a SOURCE file — body stripping must not let
# this slip through; the opener's redirect is still inspected and blocked.
BLOCK_HEREDOC = [
    "cat > src/main.py <<'EOF'\nprint('pwned')\nEOF",
    "rm -rf src/ > state/runs/r/audit_log.json",
]

# Read-only roles parse JSON via interpreter one-liners. The embedded quotes/;/|
# are foreign syntax and must NOT be parsed as shell (they were false-blocked as
# "unbalanced quotes" before the interpreter-code stripping).
ALLOW_INTERP = [
    'cat plans.json | python3 -c "import json,sys; print(json.load(sys.stdin)[\'tasks\'])"',
    'python3 -c "a = 1; b = 2; print(a)"',
    'echo "=== check ==="; git diff --stat; python3 -c "import json; print(json.load(open(\'f.json\')))"',
    "node -e \"JSON.parse(require('fs').readFileSync('package.json','utf8'))\"",
    "python3 -c 'd = {\"a\": 1}; print(d[\"a\"])'",
]

# A real write that follows the interpreter code (or is the interpreter's own
# redirect) must still be caught — stripping the code must not hide the redirect.
BLOCK_INTERP = [
    "python3 -c \"open('x','w').write('hi')\" > src/main.py",
    "node -e \"console.log(1)\" && rm -rf src",
]


@pytest.mark.parametrize("cmd", ALLOW + ALLOW_HEREDOC + ALLOW_INTERP)
def test_allowed_commands_pass(cmd):
    blocked, reason = is_write_command(cmd)
    assert not blocked, f"should allow: {cmd!r} (got: {reason})"


@pytest.mark.parametrize("cmd", BLOCK + BLOCK_HEREDOC + BLOCK_INTERP)
def test_write_commands_blocked(cmd):
    blocked, reason = is_write_command(cmd)
    assert blocked, f"should block: {cmd!r}"
    assert reason


def test_cli_block_exit_two():
    r = subprocess.run(
        [sys.executable, "orchestrator/bash_guard.py"],
        input="echo x > src/foo.py", cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 2


def test_cli_allow_exit_zero():
    r = subprocess.run(
        [sys.executable, "orchestrator/bash_guard.py"],
        input="pytest -q", cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0
