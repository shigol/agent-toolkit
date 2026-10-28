const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {test} = require('node:test');
const {loadPlan, parse, createRecord, advance, receipt, Store, controller} = require('./codex_continuity.cjs');
const now = Date.parse('2026-10-28T12:00:00Z');

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'continuity-'));
  fs.mkdirSync(path.join(root, 'docs'));
  fs.writeFileSync(path.join(root, 'docs/a.md'), 'Check the harmless fixture.');
  const source = {schema: 1, title: 'Fixture only', limits: {max_runs: 4, max_minutes: 90, max_input_tokens: 1000},
    steps: [{id: 'first', brief: 'docs/a.md', attempts: 2, review: 'none'},
      {id: 'second', brief: 'docs/a.md', attempts: 2, review: 'none'}]};
  fs.writeFileSync(path.join(root, 'docs/plan.json'), JSON.stringify(source));
  return {root, source, plan: loadPlan(root, 'docs/plan.json'), close: () => fs.rmSync(root, {recursive: true})};
}
function record(plan) { return createRecord(plan, '99', 1, 'owner', 'a'.repeat(40), now); }
function reserve(plan) { return advance(record(plan), {}, now).record; }
function result(run, request, extra = {}) {
  return {run_id: run, request_id: request, worker: 'success', save: 'success', has_patch: false,
    held_count: 0, input_tokens: 100, usage_known: true, branch: '', ...extra};
}
function completed(id = 3) {
  return {id, status: 'completed', conclusion: 'success', html_url: `https://example.invalid/runs/${id}`,
    updated_at: new Date(now + 60000).toISOString()};
}

test('committed plans validate paths, hashes, unique IDs and bounded budgets', () => {
  const f = fixture();
  try {
    assert.equal(f.plan.steps.length, 2);
    assert.match(f.plan.steps[0].sha256, /^[a-f0-9]{64}$/);
    for (const change of [p => p.steps.push({...p.steps[0]}), p => p.limits.max_runs = 13,
      p => p.steps[0].attempts = 3, p => p.steps[0].brief = '../secret.md', p => p.command = 'shell']) {
      const plan = structuredClone(f.source); change(plan);
      fs.writeFileSync(path.join(f.root, 'docs/plan.json'), JSON.stringify(plan));
      assert.throws(() => loadPlan(f.root, 'docs/plan.json'));
    }
    fs.symlinkSync('a.md', path.join(f.root, 'docs/link.md'));
    const plan = structuredClone(f.source); plan.steps[0].brief = 'docs/link.md';
    fs.writeFileSync(path.join(f.root, 'docs/plan.json'), JSON.stringify(plan));
    assert.throws(() => loadPlan(f.root, 'docs/plan.json'), /Symlink/);
  } finally { f.close(); }
});

test('request parser accepts only fixed commands, no arbitrary payload or multiline commands', () => {
  assert.deepEqual(parse('/codex-plan docs/plan.json'), {command: 'plan', value: 'docs/plan.json'});
  for (const text of ['/codex-plan docs/x.json\nmore', '/codex-plan docs/x.json ; shell', '/codex-accept owner']) assert.throws(() => parse(text));
});

test('dispatch reservation is durable and a missing run is never blindly duplicated', () => {
  const f = fixture();
  try {
    const first = advance(record(f.plan), {}, now);
    assert.equal(first.effects.length, 1);
    assert.equal(first.record.status, 'dispatching');
    assert.equal(first.record.total_runs, 1);
    const second = advance(first.record, {}, now + 11 * 60000);
    assert.equal(second.record.status, 'unconfirmed');
    assert.equal(second.effects.length, 0);
    assert.equal(second.record.request_id, first.record.request_id);
  } finally { f.close(); }
});

test('real queued/running state is distinct from an accepted dispatch', () => {
  const f = fixture();
  try {
    const item = reserve(f.plan);
    let next = advance(item, {run: {...completed(), status: 'queued'}}, now + 1000);
    assert.equal(next.record.status, 'queued');
    next = advance(next.record, {run: {...completed(), status: 'in_progress'}}, now + 2000);
    assert.equal(next.record.status, 'running');
    assert.equal(next.record.run_id, 3);
  } finally { f.close(); }
});

test('a successful read-only step starts the next committed step immediately; final acceptance remains separate', () => {
  const f = fixture();
  try {
    const one = reserve(f.plan);
    const two = advance(one, {run: completed(), receipt: result(3, one.request_id)}, now + 60000);
    assert.equal(two.record.step, 1);
    assert.equal(two.record.total_runs, 2);
    assert.equal(two.effects[0].type, 'dispatch');
    const end = advance(two.record, {run: completed(4), receipt: result(4, two.record.request_id)}, now + 120000);
    assert.equal(end.record.status, 'review');
    assert.equal(end.effects.length, 0);
  } finally { f.close(); }
});

