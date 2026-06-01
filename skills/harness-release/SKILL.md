---
name: harness-release
description: Phase 8 of the deep-build harness. Use only when every task in plans.json is verified to package the release — pre-flight gate, final test run, release proof, git tag. Triggers on /harness-release.
---

# Phase 8 — Release

You package the release. You run only when every task in plans.json is verified by the independent auditor.

## Run directory
Resolve RUN: use the run id established earlier in this session; if none, read `state/CURRENT`. RUN_DIR = `state/runs/<RUN>/`. All state files below live in RUN_DIR.

## Step 1 — Pre-flight gate
Read RUN_DIR/plans.json. Count tasks by status. If ANY task is not "verified": list them with their status, say "Cannot release. Run /harness-work to complete remaining tasks." Stop.

Read RUN_DIR/audit_log.json. Verify every task has a PASS entry. If any PASS entry is missing: "Audit log incomplete. Cannot release." Stop.

## Step 2 — Final test run
Run the full test suite (command from RUN_DIR/context.md / RUN_DIR/architecture.md). If any test fails: "Final test run failed. Cannot release." Stop — do not tag.

## Step 3 — Build release proof
Create RUN_DIR/release_proof/:

RELEASE_SUMMARY.md:
```
# Release Summary
Date: <timestamp>
## What Was Built
<paragraph from task titles>
## Requirements Met
<table: requirement from context.md | verified by task | auditor verdict>
## Quality Metrics
<table: task | coverage | lint | type check | audit verdict>
## Audit Trail
<reference to audit_log.json>
```

Copy into RUN_DIR/release_proof/: context.md, architecture.md, plans.json, audit_log.json, integration_log.json (all from RUN_DIR).

## Step 4 — Git tag
```
git add -A
git commit -m "release: all <N> tasks verified by independent auditor"
git tag release-$(date +%Y%m%d-%H%M%S)
```

## Step 5 — Done
Report:
```
Release complete.
<N> tasks implemented and verified.
Evidence in RUN_DIR/release_proof/
Git tag: release-<timestamp>
```

## Rules
- Never release with any task not "verified".
- Never release if the final test run fails.
- The release proof must reference the immutable audit_log.json entries.
