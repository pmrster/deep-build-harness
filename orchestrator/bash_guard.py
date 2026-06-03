"""Detect whether a shell command would mutate the working tree.

Closes the gap where a read-only role (auditor/integration) — which has no
Write/Edit tool — could still edit source via Bash (`echo > f`, `sed -i`,
`git checkout`, ...). The Write|Edit PreToolUse hook never sees Bash, so this
module backs a dedicated Bash PreToolUse hook for those roles.

Conservative by design: when a role is read-only, a command that writes is
blocked even if it also does legitimate reads. Auditors report findings inline,
they do not need to write files. Test runners (pytest/ruff/mypy) and read-only
git are allowed; their incidental caches (.pyc, .coverage) are not source edits.
The role's own append-only log (audit_log.json / integration_log.json) is allowed.

Limitation (honest): this catches shell-level writes (redirection, common
mutating utils, mutating git). It does NOT catch a write smuggled through an
interpreter (e.g. `python3 -c "open('f','w')..."`). It is one layer of three —
the agent's tool set (no Write/Edit) and the role prompt are the others — not a
sandbox. It raises the bar from honor-system to "no common write slips through".

Usage (CLI): printf '%s' "<command>" | python3 orchestrator/bash_guard.py
Exit 0 = read-only (allow), 2 = writes (block, reason on stderr).
"""
import re
import shlex
import sys

# Program names that mutate the filesystem when invoked.
WRITE_CMDS = {
    "cp", "mv", "rm", "rmdir", "mkdir", "touch", "dd", "truncate", "install",
    "ln", "rsync", "tee", "shred", "chmod", "chown", "chgrp", "ed",
}
# git subcommands that change tracked files / the working tree or history.
GIT_WRITE_SUBCMDS = {
    "add", "commit", "checkout", "restore", "reset", "stash", "apply", "rm",
    "mv", "clean", "revert", "merge", "rebase", "cherry-pick", "push", "am",
}
# `<cmd> -i` (in-place) editors.
INPLACE_CMDS = {"sed", "perl", "gawk", "awk"}

_SEGMENT_SPLIT = re.compile(r"&&|\|\||\||;|\n")
# A redirection that writes to a file: > or >> with a target that is not a
# /dev/null and not an fd duplication (2>&1, >&2, &>).
_REDIR = re.compile(r"(?<![0-9&])>>?(?![&])\s*([^\s;|&<>]+)")
# A heredoc opener: <<DELIM, <<-DELIM, <<'DELIM', <<"DELIM".
_HEREDOC = re.compile(r"<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")


def _strip_heredoc_bodies(command):
    """Remove heredoc *bodies* (and the closing delimiter) so JSON/quotes inside
    a `cat > log <<'EOF' ... EOF` are never parsed as shell. The opener line is
    kept — that is what carries the redirect we still need to inspect. Without
    this, an apostrophe or unbalanced quote in a log payload trips shlex and the
    command is wrongly blocked, even though it only writes to an allowed target."""
    lines = command.split("\n")
    out = []
    i = 0
    while i < len(lines):
        out.append(lines[i])
        m = _HEREDOC.search(lines[i])
        if m:
            delim = m.group(2)
            i += 1
            while i < len(lines) and lines[i].strip() != delim:
                i += 1  # skip body
            # skip the closing delimiter line itself (if present)
        i += 1
    return "\n".join(out)

# The only files these read-only roles legitimately own and append to (they have
# no Write/Edit tool, so they must use Bash for their own log). Allow writes here.
ALLOWED_WRITE_TARGETS = ("audit_log.json", "integration_log.json")


def _target_allowed(target):
    return target == "/dev/null" or any(target.endswith(t) for t in ALLOWED_WRITE_TARGETS)


def _segment_writes(seg):
    seg = seg.strip()
    if not seg:
        return None

    # output redirection to a real file
    for m in _REDIR.finditer(seg):
        target = m.group(1)
        if target and not _target_allowed(target):
            return f"redirection writes to {target!r}"

    try:
        tokens = shlex.split(seg)
    except ValueError:
        # unbalanced quotes — can't reason; be safe and block
        return "uninterpretable command (unbalanced quotes)"
    if not tokens:
        return None

    # step past leading env-assignments (FOO=bar cmd ...)
    i = 0
    while i < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[i]):
        i += 1
    if i >= len(tokens):
        return None
    cmd = tokens[i].split("/")[-1]  # basename, so /bin/rm == rm
    rest = tokens[i + 1:]

    if cmd in WRITE_CMDS:
        return f"{cmd} mutates the filesystem"
    if cmd in INPLACE_CMDS and ("-i" in rest or any(a.startswith("-i") for a in rest)):
        return f"{cmd} -i edits files in place"
    if cmd == "git":
        sub = next((t for t in rest if not t.startswith("-")), None)
        if sub in GIT_WRITE_SUBCMDS:
            return f"git {sub} mutates the working tree or history"
    return None


def is_write_command(command):
    """Return (blocked: bool, reason: str). True if the command writes."""
    if not command or not command.strip():
        return False, ""
    command = _strip_heredoc_bodies(command)
    for seg in _SEGMENT_SPLIT.split(command):
        reason = _segment_writes(seg)
        if reason:
            return True, reason
    return False, ""


def main():
    command = sys.stdin.read()
    blocked, reason = is_write_command(command)
    if blocked:
        print(f"BLOCKED: read-only role cannot run a write command — {reason}.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
