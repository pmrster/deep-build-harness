# Hooks

Two small hooks enforce and record the harness's read-only roles. They are a **backstop**, not the primary control — see "Two-layer enforcement" below.

## What each hook does

| Hook | Event (matcher `Write|Edit`) | Job |
|---|---|---|
| `pre-tool-use.sh` | `PreToolUse` | Block `Write`/`Edit` while a read-only role (auditor/integration) is active. Exit `2` blocks the tool call. |
| `post-tool-use.sh` | `PostToolUse` | Append every `Write`/`Edit` to the active run's `file_change_log.jsonl` for the auditor to review. |

Wired in `hooks.json`, registered from the plugin manifest. Paths use `"${CLAUDE_PLUGIN_ROOT}"` (quoted, to survive spaces).

## The `.active_role` contract

The coordinator (`harness-work`) signals the current role by writing one line to `state/.active_role`:

```
<role> <run-id>
```

e.g. `auditor 2026-06-01-todo-cli`. The coordinator sets it **before** each subagent dispatch and deletes it **after**.

- `pre-tool-use.sh` reads the **first field** (role). If it's `auditor` or `integration` and the tool is `Write`/`Edit`, it blocks.
- `post-tool-use.sh` reads role **and** run-id, and routes the log line into `state/runs/<run-id>/file_change_log.jsonl` (falls back to `state/file_change_log.jsonl` if no run-id).

If `.active_role` is absent (e.g. the coordinator isn't running), both hooks no-op for blocking — normal editing is never impeded.

## Two-layer enforcement (read this before "fixing" the hook)

1. **Authoritative:** the auditor/integration agents declare `tools: Read, Bash, Glob, Grep` and `disallowedTools: Write, Edit` in their frontmatter. The subagent **cannot** call Write/Edit at all. This holds regardless of hooks, CWD, or `python3`.
2. **Best-effort backstop:** `pre-tool-use.sh`. It strengthens (1) but is allowed to degrade — under truly simultaneous runs the single `.active_role` marker can't always attribute the actor, and the relative path only resolves when CWD is the project root.

So the hook **failing open is acceptable by design.** Do not add brittle logic to make the hook authoritative; if you need stronger guarantees, tighten the agent frontmatter, not the hook.

## Known, intentional behaviors

- **Relative `state/.active_role`** — only resolves when the session CWD is the project root. By design (the harness runs from the project root).
- **`python3` only in `post-tool-use.sh`** — it uses stdlib `json` to parse the event and build the log line safely. `pre-tool-use.sh` needs no parsing (the `Write|Edit` matcher guarantees the tool) and is pure bash. If `python3` is missing, the post-hook log line is skipped; blocking (the pre-hook) is unaffected.
- **Bash-redirect writes aren't captured** — the auditor writes `audit_log.json` via a shell redirect, not the Write tool, so it does not appear in `file_change_log.jsonl`. A `PostToolUse` hook on `Write|Edit` cannot see shell redirection. Expected.

## Checklist for adding or editing a hook

- [ ] Shebang present (`#!/bin/bash`).
- [ ] Executable bit committed — `chmod +x` then verify `git ls-files -s hooks/` shows `100755`. (A non-exec hook fails silently.)
- [ ] Reads stdin once (`INPUT=$(cat)`); parses the event JSON defensively (`2>/dev/null`, sensible default).
- [ ] Correct exit code: `PreToolUse` returns `2` to **block**, `0` to allow; never block from a `PostToolUse` hook.
- [ ] Fails **open** — a hook error must not wedge the session. Authoritative control belongs in agent frontmatter, not here.
- [ ] No unquoted expansion of file paths into JSON (build JSON with `python3 -c "json.dumps(...)"`, never `printf` raw paths).
- [ ] Tested locally by piping a sample event:
      `echo '{"tool_name":"Write","tool_input":{"file_path":"x"}}' | bash hooks/pre-tool-use.sh; echo $?`
- [ ] If it depends on run state, honor the `state/.active_role` = `"<role> <run-id>"` contract and the `state/runs/<id>/` layout.
