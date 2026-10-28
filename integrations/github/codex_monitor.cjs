// Active-only deterministic reconciliation. No model, budget renewal or cron dependency.
const {controller} = require('./codex_continuity.cjs');

const ACTIVE = new Set(['pending', 'dispatching', 'queued', 'initializing', 'running', 'retry', 'unconfirmed']);
const STOPPED = new Set(['review', 'complete', 'blocked']);

function needed(state) {
  if (!state || !Array.isArray(state.records)) throw Error('Invalid monitor state');
  return state.records.some(record => {
    if (!record || typeof record.status !== 'string') throw Error('Invalid monitor record');
    if (ACTIVE.has(record.status)) return true;
    if (STOPPED.has(record.status)) return false;
    if (record.status !== 'paused') throw Error('Unknown monitor record status');
    const history = record.history || [];
    if (!Array.isArray(history)) throw Error('Invalid paused attempt history');
    return Boolean(record.request_id && !history.some(item => item.request_id === record.request_id));
  });
}

async function monitor({github, context, root = process.cwd(), worker = 'codex-task.yml', contractPaths,
  intervalMs = 300000, maxTicks = 13, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  now = Date.now, control = controller, log = console.log}) {
  if (!Number.isSafeInteger(intervalMs) || intervalMs < 1 || intervalMs > 300000
      || !Number.isSafeInteger(maxTicks) || maxTicks < 1 || maxTicks > 13)
    throw Error('Monitor bounds exceed thirteen ticks at five-minute intervals');
  const repo = context.repo, branch = context.payload.repository.default_branch;
  if (!repo?.owner || !repo?.repo || typeof branch !== 'string' || !branch) throw Error('Missing monitor repository/default branch');
  let state;
  for (let ticks = 1; ticks <= maxTicks; ticks += 1) {
    state = await control({github, context, root, worker, contractPaths, now: now()});
    const active = state.records.filter(record => needed({records: [record]})).length;
    log(`codex-monitor: tick=${ticks}/${maxTicks} active=${active}`);
    if (!active) return {state, ticks, handoff: false};
    if (ticks < maxTicks) await sleep(intervalMs);
  }
  // Exactly one attempt. A lost/ambiguous dispatch response must never be retried here.
  await github.rest.actions.createWorkflowDispatch({...repo, workflow_id: 'codex-monitor.yml',
    ref: branch, inputs: {}});
  return {state, ticks: maxTicks, handoff: true};
}

module.exports = {needed, monitor};
