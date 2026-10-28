// Deterministic controller. Run only from the trusted default branch, never a PR checkout.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const STATE_REF = 'codex/continuity-state';
const STATE_FILE = 'state.json';
const ACTIVE = new Set(['pending', 'dispatching', 'queued', 'running', 'retry', 'unconfirmed']);
const TERMINAL = new Set(['complete', 'paused', 'blocked']);
const MAX_STATE_BYTES = 262144;
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const iso = ms => new Date(ms).toISOString();

function contractHashes(root, files) {
  if (!Array.isArray(files) || files.length > 10) throw Error('Invalid worker contract');
  const base = fs.realpathSync(root);
  return files.map(name => {
    if (typeof name !== 'string' || name.length > 240 || path.isAbsolute(name)
        || name.split('/').some(part => !part || part === '.' || part === '..')) throw Error('Invalid worker contract path');
    let target = base;
    for (const part of name.split('/')) {
      target = path.join(target, part);
      if (fs.lstatSync(target).isSymbolicLink()) throw Error('Symlinked worker contracts are not supported');
    }
    if (!fs.statSync(target).isFile() || fs.statSync(target).size > 65536) throw Error('Invalid worker contract file');
    return {path: name, sha256: hash(fs.readFileSync(target))};
  });
}

function regular(root, value, extension) {
  if (typeof value !== 'string' || value.length > 240 || !new RegExp(`^(?:codex|docs|tools)/[A-Za-z0-9_./-]+\\.${extension}$`).test(value)
      || value.split('/').some(p => !p || p.startsWith('.'))) throw Error('Invalid committed path');
  const base = fs.realpathSync(root);
  let file = base;
  for (const part of value.split('/')) {
    file = path.join(file, part);
    if (fs.lstatSync(file).isSymbolicLink()) throw Error('Symlinked plans and briefs are not supported');
  }
  if (!fs.statSync(file).isFile() || fs.statSync(file).size > 65536) throw Error('Committed file must be regular and at most64KiB');
  return fs.readFileSync(file);
}

function keys(value, allowed) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || Object.keys(value).some(k => !allowed.includes(k))) throw Error('Unknown or malformed plan fields');
}

function integer(value, min, max, label) {
  if (!Number.isSafeInteger(value) || value < min || value > max) throw Error(`Invalid ${label}`);
  return value;
}

function loadPlan(root, file) {
  const raw = regular(root, file, 'json');
  const plan = JSON.parse(raw);
  keys(plan, ['schema', 'title', 'limits', 'steps']);
  if (plan.schema !== 1 || typeof plan.title !== 'string' || !plan.title.trim() || plan.title.length > 160) throw Error('Invalid plan schema/title');
  keys(plan.limits, ['max_runs', 'max_minutes', 'max_input_tokens']);
  const limits = {
    max_runs: integer(plan.limits.max_runs, 1, 12, 'run limit'),
    max_minutes: integer(plan.limits.max_minutes, 5, 720, 'elapsed-minute limit'),
    max_input_tokens: integer(plan.limits.max_input_tokens, 1, 5000000, 'observed input-token limit')
  };
  if (!Array.isArray(plan.steps) || !plan.steps.length || plan.steps.length > 8) throw Error('Plan needs one to eight steps');
  const names = new Set();
  const steps = plan.steps.map(step => {
    keys(step, ['id', 'brief', 'attempts', 'review']);
    if (typeof step.id !== 'string' || !/^[a-z][a-z0-9-]{0,39}$/.test(step.id) || names.has(step.id)) throw Error('Invalid/duplicate step ID');
    names.add(step.id);
    if (!['required', 'none'].includes(step.review)) throw Error('Each step must declare its review policy');
    return {id: step.id, brief: step.brief, attempts: integer(step.attempts, 1, 2, 'attempt limit'),
      review: step.review, sha256: hash(regular(root, step.brief, 'md'))};
  });
  if (limits.max_runs < steps.length) throw Error('Run budget cannot cover every planned step');
  return {title: plan.title, limits, steps, path: file, sha256: hash(raw)};
}

