const {test} = require('node:test');
const assert = require('node:assert/strict');
const {eligiblePR, onlyGitlink, checksPassed, eligibleToolkitDiff, run} = require('./merge_toolkit.cjs');
const pr = {state: 'open', draft: false, user: {login: 'dependabot[bot]'},
  head: {repo: {full_name: 'shigol/career'}, sha: 'checked-head'}, base: {ref: 'main'}};
test('only the same-repository bot PR at the validated head is eligible', () => {
  assert.equal(eligiblePR(pr, 'shigol/career', 'checked-head'), true);
  for (const changed of [
    {...pr, user: {login: 'shigol'}}, {...pr, draft: true}, {...pr, state: 'closed'},
    {...pr, head: {...pr.head, sha: 'new-head'}},
    {...pr, head: {...pr.head, repo: {full_name: 'fork/career'}}},
    {...pr, base: {ref: 'other'}},
  ]) assert.equal(eligiblePR(changed, 'shigol/career', 'checked-head'), false);
});
test('additional files, additions and deletions require human review', () => {
  const link = {filename: '.agent-toolkit', status: 'modified'};
  assert.equal(onlyGitlink([link]), true);
  assert.equal(onlyGitlink([link, {filename: '.github/workflows/change.yml'}]), false);
  assert.equal(onlyGitlink([{...link, status: 'removed'}]), false);
  assert.equal(onlyGitlink([]), false);
});
test('pending, failed or absent checks prevent merging', () => {
  const success = {status: 'completed', conclusion: 'success'};
  assert.equal(checksPassed([success], []), true);
  assert.equal(checksPassed([], []), false);
  assert.equal(checksPassed([success, {status: 'in_progress'}], []), false);
  assert.equal(checksPassed([{status: 'completed', conclusion: 'failure'}], []), false);
  assert.equal(checksPassed([success], [{context: 'deploy', state: 'pending'}]), false);
  assert.equal(checksPassed([success], [
    {context: 'deploy', state: 'success'}, {context: 'deploy', state: 'failure'},
  ]), true);
});
test('manual and failed runs cannot authorize a merge', async () => {
  for (const event of ['workflow_dispatch', 'push', 'pull_request_target']) {
    await run({context: {repo: {owner: 'shigol', repo: 'career'}, payload: {
      workflow_run: {event, conclusion: 'success'},
    }}}); // No API client: any attempted request fails the test.
  }
});
test('vendored Markdown and manifest/code changes stay held even after green validation', () => {
  const comparison = {status: 'ahead', behind_by: 0,
    files: [{filename: 'catalog/humanizer.md', status: 'modified'}]};
  assert.equal(eligibleToolkitDiff(comparison), true);
  for (const filename of ['vendor/humanizer/skills/SKILL.md', 'vendor/new-reference.md',
                          'toolkit.lock.json', 'scripts/toolkit.py']) {
    assert.equal(eligibleToolkitDiff({...comparison, files: [{filename, status: 'modified'}]}), false);
  }
  assert.equal(eligibleToolkitDiff({...comparison, status: 'diverged'}), false);
  assert.equal(eligibleToolkitDiff({...comparison, behind_by: 1}), false);
  assert.equal(eligibleToolkitDiff({...comparison, files: []}), false);
  assert.equal(eligibleToolkitDiff({...comparison, files: Array(100).fill(comparison.files[0])}), false);
  assert.equal(eligibleToolkitDiff({...comparison, files: [{filename: 'README.md', status: 'removed'}]}), false);
});
test('trusted merge controller independently holds vendor pins despite green candidate checks', async () => {
  for (const filename of ['vendor/example/SKILL.md', 'catalog/humanizer.md']) {
    let merges = 0;
    const associated = () => {}, files = () => {}, checks = () => {}, statuses = () => {}, reviews = () => {};
    const github = {
      paginate: async fn => fn === associated ? [{number: 7}] : fn === files
        ? [{filename: '.agent-toolkit', status: 'modified'}] : fn === checks
          ? [{status: 'completed', conclusion: 'success'}] : [],
      rest: {
        repos: {listPullRequestsAssociatedWithCommit: associated, listCommitStatusesForRef: statuses,
          compareCommitsWithBasehead: async () => ({data: {status: 'ahead', behind_by: 0,
            files: [{filename, status: 'modified'}]}})},
        pulls: {get: async () => ({data: {...pr, base: {...pr.base, sha: 'base'}, mergeable_state: 'clean'}}),
          listFiles: files, listReviews: reviews, merge: async () => {merges++; return {data: {merged: true}};}},
        git: {getCommit: async ({commit_sha}) => ({data: {tree: {sha: commit_sha}}}),
          getTree: async ({tree_sha}) => ({data: {tree: [{path: '.agent-toolkit', mode: '160000', type: 'commit', sha: tree_sha}]}})},
        actions: {getWorkflowRun: async () => ({data: {head_sha: 'checked-head', conclusion: 'success'}})},
        checks: {listForRef: checks},
      },
    };
    await run({github, core: {info: () => {}}, context: {repo: {owner: 'shigol', repo: 'career'}, payload: {
      workflow_run: {id: 1, event: 'pull_request', conclusion: 'success', head_sha: 'checked-head',
        path: '.github/workflows/agent-toolkit-check.yml', head_repository: {full_name: 'shigol/career'}},
    }}});
    assert.equal(merges, filename.startsWith('vendor/') ? 0 : 1);
  }
});
