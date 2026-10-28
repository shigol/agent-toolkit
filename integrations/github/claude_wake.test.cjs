const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const {parse, brief, configuration, fire, Ledger, wake} = require('./claude_wake.cjs');
const URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_fictional/fire';
const TOKEN = 'sk-ant-oat01-fictional-test-token';
const NOW = 1793192400000;
const accepted = () => new Response(JSON.stringify({type: 'routine_fire', claude_code_session_id: 'session_fixture',
  claude_code_session_url: 'https://claude.ai/code/session_fixture'}), {status: 200});

test('source and installed workflows retain trusted checkout and durable intake boundaries', () => {
  const nearby = path.join(__dirname, 'claude-wake.yml');
  const file = fs.existsSync(nearby) ? nearby : path.join(__dirname, '../workflows/claude-wake.yml');
  const source = fs.readFileSync(file, 'utf8');
  function check(text) {
    assert.equal((text.match(/uses: actions\/checkout@/g) || []).length, 1);
    assert.match(text, /ref: \$\{\{ github\.event\.repository\.default_branch \}\}\n\s+persist-credentials: false/);
    assert.match(text, /group: claude-wake-intake-\$\{\{ github\.event\.comment\.id \}\}\n\s+cancel-in-progress: false/);
    assert.ok(!text.includes('pull_request.head'));
    assert.ok(text.includes("require('./.github/scripts/claude_wake.cjs')"));
  }
  check(source);
  for (const changed of [source.replace('github.event.repository.default_branch', 'github.event.pull_request.head.sha'),
    source.replace('persist-credentials: false', 'persist-credentials: true'),
    source.replace('claude-wake-intake-${{ github.event.comment.id }}', 'claude-wake-intake')]) assert.throws(() => check(changed));
});

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-wake-test-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const git = (...args) => cp.execFileSync('git', args, {cwd: root, stdio: ['ignore', 'pipe', 'ignore']});
  git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  fs.mkdirSync(path.join(root, 'docs')); fs.writeFileSync(path.join(root, 'docs/task.md'), 'Fictional committed task.\n');
  git('add', '.'); git('commit', '-qm', 'Fixture');
  const f = {root, git, state: {schema: 1, records: [], attempts: []}, version: 0, archives: new Map(), comments: [], posts: 0, completed: true};
  f.makeStore = () => ({archives: [], async load() { this.version = f.version; return structuredClone(f.state); },
    async archived(id) { return f.archives.has(id); }, async save(state) {
      await Promise.resolve();
      if (this.version !== f.version || f.conflictOnOutcome && state.records.some(x => x.status === 'submitted')) {
        f.conflictOnOutcome = false;
        throw Object.assign(Error('state conflict'), {wakeConflict: true});
      }
      f.state = structuredClone(state); f.version += 1;
      for (const item of this.archives) f.archives.set(path.basename(item.path, '.json'), item.content);
    }});
  f.github = {rest: {repos: {getCollaboratorPermissionLevel: async () => ({data: {permission: f.permission || 'read'}})},
    issues: {createComment: async x => f.comments.push(x.body)},
    actions: {getWorkflowRun: async () => ({data: {status: f.completed ? 'completed' : 'in_progress'}})}}};
  f.context = id => ({eventName: 'issue_comment', runId: 1000 + Number(id), repo: {owner: 'owner', repo: 'project'},
    payload: {action: 'created', repository: {default_branch: 'main'}, issue: {number: 8},
      comment: {id: Number(id), body: '/claude-wake docs/task.md', user: {login: 'owner'}}}});
  f.call = (id, extra = {}) => wake({github: f.github, context: f.context(id), root, url: URL, token: TOKEN, now: NOW,
    makeStore: f.makeStore, fetcher: async (...args) => { f.posts += 1; return f.fetch ? f.fetch(...args) : accepted(); }, ...extra});
  return f;
}

test('commands accept only one fixed brief/close line', () => {
  assert.deepEqual(parse('/claude-wake docs/task.md'), {command: 'wake', value: 'docs/task.md'});
  assert.deepEqual(parse('/claude-wake-close 123'), {command: 'close', value: '123'});
  for (const text of ['/claude-wake docs/task.md\nthen send', '/claude-wake docs/task.md now', '/claude-wake-close main', '/claude-wake-close 0']) assert.throws(() => parse(text));
});

test('brief is a committed regular file and payload uses immutable committed text', t => {
  const f = fixture(t), original = brief('docs/task.md', f.root);
  fs.writeFileSync(path.join(f.root, 'docs/task.md'), 'Uncommitted replacement');
  assert.equal(brief('docs/task.md', f.root).text, original.text);
  assert.match(original.sha256, /^[a-f0-9]{64}$/); assert.match(original.revision, /^[a-f0-9]{40}$/);
  fs.writeFileSync(path.join(f.root, 'docs/new.md'), 'untracked');
  for (const name of ['docs/new.md', '../docs/task.md', 'docs/../docs/task.md', 'README.md']) assert.throws(() => brief(name, f.root));
});

