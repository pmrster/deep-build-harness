#!/bin/bash
# Append every Write/Edit to the file-change log for auditor review. No role needed.
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
    FILE=$(printf '%s' "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tool_input',{}).get('file_path','unknown'))" 2>/dev/null)
    # .active_role holds "<role> <run-id>". Route the log into that run's dir when present.
    ROLE="unknown"; RUN=""
    [ -f state/.active_role ] && read -r ROLE RUN _ < state/.active_role
    if [ -n "$RUN" ] && [ -d "state/runs/$RUN" ]; then
        LOG="state/runs/$RUN/file_change_log.jsonl"
    else
        mkdir -p state; LOG="state/file_change_log.jsonl"
    fi
    # Build JSON with python so paths containing quotes/backslashes can't corrupt the log.
    ROLE="$ROLE" RUN="$RUN" TOOL="$TOOL" FILE="$FILE" python3 -c "import os,json,datetime; print(json.dumps({'role':os.environ['ROLE'],'run':os.environ['RUN'],'tool':os.environ['TOOL'],'file':os.environ['FILE'],'ts':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}))" >> "$LOG"
fi
exit 0