test('failed attempts retry within the declared cap and then stop', () => {
  const f = fixture();
  try {
    let item = reserve(f.plan);
    let next = advance(item, {run: {...completed(), conclusion: 'failure'}, receipt: result(3, item.request_id, {worker: 'failure'})}, now + 60000);
    assert.equal(next.record.attempt, 2);
    assert.equal(next.effects[0].type, 'dispatch');
    item = next.record;
    next = advance(item, {run: {...completed(4), conclusion: 'failure'}, receipt: result(4, item.request_id, {worker: 'failure'})}, now + 120000);
    assert.equal(next.record.status, 'blocked');
    assert.equal(next.record.total_runs, 2);
    assert.equal(next.effects.length, 0);
  } finally { f.close(); }
});

test('changed or held files always stop at review even on a failed attempt', () => {
  const f = fixture();
  try {
    for (const extra of [{has_patch: true, branch: 'codex/task-3'}, {held_count: 1}]) {
      const item = reserve(f.plan);
      const next = advance(item, {run: {...completed(), conclusion: 'failure'}, receipt: result(3, item.request_id, extra)}, now + 60000);
      assert.equal(next.record.status, 'review');
      assert.equal(next.effects.length, 0);
    }
  } finally { f.close(); }
});

test('unknown usage, exceeded usage and elapsed budgets cannot start another model call', () => {
  const f = fixture();
  try {
    let item = reserve(f.plan);
    let next = advance(item, {run: completed(), receipt: result(3, item.request_id, {usage_known: false})}, now + 60000);
    assert.equal(next.record.status, 'blocked');
    item = reserve(f.plan);
    next = advance(item, {run: completed(), receipt: result(3, item.request_id, {input_tokens: 1000})}, now + 60000);
    assert.equal(next.record.status, 'blocked');
    next = advance(item, {run: {...completed(), status: 'in_progress'}}, now + 91 * 60000);
    assert.equal(next.record.status, 'paused');
    assert.deepEqual(next.effects, [{type: 'cancel', id: 3}]);
  } finally { f.close(); }
});

test('source drift and stale workers produce a pause/cancel instead of silent continuation', () => {
  const f = fixture();
  try {
    const item = reserve(f.plan);
    const drift = advance(item, {changed: true, run: {...completed(), status: 'in_progress'}}, now + 1000);
    assert.equal(drift.record.status, 'paused');
    assert.equal(drift.effects[0].type, 'cancel');
    const stale = advance(item, {run: {...completed(), status: 'in_progress', run_started_at: new Date(now).toISOString()}}, now + 51 * 60000);
    assert.equal(stale.effects[0].type, 'cancel');
  } finally { f.close(); }
});

test('result receipts are bounded, typed and tied to the exact run/request', () => {
  const body = '<!-- codex-result:3 -->\n' + JSON.stringify(result(3, 'continuity-99-0-1')) + '\nHuman summary';
  assert.equal(receipt(body, 'continuity-99-0-1', 3).worker, 'success');
  assert.equal(receipt(body, 'other-request', 3), null);
  assert.equal(receipt(body.replace('codex-result:3', 'codex-result:4'), 'continuity-99-0-1', 3), null);
  assert.equal(receipt('<!-- codex-result:3 -->\n' + JSON.stringify(result(3, 'x', {branch: 'main'})), 'x', 3), null);
});

class MemoryStore {
  constructor() { this.value = {schema: 1, records: []}; this.saves = []; this.old = new Set(); }
  async load() { return structuredClone(this.value); }
  async save(state) { this.value = structuredClone(state); this.saves.push(structuredClone(state)); }
  archive(record) { this.old.add(record.id); }
  async archived(id) { return this.old.has(id); }
}
function service() {
  const calls = [], comments = [], runs = [];
  const github = {rest: {actions: {
    listWorkflowRuns: async () => ({data: {workflow_runs: runs}}),
    createWorkflowDispatch: async call => { calls.push(call); runs.push({id: 3, status: 'in_progress', event: 'workflow_dispatch',
      head_branch: 'main', head_repository: {full_name: 'owner/project'},
      display_title: `Codex request ${call.inputs.request_id} — ${call.inputs.brief}`, html_url: 'https://example.invalid/run/3'}); },
    cancelWorkflowRun: async call => calls.push({cancel: call.run_id})},
  repos: {getCollaboratorPermissionLevel: async () => ({data: {permission: 'read'}})},
  pulls: {list: async () => ({data: []})},
  issues: {listComments: () => {}, createComment: async call => { comments.push({...call, id: comments.length + 1, user: {login: 'github-actions[bot]'}}); return {data: {id: comments.length}}; },
    updateComment: async call => { const old = comments.find(x => x.id === call.comment_id); if (old) old.body = call.body; } }},
  paginate: async () => comments};
  github.rest.actions.enableWorkflow = async () => {};
  github.rest.actions.disableWorkflow = async () => {};
  return {github, calls, comments, runs};
}
function context(body = '/codex-plan docs/plan.json') {
  return {eventName: 'issue_comment', repo: {owner: 'owner', repo: 'project'}, payload: {
    repository: {default_branch: 'main'}, comment: {id: 99, body, user: {login: 'owner'}}, issue: {number: 1}}};
}