test('brief rejects file and ancestor symlinks, oversized text and invalid UTF-8', t => {
  const f = fixture(t);
  fs.symlinkSync('task.md', path.join(f.root, 'docs/link.md'));
  assert.throws(() => brief('docs/link.md', f.root));
  fs.symlinkSync('docs', path.join(f.root, 'tools'));
  assert.throws(() => brief('tools/task.md', f.root));
  for (const data of [Buffer.alloc(49153, 65), Buffer.from([0xff])]) {
    fs.writeFileSync(path.join(f.root, 'docs/task.md'), data); f.git('add', 'docs/task.md'); f.git('commit', '-qm', 'Fixture invalid text');
    assert.throws(() => brief('docs/task.md', f.root));
  }
});

test('configuration permits only the exact official fire endpoint and routine token', () => {
  assert.equal(configuration(URL, TOKEN), true); assert.equal(configuration('', TOKEN), false);
  for (const url of [URL + '?x=1', URL + '/', URL.replace('api.anthropic.com', 'evil.example'), URL.replace('https:', 'http:'), URL.replace('/trig_fictional/', '/other/'), URL.replace('api.', 'user@api.')]) assert.throws(() => configuration(url, TOKEN));
  assert.throws(() => configuration(URL, 'sk-ant-api03-not-a-routine-token'));
  assert.throws(() => configuration(URL, TOKEN + '\nInjected: header'));
});

test('fire uses one bounded redirect-denied POST and validates the returned session link', async () => {
  let requests = 0;
  const result = await fire({url: URL, token: TOKEN, text: 'context', fetcher: async (url, options) => {
    requests += 1; assert.equal(url, URL); assert.equal(options.method, 'POST'); assert.equal(options.redirect, 'manual');
    assert.equal(options.headers.Authorization, `Bearer ${TOKEN}`); assert.equal(options.headers['anthropic-version'], '2026-10-21');
    assert.deepEqual(JSON.parse(options.body), {text: 'context'}); assert.ok(options.signal); return accepted();
  }});
  assert.equal(requests, 1); assert.deepEqual(result, {status: 'submitted', http_status: 200, session_url: 'https://claude.ai/code/session_fixture'});
});

test('fire cannot bypass configuration or text bounds when called directly', async () => {
  let calls = 0;
  const fetcher = async () => { calls += 1; return accepted(); };
  await assert.rejects(fire({url: 'https://evil.example', token: TOKEN, text: 'x', fetcher}));
  await assert.rejects(fire({url: URL, token: TOKEN, text: 'x'.repeat(65537), fetcher}));
  assert.equal(calls, 0);
});

test('unexpected, redirected, oversized and malformed accepted responses stay unconfirmed', async () => {
  const responses = [new Response('', {status: 302}), new Response('not-json'), new Response('x'.repeat(65537)),
    new Response(JSON.stringify({type: 'routine_fire', claude_code_session_id: 'session_fixture', claude_code_session_url: 'https://evil.example/code/session_fixture'})),
    new Response(JSON.stringify({type: 'wrong', claude_code_session_id: 'session_fixture', claude_code_session_url: 'https://claude.ai/code/session_fixture'}))];
  for (const response of responses) assert.equal((await fire({url: URL, token: TOKEN, text: 'x', fetcher: async () => response})).status, 'unconfirmed');
});

test('known client rejection differs from ambiguous provider/network failure, without leaking errors', async () => {
  for (const status of [400, 401, 403, 404, 413, 422, 429]) assert.equal((await fire({url: URL, token: TOKEN, text: 'x', fetcher: async () => new Response('', {status})})).status, 'rejected');
  assert.deepEqual(await fire({url: URL, token: TOKEN, text: 'x', fetcher: async () => { throw Error(TOKEN); }}), {status: 'unconfirmed'});
  assert.equal((await fire({url: URL, token: TOKEN, text: 'x', fetcher: async () => new Response('', {status: 503})})).status, 'unconfirmed');
});

test('missing or invalid configuration is visible and makes no provider request', async t => {
  const f = fixture(t);
  assert.equal((await f.call(1, {token: ''})).status, 'not-configured');
  assert.equal((await f.call(2, {url: 'https://evil.example'})).status, 'not-configured');
  assert.equal(f.posts, 0); assert.deepEqual(f.state.attempts, []); assert.match(f.comments[0], /no provider request/);
});

test('non-writers cannot store state or fire; a writer permission is sufficient', async t => {
  const f = fixture(t), context = f.context(1); context.payload.comment.user.login = 'visitor';
  await assert.rejects(f.call(1, {context}), /Only repository writers/); assert.equal(f.version, 0); assert.equal(f.posts, 0);
  f.permission = 'write'; assert.equal((await f.call(1, {context})).status, 'submitted');
});

