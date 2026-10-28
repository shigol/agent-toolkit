import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

from test_toolkit import toolkit
from handoff import resolve


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'unrelated-project'
        self.project.mkdir()
        self.profile = {'schema': 1, 'gateway_repository': 'shigol/career',
                        'gateway_issue': 1, 'brief_directory': 'docs/agent-briefs'}
        (self.root / 'HANDOFF.json').write_text(json.dumps(self.profile))

    def test_shared_default_is_metadata_not_live_access(self):
        result = resolve(self.root, self.project)
        for key, value in self.profile.items():
            self.assertEqual(result[key], value)
        self.assertEqual(result['status'], 'profile_resolved')
        self.assertEqual(result['credentials'], 'not_checked')
        self.assertEqual(result['provider_access'], 'not_checked')

    def test_project_override_and_disable_do_not_mutate_shared_default(self):
        p = self.project / '.agent-handoff.json'
        p.write_text(json.dumps({**self.profile, 'gateway_repository': 'other/repo'}))
        self.assertEqual(resolve(self.root, self.project)['gateway_repository'], 'other/repo')
        p.write_text('{"schema":1,"disabled":true}')
        self.assertEqual(resolve(self.root, self.project)['status'], 'disabled')
        self.assertEqual(resolve(self.root)['gateway_repository'], 'shigol/career')

    def test_real_cli_uses_current_project_and_explicit_project_takes_precedence(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/toolkit.py'
        def run(*args):
            return json.loads(subprocess.check_output([sys.executable, str(script), 'handoff-config', *args],
                                                     cwd=self.project, text=True))
        override = self.project / '.agent-handoff.json'
        override.write_text('{"schema":1,"disabled":true}')
        self.assertEqual(run()['status'], 'disabled')
        override.write_text(json.dumps({**self.profile, 'gateway_repository': 'cwd/alternate'}))
        self.assertEqual(run()['gateway_repository'], 'cwd/alternate')
        other = self.root / 'explicit-project'
        other.mkdir()
        (other / '.agent-handoff.json').write_text(json.dumps({**self.profile, 'gateway_repository': 'explicit/target'}))
        override.write_text('{"schema":1,"disabled":true}')
        result = run('--project', str(other))
        self.assertEqual(result['gateway_repository'], 'explicit/target')
        self.assertEqual(result['credentials'], 'not_checked')

    def test_missing_profile_does_not_claim_configuration(self):
        (self.root / 'HANDOFF.json').unlink()
        self.assertEqual(resolve(self.root)['status'], 'not_configured')

    def test_unsafe_or_credential_fields_and_symlinks_fail_closed(self):
        for delta in ({'token': 'fictional'}, {'gateway_repository': '../repo'}, {'gateway_issue': True},
                      {'gateway_issue': 0}, {'brief_directory': 'docs/../private'}, {'disabled': 'yes'}):
            (self.root / 'HANDOFF.json').write_text(json.dumps({**self.profile, **delta}))
            with self.assertRaises(ValueError):
                resolve(self.root)
        (self.root / 'HANDOFF.json').write_text(json.dumps(self.profile))
        (self.project / '.agent-handoff.json').symlink_to(self.root / 'HANDOFF.json')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            resolve(self.root, self.project)
