"""Recovery validates real Actions state and only transports an existing artifact."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ResultRecoveryTests(unittest.TestCase):
    def test_actual_run_and_artifact_validation_rejects_untrusted_or_unfinished_sources(self):
        source = ROOT / 'integrations/github/codex_recover.cjs'
        javascript = r'''
const assert = require('node:assert/strict');
const {validate} = require(process.argv[1]);
const context = {repo:{owner:'owner',repo:'project'},actor:'writer',payload:{repository:{default_branch:'main'}}};
const baseline = {id:123,status:'completed',event:'workflow_dispatch',path:'.github/workflows/codex-task.yml',head_branch:'main',head_repository:{full_name:'owner/project'},head_sha:'a'.repeat(40)};
const artifact = {name:'codex-task-123',expired:false,size_in_bytes:1234};
const worker = {name:'run',conclusion:'success',steps:[{name:'Execute one committed brief',conclusion:'success'},{name:'Run actions/upload-artifact@v4',conclusion:'success'}]};
async function attempt({run=baseline,artifacts=[artifact],jobs=[worker],permission='write',contract={}}={}) {
 const github={rest:{repos:{getCollaboratorPermissionLevel:async()=>({data:{permission}})},actions:{getWorkflowRun:async()=>({data:run}),listJobsForWorkflowRun:()=>{},listWorkflowRunArtifacts:()=>{}}}};
 github.paginate=async (fn,args)=>{if(fn===github.rest.actions.listJobsForWorkflowRun){assert.equal(args.filter,'all');return jobs;}return artifacts;};
 return validate({github,context,sourceRun:'123',...contract});
}
(async()=>{
 assert.deepEqual(await attempt(),{sha:'a'.repeat(40),run_id:123});
 const contract={expectedWorkerPath:'.github/workflows/continuity-fixture.yml',executeStepName:'Execute fixed harmless probe'};
 const fixed={run:{...baseline,path:contract.expectedWorkerPath},jobs:[{...worker,steps:[{name:contract.executeStepName,conclusion:'success'},worker.steps[1]]}]};
 await assert.rejects(attempt(fixed));
 assert.deepEqual(await attempt({...fixed,contract}),{sha:'a'.repeat(40),run_id:123});
 for(const delta of [{status:'in_progress'},{event:'pull_request'},{head_branch:'feature'},{head_repository:{full_name:'fork/project'}},{path:'.github/workflows/other.yml'},{head_sha:'bad'}])
  await assert.rejects(attempt({run:{...baseline,...delta}}));
 for(const overrides of [{permission:'read'},{jobs:[]},{jobs:[{...worker,conclusion:'cancelled'}]},{jobs:[{...worker,steps:[]}]},{artifacts:[]},{artifacts:[artifact,artifact]},{artifacts:[{...artifact,expired:true}]},{artifacts:[{...artifact,size_in_bytes:25000001}]}])
  await assert.rejects(attempt(overrides));
})().catch(error=>{console.error(error);process.exitCode=1});
'''
        subprocess.run(['node', '-e', javascript, str(source)], check=True, capture_output=True)

    def test_result_and_recovery_templates_use_bounded_trusted_transport_without_inference(self):
        ordinary = (ROOT / 'integrations/github/codex-task.yml').read_text().split('  result:', 1)[1]
        recovery = (ROOT / 'integrations/github/codex-recover.yml').read_text()
        for text in (ordinary, recovery):
            self.assertIn('timeout-minutes: 15', text)
            self.assertIn('sparse-checkout:', text)
            for directory in ('src', 'public', 'scripts', 'tools', 'tests', 'docs', 'codex', 'catalogue'):
                self.assertRegex(text, r'(?m)^            ' + directory + r'$')
            self.assertNotIn('git push', text)  # The hook-disabled, bounded helper owns transport.
            self.assertIn('codex_task_patch.py', text)
        self.assertIn('ref: ${{ github.event.repository.default_branch }}', recovery)
        self.assertIn('persist-credentials: false', recovery)
        self.assertIn('ref: ${{ steps.source.outputs.sha }}', recovery)
        self.assertIn('run-id: ${{ inputs.source_run }}', recovery)
        self.assertIn('trusted/.github/scripts/codex_task_patch.py', recovery)
        for forbidden in ('codex exec', 'codex_task_run.py', 'createWorkflowDispatch', 'rerunWorkflow'):
            self.assertNotIn(forbidden, recovery)
        self.assertIn('no model inference was run', recovery)
        self.assertIn('review pending', ordinary)
        check = (ROOT / 'integrations/github/agent-toolkit-check.yml').read_text()
        for path in ('.github/workflows/codex-task.yml', '.github/workflows/codex-recover.yml',
                     '.github/scripts/codex_recover.cjs', '.github/scripts/codex_task_patch.py'):
            self.assertEqual(check.count('- ' + path), 2)