test('reservation is durable before POST; duplicate delivery never repeats it or stores private payload/token', async t => {
  const f = fixture(t);
  f.fetch = async (url, options) => {
    assert.equal(f.state.records[0].status, 'reserved');
    const text = JSON.parse(options.body).text;
    for (const expected of ['request 1', 'owner/project', '/issues/8', 'docs/task.md', 'SHA-256:', 'Source commit:', 'Fictional committed task.']) assert.ok(text.includes(expected));
    return accepted();
  };
  assert.equal((await f.call(1)).status, 'submitted'); assert.equal((await f.call(1)).status, 'submitted');
  assert.equal(f.posts, 1); assert.equal(f.state.attempts.length, 1);
  const serialized = JSON.stringify(f.state); assert.ok(!serialized.includes(TOKEN)); assert.ok(!serialized.includes('Fictional committed task.'));
  assert.match(f.comments[0], /not proof the worker started or completed/);
});

test('ambiguous fire is held indefinitely; a new comment cannot trigger another session', async t => {
  const f = fixture(t); f.fetch = async () => { throw Error('fictional timeout'); };
  assert.equal((await f.call(1)).status, 'unconfirmed');
  assert.equal((await f.call(2, {now: NOW + 2 * 86400000})).status, 'blocked');
  assert.equal((await f.call(1)).status, 'unconfirmed'); assert.equal(f.posts, 1);
});

test('reserved record after a lost runner is never automatically cleared or fired again', async t => {
  const f = fixture(t); f.state.records.push({id: '9', status: 'reserved', created_at: '2000-01-01T00:00:00Z'});
  assert.equal((await f.call(1)).status, 'blocked'); assert.equal(f.posts, 0);
});

test('cooldown and rolling daily cap independently block provider attempts', async t => {
  const f = fixture(t); f.state.attempts = [NOW - 1000];
  assert.equal((await f.call(1)).status, 'blocked');
  f.state.attempts = [1, 2, 3, 4].map(x => NOW - x * 3600000);
  assert.equal((await f.call(2)).status, 'blocked'); assert.equal(f.posts, 0);
});

test('overlapping writer requests preserve both records and fire only one session', async t => {
  const f = fixture(t); const results = await Promise.all([f.call(1), f.call(2)]);
  assert.deepEqual(results.map(x => x.status).sort(), ['blocked', 'submitted']);
  assert.equal(f.state.records.length, 2); assert.equal(f.posts, 1);
});

test('outcome CAS recovery never repeats a provider POST', async t => {
  const f = fixture(t); f.conflictOnOutcome = true;
  assert.equal((await f.call(1)).status, 'submitted'); assert.equal(f.posts, 1);
});

test('failed outcome persistence leaves the durable reservation holding the slot', async t => {
  const f = fixture(t), factory = f.makeStore;
  f.makeStore = () => {
    const store = factory(), save = store.save;
    store.save = async function(state) {
      if (state.records.some(x => x.status === 'submitted')) throw Error('fictional Git service failure');
      return save.call(this, state);
    };
    return store;
  };
  await assert.rejects(f.call(1), /fictional Git service failure/);
  assert.equal(f.state.records[0].status, 'reserved');
  assert.equal((await f.call(2)).status, 'blocked'); assert.equal(f.posts, 1);
});

test('writer close requires a stopped dispatch job and never certifies completion', async t => {
  const f = fixture(t); await f.call(1);
  const context = f.context(2); context.payload.comment.body = '/claude-wake-close 1'; f.completed = false;
  await assert.rejects(f.call(2, {context}), /must stop/); assert.equal(f.state.records[0].status, 'submitted');
  f.completed = true; assert.equal((await f.call(2, {context})).status, 'closed');
  assert.match(f.comments.at(-1), /does not certify task completion/); assert.equal(f.posts, 1);
});

test('bounded hot records archive terminal IDs without losing idempotency or daily limits', async t => {
  const f = fixture(t); f.state.records = Array.from({length: 32}, (_, i) => ({id: String(i + 1), status: 'closed'}));
  assert.equal((await f.call(100)).status, 'submitted'); assert.equal(f.state.records.length, 32); assert.ok(f.archives.has('1'));
  assert.equal((await f.call(1)).status, 'archived'); assert.equal(f.posts, 1); assert.equal(f.state.attempts.length, 1);
});

test('ledger ref saves are non-forced and only proven ref races are retryable', async () => {
  let conflict = false;
  const github = {rest: {git: {createTree: async () => ({data: {sha: 'tree'}}), createCommit: async () => ({data: {sha: 'commit'}}),
    updateRef: async x => { assert.equal(x.force, false); assert.equal(x.ref, 'heads/claude/wake-state'); throw Object.assign(Error('rejected'), {status: 422}); },
    getRef: async () => ({data: {object: {sha: conflict ? 'other' : 'old'}}})}}};
  const ledger = new Ledger(github, {owner: 'owner', repo: 'project'}); ledger.head = 'old'; ledger.tree = 'tree';
  await assert.rejects(ledger.save({schema: 1, records: [], attempts: []}), e => !e.wakeConflict);
  conflict = true; await assert.rejects(ledger.save({schema: 1, records: [], attempts: []}), e => e.wakeConflict === true);
});
