#!/bin/bash
# Best-effort defense in depth: block Write/Edit while a read-only role is active.
# The active role is signalled by the coordinator via state/.active_role.
# Authoritative enforcement is the agent's tools: frontmatter; this is a backstop.
INPUT=$(cat)
ROLE_FILE="state/.active_role"
[ -f "$ROLE_FILE" ] || exit 0
# .active_role holds "<role> <run-id>"; take the role (first field).
read -r ROLE _REST < "$ROLE_FILE"
if [ "$ROLE" = "auditor" ] || [ "$ROLE" = "integration" ]; then
    TOOL=$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
    if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
        echo "BLOCKED: $ROLE role cannot write files." >&2
        exit 2
    fi
fi
exit 0
