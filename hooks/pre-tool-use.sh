#!/bin/bash
# Best-effort defense in depth: block Write/Edit while a read-only role is active.
# This hook is registered with matcher "Write|Edit", so if it fires the tool already
# IS Write or Edit — no need to parse the event JSON (pure bash, no python).
# The active role is signalled by the coordinator via state/.active_role ("<role> <run-id>").
# Authoritative enforcement is the agent's tools/disallowedTools frontmatter; this is a backstop.
cat >/dev/null   # drain stdin (the event JSON), unused
ROLE_FILE="state/.active_role"
[ -f "$ROLE_FILE" ] || exit 0
read -r ROLE _REST < "$ROLE_FILE"
if [ "$ROLE" = "auditor" ] || [ "$ROLE" = "integration" ]; then
    echo "BLOCKED: $ROLE role cannot write files." >&2
    exit 2
fi
exit 0
