#!/bin/bash
# Defense in depth for the read-only roles. The Write|Edit hook never fires on
# Bash, so a role with no Write/Edit tool (auditor/integration) could still edit
# source via `echo > f`, `sed -i`, `git checkout`, etc. This hook screens Bash
# for those roles and blocks any command that would mutate the working tree.
# Registered with matcher "Bash", so the tool already IS Bash when we fire.
INPUT=$(cat)
ROLE_FILE="state/.active_role"
[ -f "$ROLE_FILE" ] || exit 0
read -r ROLE _REST < "$ROLE_FILE"
case "$ROLE" in
    auditor|integration) ;;
    *) exit 0 ;;   # workers/coordinator run freely
esac

# Locate the guard relative to this script (works with or without CLAUDE_PLUGIN_ROOT).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD="$DIR/orchestrator/bash_guard.py"
[ -f "$GUARD" ] || exit 0   # fail open if the guard is missing; tools frontmatter still applies

CMD=$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)
[ -n "$CMD" ] || exit 0

printf '%s' "$CMD" | python3 "$GUARD"
exit $?
