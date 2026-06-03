---
name: harness-doctor
description: "Environment verification and recovery for the deep-build harness. Checks claude CLI, hooks, resolver, state dir, stale active_role, and current run. Clears a stale .active_role on request. Triggers on /harness-doctor."
---

# Harness Doctor

Verify the harness environment is healthy and recover common stuck states.

## Checks (run in order; report ✓ or ✗ for each)

### 1. claude CLI
```bash
claude --version
```
✓ if exit 0 and prints a version string.
✗ if missing or errors — tell user to install Claude Code CLI.

### 2. Plugin hooks
Check `hooks/hooks.json` exists and is valid JSON (locate via `$CLAUDE_PLUGIN_ROOT/hooks/hooks.json` or relative to the current directory). Check `hooks/pre-tool-use.sh`, `hooks/pre-tool-use-bash.sh`, and `hooks/post-tool-use.sh` all exist and are executable.
✓ if all present and executable.
✗ list which are missing or not executable.

### 3. Resolver
Run this exact bash command — it finds the resolver wherever the plugin is installed:
```bash
RESOLVER=$(find ~/.claude/plugins/cache -name "resolver.py" -path "*/orchestrator/*" 2>/dev/null | head -1); [ -z "$RESOLVER" ] && RESOLVER="orchestrator/resolver.py"; python3 "$RESOLVER" 2>&1 | head -1; echo "RESOLVER_PATH=$RESOLVER"
```
✓ if output contains the usage line (exit 4 is expected with no args).
✗ if "No such file" or import error — report the RESOLVER_PATH value.

### 4. Validator
Run this exact bash command:
```bash
VALIDATOR=$(find ~/.claude/plugins/cache -name "validate_plans.py" -path "*/orchestrator/*" 2>/dev/null | head -1); [ -z "$VALIDATOR" ] && VALIDATOR="orchestrator/validate_plans.py"; python3 "$VALIDATOR" 2>&1 | head -1; echo "VALIDATOR_PATH=$VALIDATOR"
```
✓ usage line, exit 4 is expected.
✗ if "No such file" — report the VALIDATOR_PATH value.

### 5. state/ directory
Check `state/` exists. If not: create it with `mkdir -p state/`.
✓ if exists (or just created).

### 6. Stale active_role
Check `state/.active_role`:
- Not present → ✓ "No stale role."
- Present → read the file directly (`<role> <run> <timestamp>`) — no script needed.
  - If age < 5 minutes AND a `/harness-work` run seems actively in progress → ✓ "Active role in use (recent)."
  - Otherwise → ✗ "Stale active role detected: `<content>` (age: <X>m). This blocks all Write/Edit operations."
    Use AskUserQuestion: "Clear the stale active role?" (Yes / No).
    If Yes: `rm state/.active_role` → report cleared.
    If No: instruct: "Run `rm state/.active_role` manually when the coordinator is no longer running."

### 7. Current run
Check `state/CURRENT`:
- Not present → "No active run. Run /harness-interview to start one."
- Present → read the run id, check `state/runs/<run-id>/plans.json`.
  Report: run id, whether plans.json exists, and if so: task count + how many verified.

## Output format

```
Deep Build Harness — Environment Check
────────────────────────────────────────
✓ claude CLI       v<version>
✓ hooks            all present and executable
✓ resolver         importable
✓ validator        importable
✓ state/           exists
⚠ active_role      "auditor run-1 2026-06-02T10:00:00Z" (age: 47m) → cleared
✓ current run      2026-06-01-todo-cli  (3/5 verified)
────────────────────────────────────────
Ready.
```

Use ⚠ for warnings (recovered), ✗ for errors (action required), ✓ for passing.

## Rules
- Never modify any source or state file except `state/.active_role` (only on explicit user confirmation in check 6) and `state/` creation (check 5).
- Report the raw output of failing commands so the user can diagnose.
