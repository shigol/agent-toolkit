// Runs only from the trusted default branch; never from a pull-request checkout.
const fs = require('node:fs');
const path = require('node:path');
function briefPath(value, root = process.cwd()) {
  if (typeof value !== 'string' || !/^(?:codex|docs|tools)\/[A-Za-z0-9_./-]+\.md$/.test(value)
      || value.split('/').some(p => !p || p === '.' || p === '..')) throw Error('Invalid committed brief path');
  const base = fs.realpathSync(root), file = fs.realpathSync(path.join(base, value));
  if (!file.startsWith(base + path.sep) || !fs.statSync(file).isFile()
      || fs.statSync(file).size > 65536) throw Error('Brief must be a regular in-repository Markdown file, at most 64 KiB');
  return value;
}
function parse(body) {
  const lines = String(body).trim().split(/\r?\n/);
  if (lines.length !== 1) throw Error('Use one command line: /codex-run docs/path.md');
  const match = /^\/codex-run ([^ ]+)(?: (native|global|value-smoke|value))?$/.exec(lines[0]);
  if (!match) throw Error('Use /codex-run docs/path.md');
  return match[1];
}
async function dispatch({github, context, root = process.cwd()}) {
  const {owner, repo} = context.repo;
  const login = context.payload.comment.user.login;
  let trusted = login.toLowerCase() === owner.toLowerCase();
  if (!trusted) {
    const access = await github.rest.repos.getCollaboratorPermissionLevel({owner, repo, username: login});
    trusted = ['admin', 'maintain', 'write'].includes(access.data.permission);
  }
  if (!trusted) throw Error('Only repository writers can start Codex');
  const body = String(context.payload.comment.body).trim();
  const brief = briefPath(parse(body), root);
  const mode = /^\/codex-run [^ ]+ (native|global|value-smoke|value)$/.exec(body)?.[1] || 'task';
  const ref = context.payload.repository.default_branch;
  const issue = String(context.payload.issue.number), request = String(context.payload.comment.id);
  await github.rest.actions.createWorkflowDispatch({owner, repo, workflow_id: 'codex-task.yml', ref,
    inputs: {brief, mode, request_issue: issue, request_id: request}});
  await github.rest.issues.createComment({owner, repo, issue_number: Number(issue),
    body: `Codex request ${request} accepted from @${login}: ${brief} on ${ref}; mode=${mode}. ${mode === 'value' ? 'Fixed18-call quality sample; no quality result is assumed.' : mode === 'value-smoke' ? 'Two-call quality pilot.' : ''} Results will be posted here. Workflow: https://github.com/${owner}/${repo}/actions/workflows/codex-task.yml`});
}
module.exports = {briefPath, parse, dispatch};