function parse(body) {
  const match = /^\/codex-(plan|pause|resume|accept|archive) ([A-Za-z0-9_./-]+)$/.exec(String(body).trim());
  if (!match) throw Error('Use one line: /codex-plan docs/plan.json, or /codex-pause|resume|accept|archive REQUEST_ID');
  if (match[1] !== 'plan' && !/^\d+$/.test(match[2])) throw Error('Request ID must be numeric');
  return {command: match[1], value: match[2]};
}

function createRecord(plan, request, issue, author, revision, now) {
  return {schema: 1, id: request, issue, author, revision, plan, status: 'pending', step: 0, attempt: 0,
    total_runs: 0, input_tokens: 0, started_at: iso(now), expires_at: iso(now + plan.limits.max_minutes * 60000),
    observed_at: iso(now), history: [], commands: [], message: 'Plan registered; no worker is running yet.'};
}

function receipt(body, request, runId) {
  const marker = `<!-- codex-result:${runId} -->\n`;
  if (!body.startsWith(marker) || body.length > 16384) return null;
  const text = body.slice(marker.length).split('\n')[0];
  let data;
  try { data = JSON.parse(text); } catch { return null; }
  if (String(data.request_id) !== request || data.run_id !== runId
      || !['success', 'failure', 'cancelled', 'timed_out', 'skipped'].includes(data.worker)
      || typeof data.has_patch !== 'boolean' || !Number.isSafeInteger(data.held_count) || data.held_count < 0
      || !Number.isSafeInteger(data.input_tokens) || data.input_tokens < 0
      || typeof data.usage_known !== 'boolean'
      || (data.branch && data.branch !== `codex/task-${runId}`)) return null;
  return {run_id: data.run_id, request_id: data.request_id, worker: data.worker,
    save: ['success', 'failure', 'skipped', 'cancelled'].includes(data.save) ? data.save : 'unknown',
    has_patch: data.has_patch, held_count: data.held_count, input_tokens: data.input_tokens,
    usage_known: data.usage_known, branch: data.branch || '',
    checkpoint_status: ['running', 'execution_complete', 'failed', 'timeout', 'stalled', 'interrupted', 'not_available'].includes(data.checkpoint_status) ? data.checkpoint_status : 'unknown'};
}