test('duplicate request delivery and controller crash after dispatch do not duplicate work', async () => {
  const f = fixture(), api = service(), store = new MemoryStore();
  try {
    const normal = api.github.rest.issues.createComment;
    api.github.rest.issues.createComment = async () => { throw Error('callback temporarily unavailable'); };
    await assert.rejects(controller({github: api.github, context: context(), root: f.root, store, now}));
    assert.equal(api.calls.length, 1);
    assert.equal(store.value.records[0].status, 'dispatching');
    api.github.rest.issues.createComment = normal;
    await controller({github: api.github, context: context(), root: f.root, store, now: now + 1000});
    assert.equal(api.calls.length, 1);
    assert.equal(store.value.records.length, 1);
    assert.equal(store.value.records[0].status, 'running');
  } finally { f.close(); }
});

test('reader-only users cannot register or accept unattended work', async () => {
  const f = fixture(), api = service(), store = new MemoryStore(), event = context();
  event.payload.comment.user.login = 'visitor';
  try {
    await assert.rejects(controller({github: api.github, context: event, root: f.root, store, now}), /writers/);
    assert.equal(api.calls.length, 0);
    assert.equal(store.value.records.length, 0);
  } finally { f.close(); }
});

test('a same-title PR/fork run cannot impersonate the trusted default-branch worker', async () => {
  const f = fixture(), api = service(), store = new MemoryStore();
  try {
    await controller({github: api.github, context: context(), root: f.root, store, now});
    api.runs[0].head_branch = 'unreviewed';
    api.runs[0].head_repository = {full_name: 'someone/fork'};
    await controller({github: api.github, context: context(), root: f.root, store, now: now + 11 * 60000});
    assert.equal(store.value.records[0].status, 'unconfirmed');
    assert.equal(store.value.records[0].run_id, undefined);
    assert.equal(api.calls.length, 1);
  } finally { f.close(); }
});

test('trusted receipt parser keeps unknown or partial metadata out of automatic progress', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'result-receipt-'));
  try {
    const {result: format} = require('./codex_result.cjs');
    const metadata = {run_id: 3, request_id: 'x', worker: 'failure', execution: 'failure', save: 'success'};
    assert.equal(format(root, metadata).usage_known, false);
    assert.equal(format(root, {...metadata, execution: 'skipped'}).usage_known, true);
    fs.writeFileSync(path.join(root, 'checkpoint.json'), JSON.stringify({input_tokens: 250, usage_known: true, status: 'execution_complete'}));
    fs.writeFileSync(path.join(root, 'patch-report.json'), JSON.stringify({held: ['.github/workflows/held.yml']}));
    assert.equal(format(root, metadata).input_tokens, 250);
    assert.equal(format(root, metadata).held_count, 1);
    fs.unlinkSync(path.join(root, 'checkpoint.json'));
    fs.symlinkSync('patch-report.json', path.join(root, 'checkpoint.json'));
    assert.throws(() => format(root, metadata), /Invalid bounded/);
  } finally { fs.rmSync(root, {recursive: true}); }
});

test('writer pause updates the visible checkpoint and cancels an active job', async () => {
  const f = fixture(), api = service(), store = new MemoryStore();
  try {
    await controller({github: api.github, context: context(), root: f.root, store, now});
    await controller({github: api.github, context: context(), root: f.root, store, now: now + 1000});
    await controller({github: api.github, context: context('/codex-pause 99'), root: f.root, store, now: now + 2000});
    assert.equal(store.value.records[0].status, 'paused');
    assert.equal(api.calls.at(-1).cancel, 3);
    assert.match(api.comments[0].body, /paused/);
  } finally { f.close(); }
});

