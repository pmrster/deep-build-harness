// Deterministic execution test for workflows/harness-build-parallel.js.
//
// The Workflow tool runs the script by wrapping its body in an async function
// and injecting agent()/parallel()/pipeline()/log()/phase()/args. We replicate
// that here with MOCKS so we can assert the script's control flow and every
// harness contract without dispatching any live subagent:
//   * build mode -> one write-only worker per task, each told COMMIT_MODE: defer
//   * audit mode -> canonical auditor + N read-only Explore refuters, majority math
//   * the script performs NO I/O and never references state/.active_role
//
// Run: node tests/workflow_harness_smoke.mjs   (exit 0 = pass)

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const SCRIPT = path.join(HERE, '..', 'workflows', 'harness-build-parallel.js')
const SRC = fs.readFileSync(SCRIPT, 'utf8')

const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

// Build a fresh runnable from the real source for each scenario (so module-level
// const re-initializes per run). Strip the `export` so it is a plain statement.
function makeRun() {
  const body = SRC.replace('export const meta', 'const meta')
  return new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args', body)
}

const mockParallel = async (thunks) => Promise.all(thunks.map((t) => t()))
const mockPipeline = async () => {
  throw new Error('pipeline should not be used by this script')
}
const noop = () => {}

// --- tiny assert harness ---------------------------------------------------
let failures = 0
function check(name, cond, detail) {
  if (cond) {
    console.log(`  ok  - ${name}`)
  } else {
    failures++
    console.log(`  FAIL - ${name}${detail ? ` :: ${detail}` : ''}`)
  }
}
async function expectThrow(name, fn) {
  try {
    await fn()
    failures++
    console.log(`  FAIL - ${name} :: expected throw, got none`)
  } catch {
    console.log(`  ok  - ${name}`)
  }
}

// Records every agent() call and returns a controllable response.
function recorder(opts = {}) {
  const calls = []
  const { workerThrows = new Set(), canonicalVerdict = 'PASS', refuterBlocking = () => false } = opts
  const agent = async (prompt, o = {}) => {
    const call = { prompt, opts: o, type: o.agentType || null, label: o.label || null, schema: !!o.schema }
    calls.push(call)
    if (o.schema) {
      // refuter (Explore) -> structured vote
      const idx = calls.filter((c) => c.schema).length - 1
      return { blocking: refuterBlocking(call, idx), evidence: 'mock', criterion: 'AC1' }
    }
    if ((o.agentType || '').includes('worker')) {
      const id = (prompt.match(/TASK_ID: (\S+)/) || [])[1]
      if (workerThrows.has(id)) throw new Error(`worker ${id} blew up`)
      return `built ${id}`
    }
    if ((o.agentType || '').includes('auditor')) return canonicalVerdict
    return 'unexpected agent call'
  }
  return { agent, calls }
}

const RUN_DIR = 'state/runs/test-run'

console.log('static guards:')
// The script must perform NO file I/O — it only builds prompt strings and calls
// agent(). That is what keeps the singletons (git, plans.json, active_role) the
// coordinator's job alone. Mentions of those names live only in comments/prompts.
// Drop `//` comments and the meta `description:` string (both are prose, not code).
const codeOnly = SRC.split('\n')
  .map((l) => l.replace(/\/\/.*$/, ''))
  .filter((l) => !/^\s*description:/.test(l))
  .join('\n')