// Pure transition function. API effects are returned, not performed here.
function advance(record, observed, now) {
  const next = structuredClone(record), effects = [];
  const step = next.plan.steps[next.step];
  next.observed_at = iso(now);
  if (next.status === 'review' || next.status === 'complete') return {record: next, effects};
  const expired = now >= Date.parse(next.expires_at);
  if (expired && next.status !== 'complete') {
    next.status = 'paused'; next.message = 'Elapsed-time budget exhausted; no further worker will be started.';
    if (observed.run && observed.run.status !== 'completed') effects.push({type: 'cancel', id: observed.run.id});
    return {record: next, effects};
  }
  if (TERMINAL.has(next.status)) return {record: next, effects};
  if (observed.changed) {
    next.status = 'paused'; next.message = 'The committed plan, brief or worker contract changed. Submit a newly reviewed plan to continue.';
    if (observed.run && observed.run.status !== 'completed') effects.push({type: 'cancel', id: observed.run.id});
    return {record: next, effects};
  }
  if (next.status === 'pending' || next.status === 'retry') {
    if (next.usage_unknown || next.total_runs >= next.plan.limits.max_runs || next.input_tokens >= next.plan.limits.max_input_tokens
        || next.attempt >= step.attempts) {
      next.status = 'blocked'; next.message = 'Attempt/run/observed-usage budget exhausted; no more automatic retries.';
      return {record: next, effects};
    }
    next.attempt += 1; next.total_runs += 1;
    next.run_id = null; next.run_url = ''; next.run_revision = null;
    delete next.no_jobs_observed_at;
    next.request_id = `continuity-${next.id}-${next.step}-${next.attempt}`;
    next.dispatched_at = iso(now); next.status = 'dispatching';
    next.message = 'Dispatch reserved; waiting for a verified Actions run.';
    effects.push({type: 'dispatch', request_id: next.request_id, brief: step.brief, issue: next.issue});
    return {record: next, effects};
  }
  const run = observed.run;
  if (!run) {
    if (now - Date.parse(next.dispatched_at) > 10 * 60000) {
      next.status = 'unconfirmed';
      next.message = 'Dispatch has no observable run. It will not be duplicated; the watchdog is checking until the deadline.';
    }
    return {record: next, effects};
  }
  next.run_id = run.id; next.run_url = run.html_url;
  next.run_revision = run.head_sha || null;
  if (run.status !== 'completed') {
    next.status = run.status === 'queued' || run.status === 'waiting' ? 'queued' : 'running';
    next.message = next.status === 'queued' ? 'Actions run verified queued; execution has not started.' : 'Actions run verified active; this is not a completion claim.';
    if (run.run_started_at && now - Date.parse(run.run_started_at) > 50 * 60000) {
      effects.push({type: 'cancel', id: run.id});
      next.message = 'Active run exceeded the worker deadline; cancellation requested. Waiting for its saved result.';
    }
    return {record: next, effects};
  }
  const result = observed.receipt;
  if (!result) {
    next.message = 'Run ended; waiting for the trusted result/checkpoint callback.';
    if (now - Date.parse(run.updated_at) > 10 * 60000) {
      next.status = 'blocked'; next.message = 'Run ended without a valid result/checkpoint. Review the run before any restart.';
    }
    return {record: next, effects};
  }
  if (next.history.some(x => x.run_id === run.id)) return {record: next, effects};
  next.history.push({run_id: run.id, revision: run.head_sha || null, request_id: next.request_id, result, recorded_at: iso(now)});
  next.input_tokens += result.input_tokens;
  next.usage_unknown ||= !result.usage_known;
  next.branch = result.branch || '';
  if (result.has_patch || result.held_count) {
    next.status = 'review'; next.message = 'Saved work needs independent review. A successful worker is not accepted project completion.';
    return {record: next, effects};
  }
  if (!result.usage_known) {
    next.status = 'blocked'; next.message = 'Worker usage is unknown; review its checkpoint before authorising more work.';
    return {record: next, effects};
  }
  if (run.conclusion !== 'success' || result.worker !== 'success') {
    next.status = 'retry'; next.message = 'Failed attempt saved; a bounded retry is eligible.';
    return {record: next, effects};
  }
  if (step.review === 'required') {
    next.status = 'review'; next.message = 'Saved work needs independent review. A successful worker is not accepted project completion.';
    return {record: next, effects};
  }
  if (next.step + 1 === next.plan.steps.length) {
    next.status = 'review'; next.message = 'All planned executions ended. Final result acceptance is still required.';
  } else {
    next.step += 1; next.attempt = 0; next.status = 'pending'; next.branch = '';
    next.message = 'The next committed step is eligible; no unreviewed code was merged.';
  }
  return {record: next, effects};
}

class Store {
  constructor(github, repo) { this.github = github; this.repo = repo; this.head = null; this.tree = null; this.archives = []; }
  async load() {
    try {
      const ref = await this.github.rest.git.getRef({...this.repo, ref: `heads/${STATE_REF}`});
      this.head = ref.data.object.sha;
      this.tree = (await this.github.rest.git.getCommit({...this.repo, commit_sha: this.head})).data.tree.sha;
      const item = await this.github.rest.repos.getContent({...this.repo, path: STATE_FILE, ref: this.head});
      if (Array.isArray(item.data) || item.data.size > MAX_STATE_BYTES || item.data.encoding !== 'base64') throw Error('Invalid continuity state');
      const state = JSON.parse(Buffer.from(item.data.content, 'base64').toString());
      if (state.schema !== 1 || !Array.isArray(state.records) || state.records.length > 20) throw Error('Invalid continuity state schema');
      return state;
    } catch (error) {
      if (error.status === 404 && !this.head) return {schema: 1, records: []};
      throw error;
    }
  }
  archive(record) {
    if ((record.status !== 'complete' && !record.archived_by) || !/^\d+$/.test(record.id)) throw Error('Only accepted or writer-reviewed plans may be archived');
    this.archives.push({path: `archive/${record.id}.json`, mode: '100644', type: 'blob', content: JSON.stringify(record, null, 2) + '\n'});
  }
  async archived(id) {
    if (!this.head) return false;
    try {
      const item = await this.github.rest.repos.getContent({...this.repo, path: `archive/${id}.json`, ref: this.head});
      if (Array.isArray(item.data) || item.data.type !== 'file') throw Error('Invalid archived continuity record');
      return true;
    } catch (error) {
      if (error.status === 404) return false;
      throw error;
    }
  }
  async save(state) {
    const content = JSON.stringify(state, null, 2) + '\n';
    if (Buffer.byteLength(content) > MAX_STATE_BYTES) throw Error('Continuity state exceeds its bounded size');
    const tree = await this.github.rest.git.createTree({...this.repo, ...(this.tree ? {base_tree: this.tree} : {}),
      tree: [{path: STATE_FILE, mode: '100644', type: 'blob', content}, ...this.archives]});
    const commit = await this.github.rest.git.createCommit({...this.repo, message: 'Codex: checkpoint unattended work state\n\nSkills: none (deterministic controller state)',
      tree: tree.data.sha, parents: this.head ? [this.head] : []});
    try {
      if (this.head) await this.github.rest.git.updateRef({...this.repo, ref: `heads/${STATE_REF}`, sha: commit.data.sha, force: false});
      else await this.github.rest.git.createRef({...this.repo, ref: `refs/heads/${STATE_REF}`, sha: commit.data.sha});
    } catch (error) {
      if ([409, 422].includes(error.status)) {
        try {
          const latest = await this.github.rest.git.getRef({...this.repo, ref: `heads/${STATE_REF}`});
          if (latest.data.object.sha !== this.head) error.continuityConflict = true;
        } catch { /* A permission/deletion error is not a retryable lease conflict. */ }
      }
      throw error;
    }
    this.head = commit.data.sha;
    this.tree = tree.data.sha; this.archives = [];
  }
}

