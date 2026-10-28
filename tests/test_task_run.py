import importlib.util
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / 'integrations/github'
sys.path.insert(0, str(INTEGRATION))
import codex_task_run as runner
import codex_task_patch as transport


class BoundedRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'project'
        self.output = Path(self.tmp.name) / 'artifacts'
        self.root.mkdir()
        self.previous = Path.cwd()
        os.chdir(self.root)
        for args in [('init', '-q'), ('config', 'user.name', 'Fixture'), ('config', 'user.email', 'fixture@example.invalid')]:
            self.git(*args)
        Path('README.md').write_text('baseline\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture baseline')

    def tearDown(self):
        os.chdir(self.previous)
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL)

    def command(self, source):
        return [sys.executable, '-u', '-c', source]

    def checkpoint(self):
        return json.loads((self.output / 'checkpoint.json').read_text())

    def test_success_saves_real_usage_without_claiming_project_completion(self):
        command = self.command("import json;print(json.dumps({'type':'turn.completed','usage':{'input_tokens':175}}))")
        self.assertEqual(runner.run(command, self.output, seconds=3, stale_seconds=2, interval=.1), 0)
        data = self.checkpoint()
        self.assertEqual(data['status'], 'execution_complete')
        self.assertEqual(data['input_tokens'], 175)
        self.assertTrue(data['usage_known'])

    def test_timeout_keeps_partial_work_and_does_not_stage_the_project(self):
        command = self.command("from pathlib import Path;import time;Path('docs').mkdir();Path('docs/partial.md').write_text('partial work\\n');print('started',flush=True);time.sleep(5)")
        self.assertEqual(runner.run(command, self.output, seconds=.4, stale_seconds=3, interval=.1), 124)
        self.assertEqual(self.checkpoint()['status'], 'timeout')
        self.assertIn(b'partial work', (self.output / 'partial.patch').read_bytes())
        self.assertEqual(self.git('diff', '--cached', '--name-only'), b'')
        self.assertEqual(Path('docs/partial.md').read_text(), 'partial work\n')

    def test_silent_worker_is_stopped_and_unknown_usage_is_explicit(self):
        command = self.command('import time;time.sleep(5)')
        self.assertEqual(runner.run(command, self.output, seconds=3, stale_seconds=.3, interval=.1), 124)
        data = self.checkpoint()
        self.assertEqual(data['status'], 'stalled')
        self.assertFalse(data['usage_known'])

    def test_failure_keeps_its_exit_code_and_checkpoint(self):
        command = self.command('raise SystemExit(7)')
        self.assertEqual(runner.run(command, self.output, seconds=3, stale_seconds=2, interval=.1), 7)
        self.assertEqual(self.checkpoint()['status'], 'failed')
        self.assertEqual(self.checkpoint()['exit_code'], 7)

    def test_partial_snapshot_preserves_staged_work_and_holds_sensitive_paths(self):
        Path('README.md').write_text('unrelated staged work\n')
        self.git('add', 'README.md')
        before = self.git('diff', '--cached', '--binary')
        Path('auth.json').write_text('not a credential, test fixture only')
        Path('docs').mkdir()
        Path('docs/new.md').write_text('checkpoint\n')
        transport.snapshot(self.output)
        self.assertEqual(before, self.git('diff', '--cached', '--binary'))
        report = json.loads((self.output / 'partial-report.json').read_text())
        self.assertEqual(report['held'], ['auth.json'])
        patch = (self.output / 'partial.patch').read_bytes()
        self.assertIn(b'checkpoint', patch)
        self.assertNotIn(b'not a credential', patch)


if __name__ == '__main__':
    unittest.main()
