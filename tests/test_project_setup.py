"""Real Git setup, rollback and global fallback instruction checks."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import re
import textwrap
from unittest.mock import patch

from test_toolkit import toolkit
import project_setup
from handoff import resolve as resolve_handoff

ROOT = Path(__file__).resolve().parents[1]


class ProjectSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        cls.source = Path(cls.base.name) / 'committed-library'
        def ignore(directory, names):
            return [name for name in names if name in ('.git', '__pycache__')
                    or (Path(directory) == ROOT / 'vendor/impeccable/skills/scripts' and name == 'bin')]
        shutil.copytree(ROOT, cls.source, ignore=ignore)
        cls.git(cls.source, 'init', '--quiet')
        cls.git(cls.source, 'add', '.')
        # Upstream ignore rules also match some deliberately vendored fixtures.
        manifest = json.loads((cls.source / 'toolkit.lock.json').read_text())
        cls.git(cls.source, 'add', '--force', '--', *manifest['files'])
        cls.git(cls.source, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '--quiet', '-m', 'Self-mirror setup fixture')
        cls.revision = cls.git(cls.source, 'rev-parse', 'HEAD')

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    @staticmethod
    def git(path, *args):
        return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / 'scratch repository'
        self.project.mkdir()
        self.git(self.project, 'init', '--quiet')

    def initialize(self):
        return project_setup.init_project(self.project, self.source, source=str(self.source))

    @staticmethod
    def bridge_guard():
        text = (ROOT / 'integrations/github/agent-toolkit-check.yml').read_text()
        match = re.search(r'      - name: Verify installed Claude wake bridge\n        run: \|\n((?:          [^\n]*\n)+)', text)
        if not match:
            raise AssertionError('Missing installed bridge CI guard')
        return textwrap.dedent(match[1])

    def test_fresh_repository_both_agents_exact_pin_and_repeat_setup(self):
        (self.project / 'AGENTS.md').write_text('Keep my project instructions.\n')
        result = self.initialize()
        self.assertEqual(result['toolkit_commit'], self.revision)
        self.assertEqual(self.git(self.project / '.agent-toolkit', 'rev-parse', 'HEAD'), self.revision)
        for agent in ('.agents', '.claude'):
            source = self.project / agent / 'skills/humanizer/SKILL.md'
            self.assertTrue(source.is_file())
        self.assertIn('Keep my project instructions.', (self.project / 'AGENTS.md').read_text())
        self.assertNotIn('skill-routes:start', (self.project / 'AGENTS.md').read_text())
        self.assertIn('skill-routes:start', (self.project / 'CLAUDE.md').read_text())
        self.assertTrue((self.project / '.github/workflows/agent-toolkit-merge.yml').is_file())
        self.assertTrue((self.project / '.github/workflows/codex-continuity.yml').is_file())
        self.assertTrue((self.project / '.github/scripts/codex_task_run.py').is_file())
        subprocess.run(['node', str(self.project / '.github/scripts/codex_continuity.test.cjs')],
                       cwd=self.project, check=True, stdout=subprocess.DEVNULL)
        self.assertTrue((self.project / '.github/workflows/claude-wake.yml').is_file())
        subprocess.run(['bash', '-c', self.bridge_guard()],
                       cwd=self.project, check=True, stdout=subprocess.DEVNULL)
        before = (self.project / 'CLAUDE.md').read_bytes()
        self.initialize()
        self.assertEqual(before, (self.project / 'CLAUDE.md').read_bytes())

    def test_ci_bridge_guard_skips_clean_projects_but_rejects_partial_and_redirected_installs(self):
        def run():
            return subprocess.run(['bash', '-c', self.bridge_guard()], cwd=self.project,
                                  capture_output=True, text=True)
        self.assertEqual(run().returncode, 0)
        scripts = self.project / '.github/scripts'
        scripts.mkdir(parents=True)
        (scripts / 'claude_wake.cjs').write_text('// fixture helper\n')
        self.assertNotEqual(run().returncode, 0)
        workflow = self.project / '.github/workflows/claude-wake.yml'
        workflow.parent.mkdir()
        workflow.write_text('name: Fixture\n')
        (scripts / 'claude_wake.test.cjs').write_text('require("node:fs").writeFileSync("bridge-test-ran", "yes");\n')
        pinned = self.project / '.agent-toolkit/integrations/github'
        pinned.mkdir(parents=True)
        for name in ('claude_wake.cjs', 'claude_wake.test.cjs'):
            shutil.copyfile(scripts / name, pinned / name)
        shutil.copyfile(workflow, pinned / workflow.name)
        self.assertEqual(run().returncode, 0)
        self.assertTrue((self.project / 'bridge-test-ran').is_file())
        for installed in (scripts / 'claude_wake.cjs', scripts / 'claude_wake.test.cjs', workflow):
            original = installed.read_text()
            installed.write_text(original + '# changed managed fixture\n')
            self.assertNotEqual(run().returncode, 0)
            installed.write_text(original)
        (pinned / 'claude_wake.cjs').unlink()
        self.assertNotEqual(run().returncode, 0)  # An older toolkit pin has no managed bridge template.
        shutil.copyfile(scripts / 'claude_wake.cjs', pinned / 'claude_wake.cjs')
        workflow.unlink()
        workflow.symlink_to('missing.yml')
        self.assertNotEqual(run().returncode, 0)
        text = (ROOT / 'integrations/github/agent-toolkit-check.yml').read_text()
        for value in ('.agent-handoff.json', '.github/scripts/claude_*', '.github/workflows/claude-wake.yml'):
            self.assertIn('      - ' + value, text)
        self.assertIn('            .github/workflows\n', text)
        events = [re.search(r'  ' + event + r':\n    paths:\n((?:      - [^\n]+\n)+)', text).group(1)
                  for event in ('pull_request', 'push')]
        self.assertEqual(events[0], events[1])
        self.assertIn("if: github.event_name != 'push' || github.ref == format('refs/heads/{0}', github.event.repository.default_branch)", text)
        self.assertLess(text.index('Verify installed Claude wake bridge'), text.index('Verify fresh installation'))

    def test_existing_selection_is_preserved(self):
        config = {'schema': 1, 'groups': ['writing'], 'native_limit': 1}
        text = json.dumps(config)
        (self.project / '.agent-toolkit.json').write_text(text)
        result = self.initialize()
        self.assertEqual(result['skills'], 1)
        self.assertEqual((self.project / '.agent-toolkit.json').read_text(), text)
        self.assertFalse((self.project / '.agents/skills/impeccable').exists())

    def test_generated_policy_scopes_verification_to_technical_claims_not_general_prose(self):
        self.initialize()
        home = Path(self.tmp.name) / 'global profile'
        project_setup.bootstrap_global(self.source, home)
        for path in (self.project / 'AGENTS.md', self.project / 'CLAUDE.md', home / 'AGENTS.md'):
            text = path.read_text()
            self.assertIn('humanizer', text)
            self.assertIn('prose', text)
            self.assertIn('technical completion claims', text)
            self.assertNotIn('before completion claims', text)
            self.assertNotIn('for tests and completion claims', text)
        native = (self.project / 'AGENTS.md').read_text()
        self.assertIn('pattern text for short replies/PR bodies', native)
        self.assertNotIn('### patterns', native)
        guide = (self.source / 'catalog/verification-before-completion.md').read_text()
        self.assertIn('**Do not use when:** General prose editing', guide)
        self.assertIn('**Use when:** A development task', guide)

    def test_unrelated_future_projects_and_global_fallback_discover_shared_gateway(self):
        self.initialize()
        other = Path(self.tmp.name) / 'different future project'
        other.mkdir()
        self.git(other, 'init', '--quiet')
        project_setup.init_project(other, self.source, source=str(self.source))
        for project in (self.project, other):
            result = resolve_handoff(project / '.agent-toolkit', project)
            self.assertEqual(result['gateway_repository'], 'shigol/career')
            self.assertEqual(result['gateway_issue'], 1)
            self.assertEqual(result['credentials'], 'not_checked')
            self.assertFalse((project / '.agent-handoff.json').exists())
        home = Path(self.tmp.name) / 'new global-only host'
        project_setup.bootstrap_global(self.source, home)
        text = (home / 'AGENTS.md').read_text()
        self.assertIn(str(self.source) + '/CONTINUITY.md', text)
        self.assertIn('handoff-config', (self.source / 'CONTINUITY.md').read_text())
        self.assertEqual(resolve_handoff(self.source)['gateway_repository'], 'shigol/career')

    def test_conflicting_integration_is_preserved_before_clone(self):
        path = self.project / '.github/dependabot.yml'
        path.parent.mkdir()
        path.write_text('Keep my existing package update configuration.\n')
        with self.assertRaisesRegex(ValueError, 'Existing integration differs'):
            self.initialize()
        self.assertFalse((self.project / '.agent-toolkit').exists())
        self.assertFalse((self.project / '.gitmodules').exists())
        self.assertIn('Keep my existing', path.read_text())

    def test_existing_claude_wake_workflow_is_not_overwritten(self):
        path = self.project / '.github/workflows/claude-wake.yml'
        path.parent.mkdir(parents=True)
        original = 'name: Keep my existing Claude integration\n'
        path.write_text(original)
        with self.assertRaisesRegex(ValueError, 'Existing integration differs'):
            self.initialize()
        self.assertEqual(path.read_text(), original)
        self.assertFalse((self.project / '.agent-toolkit').exists())

    def test_failed_install_rolls_back_files_submodule_and_own_index_entries(self):
        readme = self.project / 'README.md'
        readme.write_text('Unrelated staged user work\n')
        self.git(self.project, 'add', 'README.md')
        before = self.git(self.project, 'ls-files', '--stage')
        original = subprocess.run
        def fail_install(command, *args, **kwargs):
            if len(command) > 2 and command[2] == 'install':
                raise RuntimeError('Injected install failure')
            return original(command, *args, **kwargs)
        with patch.object(project_setup.subprocess, 'run', side_effect=fail_install):
            with self.assertRaisesRegex(RuntimeError, 'Injected install'):
                self.initialize()
        self.assertEqual(before, self.git(self.project, 'ls-files', '--stage'))
        for name in ('.agent-toolkit', '.gitmodules', 'AGENTS.md', 'CLAUDE.md', '.agent-toolkit.json'):
            self.assertFalse((self.project / name).exists())
        self.assertEqual(readme.read_text(), 'Unrelated staged user work\n')

    def test_redirected_headers_and_skill_parents_are_rejected(self):
        outside = Path(self.tmp.name) / 'keep.md'
        outside.write_text('Private user instructions, not a template target.\n')
        header = self.project / 'AGENTS.md'
        header.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'redirected'):
            self.initialize()
        self.assertFalse((self.project / '.agent-toolkit').exists())
        self.assertEqual(outside.read_text(), 'Private user instructions, not a template target.\n')

    def test_global_setup_is_repeatable_and_leaves_other_configuration_untouched(self):
        home = Path(self.tmp.name) / 'codex home'
        home.mkdir()
        (home / 'AGENTS.md').write_text('Keep existing global rules.\n')
        settings = home / 'settings.toml'
        settings.write_text('test_only = true\n')
        first = project_setup.bootstrap_global(self.source, home)
        before = (home / 'AGENTS.md').read_bytes()
        project_setup.bootstrap_global(self.source, home)
        self.assertEqual(before, (home / 'AGENTS.md').read_bytes())
        self.assertIn('Keep existing global rules.', before.decode())
        self.assertIn(str(self.source), before.decode())
        self.assertEqual(settings.read_text(), 'test_only = true\n')
        self.assertEqual(first['credentials'], 'not read or changed')


if __name__ == '__main__':
    unittest.main()