async function writer(github, repo, login) {
  if (login.toLowerCase() === repo.owner.toLowerCase()) return true;
  const permission = await github.rest.repos.getCollaboratorPermissionLevel({...repo, username: login});
  return ['admin', 'maintain', 'write'].includes(permission.data.permission);
}

function summary(record) {
  return `<!-- codex-continuity:${record.id} -->\n` +
    `Codex plan ${record.id}: **${record.status}**; step${record.step + 1}/${record.plan.steps.length}, ` +
    `runs${record.total_runs}/${record.plan.limits.max_runs}. ${record.message}\n` +
    (record.run_url ? `Last verified run: ${record.run_url}. ` : '') +
    `Checkpoint: \`${STATE_REF}\`, \`${STATE_FILE}\` (accepted archives: \`archive/${record.id}.json\`). Observed ${record.observed_at}; deadline ${record.expires_at}. ` +
    'No automatic merge or deployment. An unsupported idle chat does not continue this plan.';
}

async function report(github, repo, record) {
  const body = summary(record);
  const first = !record.comment_id;
  if (!first) await github.rest.issues.updateComment({...repo, comment_id: record.comment_id, body});
  else record.comment_id = (await github.rest.issues.createComment({...repo, issue_number: record.issue, body})).data.id;
  const changed = record.reported_status && record.reported_status !== record.status
    && ['review', 'paused', 'blocked', 'complete'].includes(record.status);
  const due = ACTIVE.has(record.status) && record.last_notice_at
    && Date.parse(record.observed_at) - Date.parse(record.last_notice_at) >= 30 * 60000;
  if (!first && (changed || due)) await github.rest.issues.createComment({...repo, issue_number: record.issue,
    body: `Plan ${record.id} update: ${record.status}. ${record.message}\n${record.run_url || 'No Actions run is yet verified.'}\nCheckpoint/status: ${record.comment_id}. No automatic merge or deployment.`});
  if (first || changed || due) record.last_notice_at = record.observed_at;
  record.reported_status = record.status;
}

