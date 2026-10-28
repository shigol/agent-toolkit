// Trusted default-branch bridge. One durable reservation, at most one provider POST.
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const REF = 'claude/wake-state', FILE = 'state.json';
const ACTIVE = new Set(['reserved', 'submitted', 'unconfirmed']);
const DAY = 86400000, COOLDOWN = 900000, DAILY_CAP = 4, MAX_RECORDS = 32;

function parse(body) {
  const match = /^\/claude-wake(?:-(close))? ([A-Za-z0-9_./-]+)$/.exec(String(body).trim());
  if (!match) throw Error('Use one line: /claude-wake docs/path.md or /claude-wake-close REQUEST_ID');
  if (match[1] && !/^[1-9][0-9]{0,19}$/.test(match[2])) throw Error('Invalid wake request ID');
  return {command: match[1] ? 'close' : 'wake', value: match[2]};
}

function brief(value, root) {
  if (!/^(?:codex|docs|tools)\/[A-Za-z0-9_./-]+\.md$/.test(value)
      || value.split('/').some(x => !x || x === '.' || x === '..')) throw Error('Invalid committed wake brief');
  const base = fs.realpathSync(root);
  let cursor = base;
  for (const part of value.split('/')) {
    cursor = path.join(cursor, part);
    if (fs.lstatSync(cursor).isSymbolicLink()) throw Error('Wake briefs cannot use symlinks');
  }
  if (!fs.statSync(cursor).isFile()) throw Error('Wake brief must be a regular file');
  const readGit = (args, maxBuffer = 65537) => {
    try { return cp.execFileSync('git', args, {cwd: base, maxBuffer, stdio: ['ignore', 'pipe', 'ignore']}); }
    catch { throw Error('Unable to read bounded committed wake source'); }
  };
  const entry = readGit(['ls-tree', '-z', 'HEAD', '--', value]).toString();
  if (!new RegExp('^100644 blob [a-f0-9]{40}\\t' + value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\0$').test(entry)) throw Error('Wake brief must be committed as a regular Markdown file');
  const source = readGit(['show', `HEAD:${value}`]);
  if (source.length > 49152 || !source.equals(Buffer.from(source.toString('utf8')))) throw Error('Wake brief must be UTF-8 and at most 48 KiB');
  return {text: source.toString('utf8'), sha256: crypto.createHash('sha256').update(source).digest('hex'),
    revision: readGit(['rev-parse', 'HEAD']).toString().trim()};
}

function configuration(url, token) {
  if (!url || !token) return false;
  if (!/^https:\/\/api\.anthropic\.com\/v1\/claude_code\/routines\/trig_[A-Za-z0-9_-]{1,128}\/fire$/.test(url)
      || !/^sk-ant-oat01-[A-Za-z0-9_-]{1,1024}$/.test(token)) throw Error('Invalid Claude routine configuration');
  return true;
}

function responseShape(body) {
  // Only fixed structural names and booleans leave this function, never values or unknown keys.
  const known = ['type', 'id', 'url', 'status', 'object', 'session_id', 'session_url',
    'claude_code_session_id', 'claude_code_session_url', 'routine_id', 'trigger_id', 'request_id',
    'data', 'result', 'response', 'session'];
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  function fields(value) {
    if (!object(value)) return {object: false, array: Array.isArray(value)};
    const keys = known.filter(key => Object.hasOwn(value, key));
    const id = value.claude_code_session_id, url = value.claude_code_session_url;
    return {object: true, known_keys: keys, other_keys_present: Object.keys(value).some(key => !known.includes(key)),
      string_fields: keys.filter(key => typeof value[key] === 'string'),
      object_fields: keys.filter(key => object(value[key])),
      expected_type_matches: value.type === 'routine_fire',
      expected_id_format_matches: typeof id === 'string' && /^(?:session|cse)_[A-Za-z0-9_-]{1,128}$/.test(id),
      expected_url_format_matches: typeof url === 'string' && /^https:\/\/claude\.ai\/code\/(?:session|cse)_[A-Za-z0-9_-]{1,128}$/.test(url),
      expected_url_matches_id: typeof id === 'string' && /^(?:session|cse)_[A-Za-z0-9_-]{1,128}$/.test(id) && url === `https://claude.ai/code/${id}`,
      id_shapes: Object.fromEntries(['claude_code_session_id', 'session_id', 'id'].filter(key => Object.hasOwn(value, key))
        .map(key => [key, {session_prefix: typeof value[key] === 'string' && /^session_[A-Za-z0-9_-]{1,128}$/.test(value[key]),
          cse_prefix: typeof value[key] === 'string' && /^cse_[A-Za-z0-9_-]{1,128}$/.test(value[key])}])),
      url_shapes: Object.fromEntries(['claude_code_session_url', 'session_url', 'url'].filter(key => Object.hasOwn(value, key))
        .map(key => [key, {session_path: typeof value[key] === 'string' && /^https:\/\/claude\.ai\/code\/session_[A-Za-z0-9_-]{1,128}$/.test(value[key]),
          cse_path: typeof value[key] === 'string' && /^https:\/\/claude\.ai\/code\/cse_[A-Za-z0-9_-]{1,128}$/.test(value[key])}]))};
  }
  const shape = fields(body);
  if (!shape.object) return shape;
  shape.containers = Object.fromEntries(['data', 'result', 'response', 'session']
    .filter(key => Object.hasOwn(body, key)).map(key => [key, fields(body[key])]));
  if (JSON.stringify(shape).length > 2048) { shape.containers = {}; shape.containers_omitted = true; }
  return shape;
}

async function fire({url, token, text, fetcher = fetch}) {
  if (!configuration(url, token) || typeof text !== 'string' || text.length > 65536) throw Error('Invalid bounded routine request');
  const timeout = new AbortController(), timer = setTimeout(() => timeout.abort(), 15000);
  try {
    const response = await fetcher(url, {method: 'POST', redirect: 'manual', signal: timeout.signal,
      headers: {Authorization: `Bearer ${token}`, 'anthropic-version': '2026-10-21', 'Content-Type': 'application/json'},
      body: JSON.stringify({text})});
    if (response.status !== 200) return {status: [400, 401, 403, 404, 413, 422, 429].includes(response.status) ? 'rejected' : 'unconfirmed', http_status: response.status};
    const chunks = [];
    let size = 0;
    for await (const chunk of response.body) {
      size += chunk.length;
      if (size > 65536) throw Error('Oversized provider response');
      chunks.push(chunk);
    }
    const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if (body === null || body.type !== 'routine_fire' || typeof body.claude_code_session_id !== 'string'
        || !/^(?:session|cse)_[A-Za-z0-9_-]{1,128}$/.test(body.claude_code_session_id)
        || body.claude_code_session_url !== `https://claude.ai/code/${body.claude_code_session_id}`) {
      return {status: 'unconfirmed', http_status: 200, response_shape: responseShape(body)};
    }
    return {status: 'submitted', http_status: 200, session_url: body.claude_code_session_url};
  } catch {
    return {status: 'unconfirmed'}; // Never include request headers, response bodies or transport errors.
  } finally { clearTimeout(timer); }
}

class Ledger {
  constructor(github, repo) { this.github = github; this.repo = repo; this.head = null; this.tree = null; this.archives = []; }
  async load() {
    try {
      this.head = (await this.github.rest.git.getRef({...this.repo, ref: `heads/${REF}`})).data.object.sha;
      this.tree = (await this.github.rest.git.getCommit({...this.repo, commit_sha: this.head})).data.tree.sha;
      const item = (await this.github.rest.repos.getContent({...this.repo, path: FILE, ref: this.head})).data;
      if (item.encoding !== 'base64' || !Number.isSafeInteger(item.size) || item.size > 131072) throw Error('Invalid wake ledger');
      const data = JSON.parse(Buffer.from(item.content, 'base64').toString());
      if (data.schema !== 1 || !Array.isArray(data.records) || data.records.length > MAX_RECORDS
          || !Array.isArray(data.attempts) || data.attempts.length > DAILY_CAP
          || data.attempts.some(x => !Number.isSafeInteger(x) || x < 0)
          || data.records.some(x => !/^[1-9][0-9]{0,19}$/.test(x.id)
            || !['reserved', 'submitted', 'unconfirmed', 'rejected', 'not-configured', 'blocked', 'closed'].includes(x.status)
            || !Number.isSafeInteger(x.run_id) || x.run_id < 1)) throw Error('Invalid wake ledger schema');
      return data;
    } catch (error) {
      if (error.status === 404 && !this.head) return {schema: 1, records: [], attempts: []};
      throw error;
    }
  }
  async archived(id) {
    if (!this.head) return false;
    try { await this.github.rest.repos.getContent({...this.repo, path: `archive/${id}.json`, ref: this.head}); return true; }
    catch (error) { if (error.status === 404) return false; throw error; }
  }
  async save(data) {
    const content = JSON.stringify(data, null, 2) + '\n';
    if (Buffer.byteLength(content) > 131072) throw Error('Wake ledger exceeds its bound');
    const tree = (await this.github.rest.git.createTree({...this.repo, ...(this.tree ? {base_tree: this.tree} : {}),
      tree: [{path: FILE, mode: '100644', type: 'blob', content}, ...this.archives]})).data;
    const commit = (await this.github.rest.git.createCommit({...this.repo, tree: tree.sha, parents: this.head ? [this.head] : [],
      message: 'Checkpoint Claude wake dispatch state\n\nSkills: none (deterministic transport state)'})).data;
    try {
      if (this.head) await this.github.rest.git.updateRef({...this.repo, ref: `heads/${REF}`, sha: commit.sha, force: false});
      else await this.github.rest.git.createRef({...this.repo, ref: `refs/heads/${REF}`, sha: commit.sha});
    } catch (error) {
      if ([409, 422].includes(error.status)) {
        try { error.wakeConflict = (await this.github.rest.git.getRef({...this.repo, ref: `heads/${REF}`})).data.object.sha !== this.head; }
        catch { /* Permission/deletion errors are not safe retry signals. */ }
      }
      throw error;
    }
    this.head = commit.sha; this.tree = tree.sha; this.archives = [];
  }
}

async function mutate(makeStore, change) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const store = makeStore(), state = await store.load();
    const result = await change(state, store);
    if (!result.save) return result;
    try { await store.save(state); return result; }
    catch (error) { if (!error.wakeConflict || attempt === 5) throw error; }
  }
}

