export const meta = {
  name: 'harness-build-parallel',
  description: 'Parallel write-only build + adversarial audit fan-out for one set of harness tasks. Driven by /harness-work-parallel. Never commits, never writes plans.json, never touches state/.active_role.',
  phases: [
    { title: 'Build' },
    { title: 'Audit' },
    { title: 'Refute' },
  ],
}

// ---------------------------------------------------------------------------
// Reusable orchestrator for the deep-build harness.
//
// This script is the PARALLEL-SAFE half of phase 4/6 only. It runs inside the
// Workflow tool, dispatched by the /harness-work-parallel command. The command
// (main conversation loop) remains the coordinator and keeps every harness
// singleton SERIAL: git commits, state/.active_role, and plans.json writes are
// all done by the command, NOT here. That is the whole reason this is safe to
// fan out — see CLAUDE.md "the conflict" analysis.
//
// Invariants this script upholds (so the sequential /harness-work path and its
// agents are never affected):
//   * Workers are dispatched with `COMMIT_MODE: defer` -> they write files +
//     their per-task work_log but DO NOT git commit. The command commits each
//     task serially after the build wave returns (single git writer, no race).
//   * It NEVER writes or reads state/.active_role. The canonical auditor is
//     constrained by its own tool frontmatter (no Write/Edit), so the global
//     role signal is unnecessary here; not using it = zero collision risk.
//   * It NEVER writes plans.json. The command owns every status transition.
//   * The canonical harness-auditor stays the SOLE writer of audit_log.json
//     (one per task). Adversarial refuters are read-only Explore voters that
//     write nothing and only return a structured verdict.
//
// Modes (selected by args.mode):
//   'build' -> parallel write-only workers for args.tasks
//   'audit' -> per task: canonical auditor (+ N read-only adversarial refuters)
//
// args shape:
//   { runDir: string,                // required, e.g. "state/runs/2026-06-01-todo-cli"
//     mode: 'build' | 'audit',        // default 'build'
//     tasks: [{ id: string, title?: string }],
//     refuters?: number,              // adversarial voters per task in audit mode (default 2; 0 disables)
//     workerAgent?, auditorAgent?,    // override plugin-scoped subagent ids
//     workerModel?, auditorModel?, refuterModel? }  // optional model overrides
// ---------------------------------------------------------------------------

const A = args || {}
const RUN_DIR = A.runDir
const MODE = A.mode || 'build'
const TASKS = Array.isArray(A.tasks) ? A.tasks : []
const REFUTERS = A.refuters == null ? 2 : A.refuters
const WORKER = A.workerAgent || 'deep-build-harness:harness-worker'
const AUDITOR = A.auditorAgent || 'deep-build-harness:harness-auditor'
// Refuters are a first-class read-only agent (disallowedTools: Write, Edit) so the
// write prohibition is authoritative tool policy, not just a prompt instruction.
const REFUTER = A.refuterAgent || 'deep-build-harness:harness-refuter'

if (!RUN_DIR) throw new Error('harness-build-parallel: args.runDir is required')
if (!TASKS.length) return { mode: MODE, runDir: RUN_DIR, results: [] }

const REFUTE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['blocking', 'evidence'],
  properties: {
    blocking: { type: 'boolean', description: 'true ONLY if you found a concrete, reproducible failure that should block the task' },
    criterion: { type: 'string', description: 'the acceptance criterion or quality bar that fails, if applicable' },
    evidence: { type: 'string', description: 'the command you ran and what you observed; or why you could not refute' },
  },
}

const title = (t) => t.title ? ` — ${t.title}` : ''

// --- BUILD: parallel write-only workers ------------------------------------
if (MODE === 'build') {
  phase('Build')
  log(`Build wave: ${TASKS.length} task(s) in parallel (write-only, deferred commit)`)
  const results = await parallel(TASKS.map((t) => () =>
    agent(
      [
        `You are dispatched as the harness Worker for the deep-build harness.`,
        `TASK_ID: ${t.id}`,
        `RUN_DIR: ${RUN_DIR}`,
        `COMMIT_MODE: defer`,
        ``,
        `Build ONLY task ${t.id}${title(t)} exactly per your agent instructions, architecture.md, and its acceptance_criteria in plans.json. Follow strict TDD and your accuracy self-check.`,
        `Because COMMIT_MODE is defer: do everything through writing RUN_DIR/work_logs/${t.id}.json, but DO NOT run git add or git commit — the coordinator commits after you return.`,
        `Return a concise summary: what you built, files changed, test/coverage results. Do not claim verification.`,
      ].join('\n'),
      { agentType: WORKER, label: `build:${t.id}`, phase: 'Build', model: A.workerModel },
    )
      .then((summary) => ({ id: t.id, ok: true, summary }))
      .catch((e) => ({ id: t.id, ok: false, error: String(e) })),
  ))
  return { mode: 'build', runDir: RUN_DIR, results }
}