async function controllerOnce({github, context, root = process.cwd(), now = Date.now(), worker = 'codex-task.yml', relatedWorkers, watchdog = true, contractPaths, store}) {
  const repo = context.repo;
  store ||= new Store(github, repo);
  const state = await store.load();
  const event = context.payload;
  relatedWorkers ||= fs.existsSync(path.join(root, '.github/workflows/codex-build.yml')) ? ['codex-build.yml'] : [];
  const workers = [worker, ...relatedWorkers];
  if (workers.length > 4 || workers.some(name => !/^[A-Za-z0-9_-]+\.yml$/.test(name))) throw Error('Invalid related worker contract');
  contractPaths ||= [`.github/workflows/${worker}`, '.github/workflows/codex-continuity.yml',
    '.github/workflows/codex-continuity-watchdog.yml', '.github/scripts/codex_continuity.cjs',
    '.github/scripts/codex_task_run.py', '.github/scripts/codex_task_patch.py', '.github/scripts/codex_result.cjs',
    ...relatedWorkers.map(name => `.github/workflows/${name}`)];
  let armed = false;
  async function enableWatchdog() {
    if (watchdog && !armed) {
      // Arm independent recovery before saving runnable work or dispatching a model.
      await github.rest.actions.enableWorkflow({...repo, workflow_id: 'codex-continuity-watchdog.yml'});
      state.watchdog_enabled = true; armed = true;
    }
  }
  if (context.eventName === 'issue_comment') {
    const command = parse(event.comment.body);
    if (!await writer(github, repo, event.comment.user.login)) throw Error('Only repository writers can manage unattended plans');
    if (command.command === 'plan') {
      const id = String(event.comment.id);
      if (!state.records.some(x => x.id === id) && !(store.archived && await store.archived(id))) {
        if (state.records.filter(x => !TERMINAL.has(x.status)).length >= 10) throw Error('Continuity registry has ten unfinished plans; review them before adding more');
        if (state.records.length >= 20) {
          const archived = state.records.findIndex(record => record.status === 'complete');
          if (archived < 0 || !store.archive) throw Error('Continuity registry is full of unresolved plans; review them before adding more');
          store.archive(state.records[archived]); state.records.splice(archived, 1);
          await store.save(state);
        }
        const plan = loadPlan(root, command.value);
        await enableWatchdog();
        const record = createRecord(plan, id, event.issue.number, event.comment.user.login, process.env.GITHUB_SHA || '', now);
        record.contracts = contractHashes(root, contractPaths);
        state.records.push(record);
        await store.save(state);
      }
    } else {
      const record = state.records.find(x => x.id === command.value);
      if (!record) {
        if (!(store.archived && await store.archived(command.value))) throw Error('Unknown continuity request');
      } else if (!(record.commands || []).includes(String(event.comment.id))) {
        record.commands ||= [];
        if (record.commands.length >= 128) throw Error('This plan has reached its command limit; archive and submit a reviewed replacement');
        record.commands.push(String(event.comment.id));
        if (command.command === 'archive') {
          if (!TERMINAL.has(record.status)) throw Error('Pause/finish and review this plan before archiving it');
          if (record.request_id && !record.history.some(item => item.request_id === record.request_id)) {
            if (!record.run_id) throw Error('An unconfirmed dispatch cannot be archived');
            const actual = await github.rest.actions.getWorkflowRun({...repo, run_id: record.run_id});
            if (actual.data.status !== 'completed') throw Error('The worker must be confirmed stopped before archiving');
          }
          record.archived_by = event.comment.user.login; record.archived_at = iso(now);
          store.archive(record); state.records.splice(state.records.indexOf(record), 1);
          await store.save(state);
          await github.rest.issues.createComment({...repo, issue_number: record.issue,
            body: `Plan ${record.id} archived by @${record.archived_by}: ${STATE_REF}:archive/${record.id}.json. Its ${record.status} outcome and evidence were preserved; no work was marked complete by archival.`});
        } else if (command.command === 'pause') {
          record.status = 'paused'; record.message = 'Paused by a repository writer; no new work will start.';
          if (record.run_id) await github.rest.actions.cancelWorkflowRun({...repo, run_id: record.run_id}).catch(e => { if (![409, 422].includes(e.status)) throw e; });
        } else if (command.command === 'resume') {
          if (record.status !== 'paused' || record.request_id && !record.history.some(x => x.request_id === record.request_id)) throw Error('Cannot resume an unconfirmed or still-active run');
          record.status = 'retry'; record.message = 'Resume requested; original budgets still apply.';
        } else {
          if (record.status !== 'review') throw Error('Only a saved review checkpoint can be accepted');
          if (record.branch) {
            const branch = await github.rest.git.getRef({...repo, ref: `heads/${record.branch}`});
            const pulls = await github.rest.pulls.list({...repo, state: 'closed', head: `${repo.owner}:${record.branch}`, per_page: 20});
            if (!pulls.data.some(pr => pr.merged_at && pr.head.sha === branch.data.object.sha
                && pr.base.ref === event.repository.default_branch)) throw Error('Review branch must be merged through its reviewed PR before dependent work continues');
          }
          if (record.step + 1 === record.plan.steps.length) {
            record.status = 'complete'; record.message = 'Final results accepted by a repository writer.';
          } else {
            record.step += 1; record.attempt = 0; record.status = 'pending'; record.branch = '';
            record.message = 'Reviewed step accepted; next committed step is eligible.';
          }
        }
        if (command.command !== 'archive') {
          if (ACTIVE.has(record.status)) await enableWatchdog();
          await report(github, repo, record);
          await store.save(state);
        }
      }
    }
  }
  if (state.records.some(record => ACTIVE.has(record.status))) await enableWatchdog();
  let runs;
  async function observedRuns() {
    if (!runs) {
      const groups = await Promise.all(workers.map(async name => (await github.rest.actions.listWorkflowRuns({...repo, workflow_id: name, per_page: 100})).data.workflow_runs
        .map(item => ({...item, worker: name}))));
      runs = groups.flat();
    }
    return runs;
  }
  async function busy(record) {
    const reserved = state.records.some(other => other.id !== record.id
      && ['dispatching', 'queued', 'running', 'unconfirmed'].includes(other.status));
    return reserved || (await observedRuns()).some(item => item.status !== 'completed'
      && item.head_branch === event.repository.default_branch
      && item.head_repository?.full_name === `${repo.owner}/${repo.repo}`);
  }
  for (let index = 0; index < state.records.length; index += 1) {
    let record = state.records[index];
    if (!ACTIVE.has(record.status) && record.status !== 'review' && !(record.status === 'paused' && record.request_id)) continue;
    let changed = false;
    try {
      changed = hash(regular(root, record.plan.path, 'json')) !== record.plan.sha256
        || record.plan.steps.some(step => hash(regular(root, step.brief, 'md')) !== step.sha256)
        || JSON.stringify(contractHashes(root, record.contracts.map(item => item.path))) !== JSON.stringify(record.contracts);
    } catch { changed = true; }
    let run = null, result = null;
    const stoppedByBudget = now >= Date.parse(record.expires_at) || record.usage_unknown
      || record.total_runs >= record.plan.limits.max_runs || record.input_tokens >= record.plan.limits.max_input_tokens
      || record.attempt >= record.plan.steps[record.step].attempts;
    if ((record.status === 'pending' || record.status === 'retry') && !changed && !stoppedByBudget) {
      if (await busy(record)) {
        record.observed_at = iso(now); record.message = 'Waiting in the durable repository queue; another worker is reserved/active. No new dispatch was made.';
        await report(github, repo, record); await store.save(state); continue;
      }
    }
    if (record.request_id && record.status !== 'pending' && record.status !== 'retry') {
      const matches = (await observedRuns()).filter(item => item.worker === worker && item.event === 'workflow_dispatch'
        && item.head_branch === event.repository.default_branch
        && item.head_repository?.full_name === `${repo.owner}/${repo.repo}`
        && /^[a-f0-9]{40}$/.test(item.head_sha || '')
        && item.display_title.startsWith(`Codex request ${record.request_id} `));
      if (matches.length > 1) {
        for (const item of matches) if (item.status !== 'completed') await github.rest.actions.cancelWorkflowRun({...repo, run_id: item.id});
        record.status = 'blocked'; record.message = 'Duplicate dispatch detected; active duplicates cancelled. Independent review required.';
        await report(github, repo, record); await store.save(state); continue;
      }
      run = matches[0] || null;
      if (run?.status === 'completed') {
        const comments = await github.paginate(github.rest.issues.listComments, {...repo, issue_number: record.issue, per_page: 100});
        result = comments.filter(item => item.user.login === 'github-actions[bot]')
          .map(item => receipt(item.body, record.request_id, run.id)).find(Boolean) || null;
        if (!result && ['cancelled', 'failure'].includes(run.conclusion)) {
          const jobs = (await github.rest.actions.listJobsForWorkflowRun({...repo, run_id: run.id, per_page: 100})).data.jobs;
          const executeSkipped = jobs.some(job => job.name === 'run'
            && job.steps?.some(step => step.name === 'Execute one committed brief' && step.conclusion === 'skipped'));
          const stableNoJobs = !jobs.length && record.no_jobs_observed_at
            && now - Date.parse(record.no_jobs_observed_at) >= 60000;
          if (!jobs.length && !record.no_jobs_observed_at) record.no_jobs_observed_at = iso(now);
          if (stableNoJobs || executeSkipped) result = {run_id: run.id, request_id: record.request_id,
            worker: 'cancelled', save: 'skipped', has_patch: false, held_count: 0, input_tokens: 0,
            usage_known: true, branch: '', checkpoint_status: 'not_available',
            not_started_evidence: stableNoJobs ? 'repeated_no_jobs' : 'execute_step_skipped'};
        }
      }
    }
    if (record.status === 'paused' && record.request_id) {
      if (run && run.status !== 'completed') {
        await github.rest.actions.cancelWorkflowRun({...repo, run_id: run.id}).catch(e => { if (![409, 422].includes(e.status)) throw e; });
      } else if (run && result && !record.history.some(x => x.run_id === run.id)) {
        record.history.push({run_id: run.id, revision: run.head_sha || null, request_id: record.request_id, result, recorded_at: iso(now)});
        record.input_tokens += result.input_tokens;
        record.usage_unknown ||= !result.usage_known;
        record.run_id = run.id; record.run_url = run.html_url; record.observed_at = iso(now);
        if (result.has_patch || result.held_count) {
          record.branch = result.branch || ''; record.status = 'review';
          record.message = 'Paused worker ended with saved work. Review is required before any restart.';
        }
      }
      await report(github, repo, record); await store.save(state); continue;
    }
    let transition = advance(record, {run, receipt: result, changed}, now);
    record = state.records[index] = transition.record;
    if (['pending', 'retry'].includes(record.status) && !transition.effects.length) {
      if (await busy(record)) record.message = 'Waiting in the durable repository queue; another worker is reserved/active. No new dispatch was made.';
      else {
        transition = advance(record, {}, now);
        record = state.records[index] = transition.record;
      }
    }
    // Reserve/persist before an external dispatch. An uncertain dispatch is never retried blindly.
    await store.save(state);
    for (const effect of transition.effects) {
      if (effect.type === 'cancel') await github.rest.actions.cancelWorkflowRun({...repo, run_id: effect.id}).catch(e => { if (![409, 422].includes(e.status)) throw e; });
      if (effect.type === 'dispatch') {
        try {
          await github.rest.actions.createWorkflowDispatch({...repo, workflow_id: worker,
            ref: event.repository.default_branch, inputs: {brief: effect.brief, mode: 'task',
              request_issue: String(effect.issue), request_id: effect.request_id,
              previous_run: record.history.length ? String(record.history.at(-1).run_id) : ''}});
          record.status = 'dispatching'; record.message = 'Dispatch accepted; waiting to verify the actual run.';
        } catch {
          record.status = 'unconfirmed'; record.message = 'Dispatch outcome is uncertain. It will be reconciled, not duplicated.';
        }
      }
    }
    await report(github, repo, record);
    await store.save(state);
  }
  if (watchdog) {
    const needed = state.records.some(record => ACTIVE.has(record.status)
      || record.status === 'paused' && record.request_id && !record.history.some(item => item.request_id === record.request_id));
    if (state.watchdog_enabled !== needed) {
      const action = needed ? 'enableWorkflow' : 'disableWorkflow';
      await github.rest.actions[action]({...repo, workflow_id: 'codex-continuity-watchdog.yml'});
      state.watchdog_enabled = needed;
      await store.save(state);
    }
  }
  return state;
}

async function controller(options) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    try {
      return await controllerOnce(options);
    } catch (error) {
      if (!error.continuityConflict || attempt === 5) throw error;
      // Only deterministic state reconciliation retries. Durable attempt IDs prevent extra model calls.
      await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100 * (attempt + 1)));
    }
  }
}

module.exports = {STATE_REF, STATE_FILE, regular, loadPlan, parse, createRecord, receipt, advance, Store, summary, controller, contractHashes};