check('no filesystem/exec imports (does no I/O)', !/\b(require\(['"](fs|child_process)|from ['"]node:(fs|child_process)|execSync|spawnSync|writeFileSync)\b/.test(SRC))
check('state/.active_role never appears in executable code', !/active_role/.test(codeOnly))
check('meta block is present', /const meta = \{|export const meta = \{/.test(SRC))

console.log('\nbuild mode:')
{
  const { agent, calls } = recorder()
  const out = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, {
    runDir: RUN_DIR,
    mode: 'build',
    tasks: [{ id: '1.1', title: 'Alpha' }, { id: '1.2' }],
  })
  check('mode is build', out.mode === 'build')
  check('one result per task', out.results.length === 2, `got ${out.results.length}`)
  check('all results ok', out.results.every((r) => r.ok === true))
  check('exactly 2 agent calls', calls.length === 2, `got ${calls.length}`)
  check('every call dispatches the worker agent', calls.every((c) => c.type === 'deep-build-harness:harness-worker'))
  check('no auditor/refuter calls in build', !calls.some((c) => c.schema || (c.type || '').includes('auditor')))
  check('every worker prompt carries COMMIT_MODE: defer', calls.every((c) => c.prompt.includes('COMMIT_MODE: defer')))
  check('every worker prompt carries its TASK_ID', calls.some((c) => c.prompt.includes('TASK_ID: 1.1')) && calls.some((c) => c.prompt.includes('TASK_ID: 1.2')))
  check('every worker prompt carries RUN_DIR', calls.every((c) => c.prompt.includes(RUN_DIR)))
  check('worker prompts forbid git in deferred mode', calls.every((c) => /do NOT run git add or git commit/i.test(c.prompt)))
}

console.log('\nbuild mode — worker failure surfaces as ok:false:')
{
  const { agent } = recorder({ workerThrows: new Set(['1.2']) })
  const out = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, {
    runDir: RUN_DIR,
    mode: 'build',
    tasks: [{ id: '1.1' }, { id: '1.2' }],
  })
  const r12 = out.results.find((r) => r.id === '1.2')
  const r11 = out.results.find((r) => r.id === '1.1')
  check('failed worker -> ok:false with error', r12 && r12.ok === false && !!r12.error)
  check('sibling worker still ok', r11 && r11.ok === true)
}

console.log('\naudit mode — canonical + 2 refuters, both blocking -> majority:')
{
  const { agent, calls } = recorder({ canonicalVerdict: 'PASS', refuterBlocking: () => true })
  const out = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, {
    runDir: RUN_DIR,
    mode: 'audit',
    refuters: 2,
    tasks: [{ id: '2.1', title: 'Beta' }],
  })
  check('mode is audit', out.mode === 'audit')
  check('one result per task', out.results.length === 1)
  const refuterCalls = calls.filter((c) => c.schema)
  const canonicalCalls = calls.filter((c) => (c.type || '').includes('auditor'))
  check('exactly one canonical auditor dispatched', canonicalCalls.length === 1)
  check('canonical uses harness-auditor agent', canonicalCalls[0].type === 'deep-build-harness:harness-auditor')
  check('exactly 2 refuters dispatched', refuterCalls.length === 2, `got ${refuterCalls.length}`)
  check('refuters use the first-class read-only harness-refuter agent', refuterCalls.every((c) => c.type === 'deep-build-harness:harness-refuter'))
  check('refuters are schema-constrained', refuterCalls.every((c) => c.schema))
  check('refuter prompt reinforces read-only (authoritative ban is in the agent frontmatter)', refuterCalls.every((c) => /read-only/i.test(c.prompt)))
  check('refuter_count == 2', out.results[0].refuter_count === 2)
  check('majority blocking is true', out.results[0].refuter_majority_blocking === true)
  check('findings captured', out.results[0].refuter_findings.length === 2)
}

console.log('\naudit mode — 1 of 2 refuters blocking -> NOT majority:')
{
  let n = 0
  const { agent } = recorder({ refuterBlocking: () => n++ === 0 }) // first true, second false
  const out = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, {
    runDir: RUN_DIR,
    mode: 'audit',
    refuters: 2,
    tasks: [{ id: '2.1' }],
  })
  check('1/2 blocking is not a majority', out.results[0].refuter_majority_blocking === false)
  check('refuter_blocking count == 1', out.results[0].refuter_blocking === 1)
}

console.log('\naudit mode — refuters:0 disables the adversarial layer:')
{
  const { agent, calls } = recorder()
  const out = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, {
    runDir: RUN_DIR,
    mode: 'audit',
    refuters: 0,
    tasks: [{ id: '2.1' }],
  })
  check('no refuter (schema) calls', !calls.some((c) => c.schema))
  check('still one canonical auditor', calls.filter((c) => (c.type || '').includes('auditor')).length === 1)
  check('majority is false with zero refuters', out.results[0].refuter_majority_blocking === false)
}

console.log('\naudit mode — canonical auditors are SERIALIZED (no audit_log.json race):')
{
  // Regression guard for the critical lost-update race: the canonical auditor
  // read-modify-writes the single shared audit_log.json, so two must never run
  // at once. The mock canonical agent yields across microtasks; if the script
  // ever dispatches canonical auditors concurrently, inFlight exceeds 1.
  let inFlight = 0
  let maxInFlight = 0
  const calls = []
  const agent = async (prompt, o = {}) => {
    calls.push({ type: o.agentType || null, schema: !!o.schema })
    if (o.schema) return { blocking: false, evidence: 'mock' } // refuter: parallel is fine
    if ((o.agentType || '').includes('auditor')) {
      inFlight++
      maxInFlight = Math.max(maxInFlight, inFlight)
      for (let k = 0; k < 5; k++) await Promise.resolve() // yield, expose any overlap
      inFlight--
      return 'PASS'
    }
    return ''
  }
  const out = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, {
    runDir: RUN_DIR,
    mode: 'audit',
    refuters: 1,
    tasks: [{ id: '3.1' }, { id: '3.2' }, { id: '3.3' }],
  })
  check('one result per task (3)', out.results.length === 3)
  check('three canonical auditors dispatched', calls.filter((c) => (c.type || '').includes('auditor')).length === 3)
  check('canonical auditors never overlapped (maxInFlight === 1)', maxInFlight === 1, `maxInFlight=${maxInFlight}`)
}

console.log('\nedge cases:')
{
  const { agent } = recorder()
  const empty = await makeRun()(agent, mockParallel, mockPipeline, noop, noop, { runDir: RUN_DIR, mode: 'build', tasks: [] })
  check('empty task list -> empty results', Array.isArray(empty.results) && empty.results.length === 0)
}
await expectThrow('missing runDir throws', async () => {
  const { agent } = recorder()
  await makeRun()(agent, mockParallel, mockPipeline, noop, noop, { mode: 'build', tasks: [{ id: '1.1' }] })
})
await expectThrow('unknown mode throws', async () => {
  const { agent } = recorder()
  await makeRun()(agent, mockParallel, mockPipeline, noop, noop, { runDir: RUN_DIR, mode: 'nope', tasks: [{ id: '1.1' }] })
})

console.log(`\n${failures === 0 ? 'PASS' : 'FAIL'} — ${failures} failure(s)`)
process.exit(failures === 0 ? 0 : 1)
