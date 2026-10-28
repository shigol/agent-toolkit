// Validate observable Actions state before reading an existing worker artifact.
// Alternate contracts are fixed constants supplied by trusted workflow adapters, never dispatch inputs.
async function validate({github, context, sourceRun,
  expectedWorkerPath = '.github/workflows/codex-task.yml',
  executeStepName = 'Execute one committed brief'}) {
  if (!/^[1-9][0-9]{0,19}$/.test(String(sourceRun)) || !Number.isSafeInteger(Number(sourceRun))) throw Error('Invalid source run');
  const repo = context.repo;
  const permission = (await github.rest.repos.getCollaboratorPermissionLevel({...repo, username: context.actor})).data.permission;
  if (!['admin', 'maintain', 'write'].includes(permission)) throw Error('Recovery requires repository writer permission');
  const run = (await github.rest.actions.getWorkflowRun({...repo, run_id: Number(sourceRun)})).data;
  if (run.id !== Number(sourceRun) || run.status !== 'completed' || run.event !== 'workflow_dispatch'
      || run.path !== expectedWorkerPath
      || run.head_branch !== context.payload.repository.default_branch
      || run.head_repository?.full_name !== `${repo.owner}/${repo.repo}`
      || !/^[a-f0-9]{40}$/.test(run.head_sha || '')) throw Error('Source must be a completed same-repository default-branch worker');
  const jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, {...repo, run_id: run.id, filter: 'all', per_page: 100});
  if (!jobs.some(job => job.name === 'run'
      && job.steps?.some(step => step.name === executeStepName && step.conclusion === 'success')
      && job.steps?.some(step => step.name === 'Run actions/upload-artifact@v4' && step.conclusion === 'success')))
    throw Error('The exact execution and artifact-upload steps must have succeeded; later job failures do not invalidate retained evidence');
  const artifacts = await github.paginate(github.rest.actions.listWorkflowRunArtifacts, {...repo, run_id: run.id, per_page: 100});
  const matching = artifacts.filter(item => item.name === `codex-task-${run.id}`);
  if (matching.length !== 1 || matching[0].expired || !Number.isSafeInteger(matching[0].size_in_bytes)
      || matching[0].size_in_bytes <= 0 || matching[0].size_in_bytes > 25_000_000)
    throw Error('Expected one retained worker artifact under 25 MB');
  return {sha: run.head_sha, run_id: run.id};
}
module.exports = {validate};
