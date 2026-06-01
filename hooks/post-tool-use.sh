#!/bin/bash
# Append every Write/Edit to the file-change log for auditor review. No role needed.
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
    FILE=$(printf '%s' "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tool_input',{}).get('file_path','unknown'))" 2>/dev/null)
    ROLE=$( [ -f state/.active_role ] && tr -d '[:space:]' < state/.active_role || echo "unknown" )
    mkdir -p state
    # Build JSON with python so paths containing quotes/backslashes can't corrupt the log.
    ROLE="$ROLE" TOOL="$TOOL" FILE="$FILE" python3 -c "import os,json,datetime; print(json.dumps({'role':os.environ['ROLE'],'tool':os.environ['TOOL'],'file':os.environ['FILE'],'ts':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}))" >> state/file_change_log.jsonl
fi
exit 0
