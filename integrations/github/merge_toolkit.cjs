// Runs only from the default branch after the read-only validation workflow.
// Never checks out a PR, executes toolkit code, or consumes PR artifacts.
function eligiblePR(pr, repository, head) {
  return pr.state === 'open' && !pr.draft && pr.user.login === 'dependabot[bot]'
    && pr.head.repo?.full_name === repository && pr.head.sha === head
    && pr.base.ref === 'main';
}

function onlyGitlink(files) {
  return files.length === 1 && files[0].filename === '.agent-toolkit'
    && files[0].status === 'modified';
}

function checksPassed(checks, statuses) {
  // Ignore superseded commit statuses, but never ignore pending or failed checks.
  const latest = new Map();
  for (const s of statuses) if (!latest.has(s.context)) latest.set(s.context, s);
  return checks.length > 0
    && checks.every(c => c.status === 'completed' && ['success', 'neutral', 'skipped'].includes(c.conclusion))
    && [...latest.values()].every(s => s.state === 'success');
}

function eligibleToolkitDiff(comparison) {
  // Never trust a candidate workflow's eligibility output or PR artifacts.
  // GitHub returns at most 300 files; a large/truncated comparison requires review.
  const files = comparison.files;
  return comparison.status === 'ahead' && comparison.behind_by === 0
    && Array.isArray(files) && files.length > 0 && files.length < 100
    && files.every(file => ['added', 'modified'].includes(file.status)
      && file.filename.endsWith('.md') && !file.filename.startsWith('vendor/'));
}

async function run({github, context, core}) {
  const run = context.payload.workflow_run;
  const {owner, repo} = context.repo;
  const repository = `${owner}/${repo}`;
  if (run.conclusion !== 'success' || run.event !== 'pull_request'
      || run.path !== '.github/workflows/agent-toolkit-check.yml'
      || run.head_repository?.full_name !== repository) return;
  const linked = await github.paginate(github.rest.repos.listPullRequestsAssociatedWithCommit,
    {owner, repo, commit_sha: run.head_sha, per_page: 100});
  for (const candidate of linked) {
    const pull_number = candidate.number;
    for (let attempt = 0; attempt < 18; attempt++) {
      const {data: pr} = await github.rest.pulls.get({owner, repo, pull_number});
      if (!eligiblePR(pr, repository, run.head_sha)) break;
      const files = await github.paginate(github.rest.pulls.listFiles,
        {owner, repo, pull_number, per_page: 100});
      if (!onlyGitlink(files)) break;
      const {data: commit} = await github.rest.git.getCommit({owner, repo, commit_sha: pr.head.sha});
      const {data: tree} = await github.rest.git.getTree({owner, repo, tree_sha: commit.tree.sha});
      const entry = tree.tree.find(e => e.path === '.agent-toolkit');
      if (entry?.mode !== '160000' || entry.type !== 'commit') break;
      const {data: baseCommit} = await github.rest.git.getCommit({owner, repo, commit_sha: pr.base.sha});
      const {data: baseTree} = await github.rest.git.getTree({owner, repo, tree_sha: baseCommit.tree.sha});
      const previous = baseTree.tree.find(e => e.path === '.agent-toolkit');
      if (previous?.mode !== '160000' || previous.type !== 'commit') break;
      const {data: comparison} = await github.rest.repos.compareCommitsWithBasehead({
        owner: 'shigol', repo: 'agent-toolkit', basehead: `${previous.sha}...${entry.sha}`,
      });
      if (!eligibleToolkitDiff(comparison)) {
        core.info(`Left #${pull_number} open: toolkit source/manifest/code changes require independent review.`);
        break;
      }
      // The completed validation must belong to this workflow and this exact head.
      const {data: validation} = await github.rest.actions.getWorkflowRun({owner, repo, run_id: run.id});
      if (validation.head_sha !== pr.head.sha || validation.conclusion !== 'success') break;
      const checks = await github.paginate(github.rest.checks.listForRef,
        {owner, repo, ref: pr.head.sha, filter: 'latest', per_page: 100});
      const statuses = await github.paginate(github.rest.repos.listCommitStatusesForRef,
        {owner, repo, ref: pr.head.sha, per_page: 100});
      const reviews = await github.paginate(github.rest.pulls.listReviews,
        {owner, repo, pull_number, per_page: 100});
      const decisions = new Map();
      for (const review of reviews) {
        if (['APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'].includes(review.state)) {
          decisions.set(review.user.login, review.state);
        }
      }
      if ([...decisions.values()].includes('CHANGES_REQUESTED')) break;
      if (pr.mergeable_state === 'clean' && checksPassed(checks, statuses)) {
        // GitHub still enforces branch protections; sha rejects a concurrently changed PR.
        const result = await github.rest.pulls.merge({owner, repo, pull_number,
          sha: pr.head.sha, merge_method: 'merge'});
        if (!result.data.merged) throw new Error(result.data.message);
        core.info(`Merged toolkit update #${pull_number} at ${result.data.sha}`);
        return;
      }
      if (attempt < 17) await new Promise(resolve => setTimeout(resolve, 10000));
    }
    core.info(`Left #${pull_number} open: another check, review, or merge requirement needs attention.`);
  }
}

module.exports = {run, eligiblePR, onlyGitlink, checksPassed, eligibleToolkitDiff};
