"""Read the transient coordinator role signal (state/.active_role).

The signal is a SINGLE global file by necessity: PreToolUse/PostToolUse hooks
fire for every tool call in the repo and have no way to know which run or
subagent triggered them, so the active role cannot be keyed per-run — the hook
would not know which key to read. Consequence: only one /harness-work coordinator
may be active in a repo at a time. This is a real constraint, not full isolation.

Format: "<role> <run-id> [<iso8601-utc-timestamp>]". The timestamp lets tooling
detect a STALE signal left by a crashed coordinator (which otherwise wedges the
repo: a leftover "auditor" role blocks all Write/Edit until cleared).

Usage (CLI): python3 orchestrator/active_role.py [state/.active_role]
Prints JSON {role,run,ts,age_seconds}; exit 0 if present, 1 if absent/empty.
"""
import datetime
import json
import sys

DEFAULT_PATH = "state/.active_role"


def parse_role(path=DEFAULT_PATH):
    """Return {role, run, ts, age_seconds} or None if absent/empty."""
    try:
        with open(path) as fh:
            line = fh.readline().strip()
    except OSError:
        return None
    if not line:
        return None
    parts = line.split()
    role = parts[0]
    run = parts[1] if len(parts) > 1 else None
    ts = parts[2] if len(parts) > 2 else None
    age = None
    if ts:
        try:
            when = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.timezone.utc)
            age = (now - when).total_seconds()
        except ValueError:
            age = None
    return {"role": role, "run": run, "ts": ts, "age_seconds": age}


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT_PATH
    info = parse_role(path)
    if info is None:
        return 1
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
