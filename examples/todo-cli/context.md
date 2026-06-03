# Run context — 2026-06-01-todo-cli

## Goal

Build a Python CLI todo app. Users can add tasks, list all tasks, and mark tasks as done. Tasks persist across sessions in `~/.todo.json`. The tool is invoked as `todo`.

## Confirmed requirements

- `todo add "buy milk"` — appends a new task with auto-incremented id, prints `Added: [1] buy milk`
- `todo list` — prints all tasks, done tasks shown with strikethrough marker (`[x]`); empty list prints `No tasks.`
- `todo done <id>` — marks task done by id, prints `Done: [1] buy milk`; unknown id prints error and exits 1
- `todo done <id>` on already-done task is idempotent (exits 0, no error)
- Storage: `~/.todo.json`, JSON array of `{id, text, done}` objects; created on first write if absent
- No external dependencies beyond Python 3 stdlib; Click is allowed for CLI parsing

## Non-goals (explicitly out of scope)

- No edit/delete commands in this version
- No due dates, priorities, or tags
- No sync or sharing

## Stack detection

- Language: Python 3 (stdlib + Click)
- Test command: `pytest tests/ -q`
- Lint: `ruff check .`
- Type check: `mypy todo/ --strict`
- Packaging: `pyproject.toml` with `[project.scripts] todo = "todo.cli:main"`

## Test commands (captured for worker/auditor)

```
pytest tests/ -q
ruff check .
mypy todo/ --strict
```

## Confidence

100 — requirements are unambiguous, non-goals explicit, test commands confirmed, no unknowns.

## Approved

2026-06-01T09:14:22Z