async function wake({github, context, root = process.cwd(), url = process.env.CLAUDE_ROUTINE_FIRE_URL,
  token = process.env.CLAUDE_ROUTINE_FIRE_TOKEN, now = Date.now(), fetcher, makeStore}) {
  const repo = context.repo, event = context.payload;
  if (context.eventName !== 'issue_comment' || event.action !== 'created') throw Error('Unsupported wake event');
  const id = String(event.comment.id), issue = event.issue.number, login = event.comment.user.login;
  if (!/^[1-9][0-9]{0,19}$/.test(id) || !Number.isSafeInteger(event.comment.id)
      || !Number.isSafeInteger(issue) || issue < 1
      || !Number.isSafeInteger(context.runId) || context.runId < 1) throw Error('Invalid wake request');
  if (login.toLowerCase() !== repo.owner.toLowerCase()) {
    const permission = (await github.rest.repos.getCollaboratorPermissionLevel({...repo, username: login})).data.permission;
    if (!['admin', 'maintain', 'write'].includes(permission)) throw Error('Only repository writers can wake Claude');
  }
  const command = parse(event.comment.body);
  const stores = makeStore || (() => new Ledger(github, repo));
  const report = record => github.rest.issues.createComment({...repo, issue_number: issue,
    body: `Claude wake ${record.id}: **${record.status}**. ${record.message}${record.session_url ? ` Provider-created session: ${record.session_url}. This is not proof the worker started or completed.` : ''} Ledger: ${REF}:${FILE}.`});
  if (command.command === 'close') {
    const result = await mutate(stores, async state => {
      const record = state.records.find(x => x.id === command.value);
      if (!record) throw Error('Unknown hot wake request; inspect the ledger/archive');
      if (record.status === 'closed') return {save: false, record};
      if ((await github.rest.actions.getWorkflowRun({...repo, run_id: record.run_id})).data.status !== 'completed') throw Error('The original dispatch job must stop before its slot is closed');
      record.status = 'closed'; record.closed_by = login; record.closed_at = new Date(now).toISOString();
      record.message = 'A repository writer released this dispatch slot after review. This does not certify task completion.';
      return {save: true, record};
    });
    await report(result.record); return result.record;
  }
  const source = brief(command.value, root);
  let ready = false, configError = false;
  try { ready = configuration(url, token); } catch { configError = true; }
  const text = `Authorized Claude wake request ${id}\nRepository: ${repo.owner}/${repo.repo}\nIssue: https://github.com/${repo.owner}/${repo.repo}/issues/${issue}\nBrief: ${command.value}\nSHA-256: ${source.sha256}\nSource commit: ${source.revision}\n\nRead the current shared coordination state and project rules before working. This starts a fresh session, not an old thread. The committed brief follows.\n\n${source.text}`;
  if (text.length > 65536) throw Error('Wake context exceeds 65536 characters');
  const reserved = await mutate(stores, async (state, store) => {
    const previous = state.records.find(x => x.id === id);
    if (previous || await store.archived(id)) return {save: false, record: previous || {id, status: 'archived', message: 'Already handled; no repeat fire.'}};
    state.attempts = state.attempts.filter(x => Number.isSafeInteger(x) && x > now - DAY);
    const active = state.records.find(x => ACTIVE.has(x.status));
    const record = {id, issue, run_id: context.runId, brief: command.value, sha256: source.sha256,
      revision: source.revision, created_at: new Date(now).toISOString(), status: 'reserved', message: 'Durable reservation recorded; provider acceptance is not yet confirmed.'};
    if (!ready) { record.status = 'not-configured'; record.message = configError ? 'Routine configuration is invalid; no provider request was sent.' : 'Routine URL/token is not configured; no provider request was sent.'; }
    else if (active) { record.status = 'blocked'; record.message = `Dispatch slot is held by request ${active.id}; no provider request was sent.`; }
    else if (state.attempts.length >= DAILY_CAP || state.attempts.some(x => x > now - COOLDOWN)) { record.status = 'blocked'; record.message = 'Wake cooldown or rolling daily limit reached; no provider request was sent.'; }
    if (state.records.length === MAX_RECORDS) {
      const index = state.records.findIndex(x => !ACTIVE.has(x.status));
      if (index < 0) throw Error('Wake ledger is full');
      const [old] = state.records.splice(index, 1);
      store.archives.push({path: `archive/${old.id}.json`, mode: '100644', type: 'blob', content: JSON.stringify(old, null, 2) + '\n'});
    }
    state.records.push(record);
    if (record.status === 'reserved') state.attempts.push(now);
    return {save: true, record, send: record.status === 'reserved'};
  });
  if (!reserved.send) { await report(reserved.record); return reserved.record; }
  const outcome = await fire({url, token, text, fetcher});
  const final = await mutate(stores, async state => {
    const record = state.records.find(x => x.id === id);
    if (!record || record.status !== 'reserved') throw Error('Wake reservation changed; do not repeat the provider request');
    Object.assign(record, outcome);
    record.message = outcome.status === 'submitted' ? 'Provider accepted a fresh-session trigger. Await an actual worker acknowledgment and result.'
      : outcome.status === 'rejected' ? 'Provider explicitly rejected the request; no automatic retry.' : 'Provider outcome is unconfirmed. Do not retry; a writer must investigate and close the slot.';
    return {save: true, record};
  });
  await report(final.record); return final.record;
}

module.exports = {REF, FILE, parse, brief, configuration, fire, Ledger, mutate, wake};