// --- AUDIT: canonical auditor (SERIAL) + adversarial refuters (parallel) ----
if (MODE === 'audit') {
  // CRITICAL ordering constraint: every canonical harness-auditor performs a
  // read-modify-write on the SINGLE shared RUN_DIR/audit_log.json. Running them
  // concurrently is a lost-update race (last writer clobbers siblings' verdicts).
  // So canonical auditors run STRICTLY SEQUENTIALLY below. The refuters write
  // nothing, so they fan out fully in parallel first.

  // Phase 1 — refuters for ALL tasks, fully parallel (read-only Explore voters).
  phase('Refute')
  const refuteThunks = TASKS.flatMap((t) =>
    Array.from({ length: Math.max(0, REFUTERS) }, (_, i) => () =>
      agent(
        [
          `You are dispatched as the adversarial harness Refuter.`,
          `TASK_ID: ${t.id}`,
          `RUN_DIR: ${RUN_DIR}`,
          ``,
          `Try to REFUTE that task ${t.id}${title(t)} meets its acceptance_criteria, exactly per your agent instructions: re-run each criterion yourself (read-only) and hunt for a criterion that does not pass, coverage below quality_bar, a missing error case, an out-of-scope edit, a broken neighbor contract, hardcoded secrets, or tests written after code. Default to blocking=true ONLY with concrete reproducible evidence.`,
        ].join('\n'),
        { agentType: REFUTER, label: `refute:${t.id}#${i + 1}`, phase: 'Refute', model: A.refuterModel, schema: REFUTE_SCHEMA },
      )
        .then((v) => ({ taskId: t.id, v }))
        .catch(() => ({ taskId: t.id, v: null })),
    ),
  )
  const refuteRuns = await parallel(refuteThunks)
  const refutesByTask = {}
  for (const r of refuteRuns) {
    if (!r) continue
    ;(refutesByTask[r.taskId] = refutesByTask[r.taskId] || []).push(r.v)
  }

  // Phase 2 — canonical auditors, ONE AT A TIME (serialize the audit_log.json write).
  phase('Audit')
  log(`Audit wave: ${TASKS.length} task(s), canonical auditor serialized; ${REFUTERS} refuter(s) each`)
  const results = []
  for (const t of TASKS) {
    const canonical = await agent(
      [
        `You are dispatched as the independent harness Auditor.`,
        `TASK_ID: ${t.id}`,
        `RUN_DIR: ${RUN_DIR}`,
        ``,
        `Verify task ${t.id}${title(t)} exactly per your agent instructions: re-run every acceptance criterion yourself, run the quality + security scan and the accuracy guardrails, then append your immutable verdict entry to RUN_DIR/audit_log.json and return the verdict line.`,
      ].join('\n'),
      { agentType: AUDITOR, label: `audit:${t.id}`, phase: 'Audit', model: A.auditorModel },
    )
      .then((text) => ({ ok: true, text }))
      .catch((e) => ({ ok: false, text: '', error: String(e) }))

    const votes = (refutesByTask[t.id] || []).filter(Boolean)
    const blockingVotes = votes.filter((v) => v && v.blocking)
    results.push({
      id: t.id,
      canonical,                                   // coordinator reads audit_log.json as authoritative; this is the prose line
      refuter_count: votes.length,
      refuter_blocking: blockingVotes.length,
      refuter_majority_blocking: votes.length > 0 && blockingVotes.length * 2 > votes.length,
      refuter_findings: blockingVotes.map((v) => ({ criterion: v.criterion || null, evidence: v.evidence })),
    })
  }
  return { mode: 'audit', runDir: RUN_DIR, results }
}

throw new Error(`harness-build-parallel: unknown mode "${MODE}" (expected 'build' or 'audit')`)