test('pause before a run becomes visible cannot be resumed into a duplicate dispatch', async () => {
  const f = fixture(), api = service(), store = new MemoryStore();
  try {
    await controller({github: api.github, context: context(), root: f.root, store, now});
    api.runs.length = 0;
    await controller({github: api.github, context: context('/codex-pause 99'), root: f.root, store, now: now + 1000});
    await assert.rejects(controller({github: api.github, context: context('/codex-resume 99'), root: f.root, store, now: now + 2000}), /unconfirmed/);
    assert.equal(api.calls.length, 1);
  } finally { f.close(); }
});

test('stale result callback blocks instead of retrying an unknown completed execution', () => {
  const f = fixture();
  try {
    const item = reserve(f.plan);
    const next = advance(item, {run: completed()}, now + 12 * 60000);
    assert.equal(next.record.status, 'blocked');
    assert.equal(next.effects.length, 0);
  } finally { f.close(); }
});

test('durable state uses a separate ref and non-forced forward updates', async () => {
  const calls = [];
  const github = {rest: {git: {
    getRef: async () => { const error = Error('missing'); error.status = 404; throw error; },
    createTree: async call => { calls.push(call); return {data: {sha: 'tree'}}; },
    createCommit: async call => { calls.push(call); return {data: {sha: `commit-${calls.length}`}}; },
    createRef: async call => calls.push(call), updateRef: async call => calls.push(call)}}};
  const store = new Store(github, {owner: 'owner', repo: 'project'});
  const state = await store.load();
  await store.save(state); await store.save(state);
  assert.equal(calls.find(x => x.ref?.startsWith('refs/')).ref, 'refs/heads/codex/continuity-state');
  assert.equal(calls.at(-1).force, false);
  assert.equal(calls.at(-1).ref, 'heads/codex/continuity-state');
  assert.deepEqual(calls[0].tree.map(x => x.path), ['state.json']);
});

test('the no-model watchdog is enabled only for active work and disabled when the repo is idle', async () => {
  const f = fixture(), api = service(), store = new MemoryStore(), changes = [];
  api.github.rest.actions.enableWorkflow = async call => changes.push(['enable', call.workflow_id]);
  api.github.rest.actions.disableWorkflow = async call => changes.push(['disable', call.workflow_id]);
  try {
    await controller({github: api.github, context: context(), root: f.root, store, now});
    assert.deepEqual(changes, [['enable', 'codex-continuity-watchdog.yml']]);
    store.value.records[0].status = 'complete';
    const tick = {eventName: 'workflow_dispatch', repo: context().repo, payload: {repository: {default_branch: 'main'}}};
    await controller({github: api.github, context: tick, root: f.root, store, now: now + 1000});
    assert.deepEqual(changes.at(-1), ['disable', 'codex-continuity-watchdog.yml']);
  } finally { f.close(); }
});

test('archived accepted requests stay idempotent and are not restarted by event redelivery', async () => {
  const f = fixture(), api = service(), store = new MemoryStore();
  try {
    store.old.add('99');
    await controller({github: api.github, context: context(), root: f.root, store, now});
    assert.equal(api.calls.length, 0);
    assert.equal(store.value.records.length, 0);
  } finally { f.close(); }
});

test('independent watchdog is armed before any external model dispatch', async () => {
  const f = fixture(), api = service(), store = new MemoryStore(), order = [];
  api.github.rest.actions.enableWorkflow = async () => order.push('watchdog');
  const dispatch = api.github.rest.actions.createWorkflowDispatch;
  api.github.rest.actions.createWorkflowDispatch = async call => { order.push('worker'); return dispatch(call); };
  try {
    await controller({github: api.github, context: context(), root: f.root, store, now});
    assert.deepEqual(order, ['watchdog', 'worker']);
  } finally { f.close(); }
});

test('reviewed stopped plans can be archived without calling them complete; active plans cannot', async () => {
  const f = fixture(), api = service(), store = new MemoryStore();
  try {
    await controller({github: api.github, context: context(), root: f.root, store, now});
    await assert.rejects(controller({github: api.github, context: context('/codex-archive 99'), root: f.root, store, now: now + 1000}), /Pause\/finish/);
    const saved = store.value.records[0];
    saved.status = 'blocked';
    saved.history.push({request_id: saved.request_id, run_id: 3});
    await controller({github: api.github, context: context('/codex-archive 99'), root: f.root, store, now: now + 2000});
    assert.equal(store.value.records.length, 0);
    assert.equal(store.old.has('99'), true);
    assert.match(api.comments.at(-1).body, /no work was marked complete/);
  } finally { f.close(); }
});
