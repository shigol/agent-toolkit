import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import commit_hooks
import skills_audit


class CommitHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='skills hook ')
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / 'consumer'
        self.project.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        # A committed project-local skill exercises canonical Git source reads.
        self.body = '---\nname: fixture\n---\nRead the complete source.\nSecond requirement.\n'
        source = self.project / '.claude/skills/fixture/SKILL.md'
        source.parent.mkdir(parents=True)
        source.write_text(self.body)
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture source')
        toolkit = self.project / '.agent-toolkit/scripts'
        toolkit.mkdir(parents=True)
        (toolkit / 'skills_audit.py').symlink_to(Path(skills_audit.__file__))
        commit_hooks.install(self.project, commit_hooks.plan(self.project))
        self.home = Path(self.tmp.name) / 'home'
        self.home.mkdir()
        self.sid = 'fixture-session'
        self.now = skills_audit.dt.datetime.now(skills_audit.dt.timezone.utc).isoformat()
        self.env = {**os.environ, 'HOME': str(self.home), 'CLAUDE_CODE_SESSION_ID': self.sid}
        self.env.pop('CODEX_THREAD_ID', None)
        self.env.pop('CODEX_HOME', None)

    def git(self, *args, **kw):
        return subprocess.run(['git', '-C', str(self.project), *args], check=True,
                              capture_output=True, text=True, **kw).stdout.strip()

    def claude(self, output):
        path = self.home / '.claude/projects/-consumer' / (self.sid + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        events = [{'type': 'tool_use', 'id': 'read', 'name': 'Read',
                   'input': {'file_path': '.claude/skills/fixture/SKILL.md'}},
                  {'type': 'tool_result', 'tool_use_id': 'read', 'content': output}]
        path.write_text(''.join(json.dumps({'timestamp': self.now, 'message': {'content': [e]}}) + '\n' for e in events))

    def commit(self):
        return subprocess.run(['git', '-C', str(self.project), 'commit', '--allow-empty', '-m',
                               'Fixture change\n\nSkills: fixture'], env=self.env, capture_output=True, text=True)

    def test_real_git_claude_refuses_unread_then_stamps_read(self):
        self.claude('Only a partial read')
        transcript = self.home / '.claude/projects/-consumer' / (self.sid + '.jsonl')
        transcript.write_text('')
        unread = self.commit()
        self.assertNotEqual(unread.returncode, 0)
        self.assertIn('UNREAD', unread.stderr)
        self.claude('Only a partial read')
        failed = self.commit()
        self.assertNotEqual(failed.returncode, 0, failed.stdout)
        self.assertIn('PARTIAL', failed.stderr)
        self.claude(self.body)
        accepted = self.commit()
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        message = self.git('log', '-1', '--format=%B')
        self.assertIn('Skills-Read: fixture ok', message)
        self.assertIn('Skills-Window:', message)
        self.assertIn('Hooks: on', message)

    def codex(self, output, custom=False, result=True, timestamp=None):
        self.env.pop('CLAUDE_CODE_SESSION_ID', None)
        self.env['CODEX_THREAD_ID'] = self.sid
        path = self.home / '.codex/sessions/2026/10/31' / ('rollout-date-' + self.sid + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        call = {'type': 'custom_tool_call' if custom else 'function_call', 'call_id': 'read', 'name': 'exec'}
        if custom: call['input'] = 'text(await tools.exec_command({cmd:"cat .claude/skills/fixture/SKILL.md"}));'
        else: call['arguments'] = json.dumps({'cmd': 'cat .claude/skills/fixture/SKILL.md'})
        res = {'type': 'custom_tool_call_output' if custom else 'function_call_output', 'call_id': 'read',
               'output': [{'type': 'input_text', 'text': json.dumps(output)}] if custom else json.dumps(output)}
        rows = [call, res] if result else [call]
        path.write_text(''.join(json.dumps({'type': 'response_item', 'timestamp': timestamp or self.now, 'payload': row}) + '\n' for row in rows))

    def test_codex_direct_and_code_mode_read(self):
        for custom in (False, True):
            with self.subTest(custom=custom):
                self.codex({'output': self.body, 'exit_code': 0}, custom=custom)
                proc = self.commit()
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn('Skills-Read: fixture ok', self.git('log', '-1', '--format=%B'))

    def test_codex_failed_truncated_input_only_and_old_refused(self):
        for output, kw in [({'output': self.body, 'exit_code': 1}, {}),
                           ({'output': self.body, 'truncated': True}, {'custom': True}),
                           ({'output': self.body}, {'result': False}),
                           ({'output': self.body}, {'timestamp': '2000-01-01T00:00:00Z'}),
                           ({'output': 'partial'}, {})]:
            with self.subTest(output=output, kw=kw):
                self.codex(output, **kw)
                proc = self.commit()
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('commit refused', proc.stderr)

    def test_installer_repeat_preserves_other_hooks(self):
        other = self.project / '.githooks/pre-push'
        other.write_text('project-owned')
        commit_hooks.install(self.project, commit_hooks.plan(self.project))
        self.assertEqual(other.read_text(), 'project-owned')
        self.assertEqual(self.git('config', '--get', 'core.hooksPath'), '.githooks')

    def test_installer_refuses_foreign_hook_and_path(self):
        hook = self.project / '.githooks/commit-msg'
        hook.write_text('foreign hook')
        with self.assertRaisesRegex(RuntimeError, 'differs'): commit_hooks.plan(self.project)
        self.assertEqual(hook.read_text(), 'foreign hook')
        self.git('config', 'core.hooksPath', 'custom-hooks')
        with self.assertRaisesRegex(RuntimeError, 'core.hooksPath'): commit_hooks.plan(self.project)

    def test_installer_refuses_redirect(self):
        hook = self.project / '.githooks/commit-msg'
        hook.unlink()
        hook.symlink_to(self.project / 'elsewhere')
        with self.assertRaisesRegex(RuntimeError, 'redirected'): commit_hooks.plan(self.project)

    def test_no_transcript_reports_skip_without_claiming_read(self):
        proc = self.commit()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('no local transcript', proc.stderr)
        self.assertNotIn('Skills-Read:', self.git('log', '-1', '--format=%B'))
