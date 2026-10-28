const test = require('node:test');
const assert = require('node:assert/strict');
const {needed, monitor} = require('./codex_monitor.cjs');

const state = status => ({schema: 1, records: status ? [{id: '42', status, history: []}] : []});
function fixture(sequence) {
  let time = 0;
  const observations = [], sleeps = [], dispatches = [], logs = [];
  const context = {eventName: 'workflow_dispatch', repo: {owner: 'owner', repo: 'project'},
    payload: {repository: {default_branch: 'main'}}};
  const github = {rest: {actions: {createWorkflowDispatch: async input => { dispatches.push(input); }}}};
  const options = {github, context, root: '/fixture', worker: 'fixed-fixture.yml', contractPaths: ['fixed-contract'],
    now: () => time, sleep: async ms => { sleeps.push(ms); time += ms; },
    log: line => logs.push(line),
    control: async input => { observations.push(input); return sequence[Math.min(observations.length - 1, sequence.length - 1)]; }};
  return {options, observations, sleeps, dispatches, logs};
}

test('needed identifies every active status and unresolved paused attempts without mutating state', () => {
  for (const status of ['pending', 'dispatching', 'queued', 'initializing', 'running', 'retry', 'unconfirmed']) {
    const value = state(status), before = structuredClone(value);
    assert.equal(needed(value), true, status); assert.deepEqual(value, before);
  }
  for (const status of ['review', 'complete', 'blocked', 'paused']) assert.equal(needed(state(status)), false, status);
  assert.equal(needed(state()), false);
  const value = state('paused'); value.records[0].request_id = 'attempt';
  assert.equal(needed(value), true);
  value.records[0].history.push({request_id: 'other'}); assert.equal(needed(value), true);
  value.records[0].history.push({request_id: 'attempt'}); assert.equal(needed(value), false);
  for (const invalid of [null, {}, {records: null}, state('unexpected')]) assert.throws(() => needed(invalid));
});

test('reconciles immediately and exits idle without sleeping or handing off', async () => {
  const f = fixture([state()]);
  const result = await monitor(f.options);
  assert.deepEqual(result, {state: state(), ticks: 1, handoff: false});
  assert.equal(f.observations[0].now, 0); assert.equal(f.observations.length, 1);
  assert.deepEqual(f.sleeps, []); assert.deepEqual(f.dispatches, []);
});

test('waits between reconciliations, uses advancing clock, and exits on review', async () => {
  const f = fixture([state('queued'), state('running'), state('review')]);
  const result = await monitor(f.options);
  assert.equal(result.ticks, 3); assert.equal(result.handoff, false);
  assert.deepEqual(f.sleeps, [300000, 300000]);
  assert.deepEqual(f.observations.map(x => x.now), [0, 300000, 600000]);
  for (const input of f.observations) {
    assert.equal(input.github, f.options.github); assert.equal(input.context, f.options.context);
    assert.equal(input.root, '/fixture'); assert.equal(input.worker, 'fixed-fixture.yml');
    assert.deepEqual(input.contractPaths, ['fixed-contract']);
  }
  assert.deepEqual(f.dispatches, []);
});

test('default finite budget is thirteen reconciliations and twelve sleeps then one fixed handoff', async () => {
  const f = fixture([state('running')]);
  const result = await monitor(f.options);
  assert.equal(result.ticks, 13); assert.equal(result.handoff, true);
  assert.equal(f.observations.length, 13); assert.equal(f.sleeps.length, 12);
  assert.equal(f.logs.length, 13);
  assert.equal(f.sleeps.reduce((a,b) => a+b, 0), 3600000);
  assert.deepEqual(f.dispatches, [{owner: 'owner', repo: 'project', workflow_id: 'codex-monitor.yml', ref: 'main', inputs: {}}]);
});

test('each tick logs only its index and active count, not request data', async () => {
  const value = {records: [{status: 'running', message: 'private fixture prose'}, {status: 'queued'}, {status: 'review'}]};
  const f = fixture([value]);
  await monitor({...f.options, maxTicks: 1});
  assert.deepEqual(f.logs, ['codex-monitor: tick=1/1 active=2']);
  assert.ok(!f.logs.join('').includes('private fixture prose'));
});

test('last tick idle never hands off; unresolved paused attempt does', async () => {
  const done = fixture([state('running'), state('complete')]);
  assert.equal((await monitor({...done.options, maxTicks: 2})).handoff, false);
  assert.equal(done.dispatches.length, 0);
  const paused = state('paused'); paused.records[0].request_id = 'unrecorded';
  const f = fixture([paused]);
  assert.equal((await monitor({...f.options, maxTicks: 1})).handoff, true);
  assert.equal(f.sleeps.length, 0); assert.equal(f.dispatches.length, 1);
});

test('never renews plan budgets, consumes usage, or dispatches a model to poll', async () => {
  const active = state('unconfirmed');
  Object.assign(active.records[0], {expires_at: '2026-10-28T13:00:00Z', total_runs: 1, input_tokens: 500,
    plan: {limits: {max_runs: 1, max_minutes: 60, max_input_tokens: 1000}}});
  const before = structuredClone(active), f = fixture([active]);
  await monitor({...f.options, maxTicks: 2, intervalMs: 1000});
  assert.deepEqual(active, before);
  assert.deepEqual(f.sleeps, [1000]);
  assert.ok(f.dispatches.every(x => x.workflow_id === 'codex-monitor.yml'));
});

test('ambiguous successor dispatch is attempted once and surfaced without a retry', async () => {
  const f = fixture([state('pending')]); let attempts = 0;
  f.options.github.rest.actions.createWorkflowDispatch = async () => { attempts += 1; throw Error('Response lost'); };
  await assert.rejects(monitor({...f.options, maxTicks: 1}), /Response lost/);
  assert.equal(attempts, 1); assert.equal(f.observations.length, 1);
});

test('controller or sleep failure is surfaced without spawning a successor or retry loop', async () => {
  const f = fixture([state('running')]);
  await assert.rejects(monitor({...f.options, control: async () => { throw Error('Controller failure'); }}), /Controller failure/);
  await assert.rejects(monitor({...f.options, sleep: async () => { throw Error('Interrupted'); }}), /Interrupted/);
  assert.equal(f.dispatches.length, 0);
});

test('rejects unbounded tick/interval inputs before touching controller or Actions', async () => {
  const f = fixture([state('running')]);
  for (const bounds of [{maxTicks: 0}, {maxTicks: 14}, {maxTicks: Infinity}, {intervalMs: 0}, {intervalMs: 300001}, {intervalMs: 1.5}])
    await assert.rejects(monitor({...f.options, ...bounds}), /bounds/);
  assert.equal(f.observations.length, 0); assert.equal(f.dispatches.length, 0);
});
