#!/bin/bash
# Append every Write/Edit to the file-change log for auditor review. No role needed.
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
    FILE=$(printf '%s' "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tool_input',{}).get('file_path','unknown'))" 2>/dev/null)
    ROLE=$( [ -f state/.active_role ] && tr -d '[:space:]' < state/.active_role || echo "unknown" )
    mkdir -p state
    printf '{"role":"%s","tool":"%s","file":"%s","ts":"%s"}\n' \
        "$ROLE" "$TOOL" "$FILE" "$(date -u +%FT%TZ)" >> state/file_change_log.jsonl
fi
exit 0
