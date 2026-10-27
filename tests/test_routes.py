"""Generated routing must follow selections, source restrictions and checked pin updates."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_toolkit import toolkit

import routes

ROOT = Path(__file__).resolve().parents[1]


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / 'project'
        self.project.mkdir()

    def select(self, groups, **extra):
        (self.project / '.agent-toolkit.json').write_text(json.dumps(
            {'schema': 1, 'groups': groups, **extra}))

    def test_same_block_both_agents_filtered_and_idempotent(self):
        self.select(['writing', 'development'])
        local_rules = '# Project rules\nKeep the factual template.\n'
        for name in ('CLAUDE.md', 'AGENTS.md'):
            (self.project / name).write_text(local_rules)
        toolkit.install(self.project, ['codex', 'claude'])
        toolkit.emit_routes(self.project, ['codex', 'claude'])
        actual = (self.project / 'AGENTS.md').read_text()
        self.assertEqual(actual, (self.project / 'CLAUDE.md').read_text())
        self.assertTrue(actual.startswith(routes.START))
        self.assertTrue(actual.endswith(local_rules))
        for name in ('humanizer', 'systematic-debugging', 'verification-before-completion'):
            self.assertIn(': ' + name + '\n', actual)
        self.assertNotIn(': impeccable\n', actual)
        toolkit.emit_routes(self.project, ['codex', 'claude'], check=True)
        toolkit.install(self.project, ['codex', 'claude'])
        self.assertEqual(actual, (self.project / 'AGENTS.md').read_text())

    def test_exclusion_and_native_budget_do_not_leak_into_routes(self):
        self.select(['design'], native_limit=2, include=['humanizer'], exclude=['impeccable'])
        toolkit.install(self.project, ['codex', 'claude'])
        toolkit.emit_routes(self.project, ['codex', 'claude'])
        text = (self.project / 'AGENTS.md').read_text()
        self.assertIn(': humanizer\n', text)
        names = [s['name'] for s in toolkit.selection(self.project, toolkit.lock())]
        self.assertEqual(len(names), 2)
        emitted = [line.split(': ')[-1] for line in text.splitlines() if line.startswith('- ')]
        self.assertCountEqual(emitted, names)

    def test_manual_and_direction_workflows_remain_restricted(self):
        self.select(['design'])
        toolkit.install(self.project, ['codex'])
        toolkit.emit_routes(self.project, ['codex'])
        lines = (self.project / 'AGENTS.md').read_text().splitlines()
        for name in ('prototype', 'pick-ui-library', 'review-animations'):
            line = next(line for line in lines if line.endswith(': ' + name))
            self.assertTrue(line.startswith('- Only when the skill is named explicitly,'))
        self.assertIn('Explicit alternative design direction only', '\n'.join(lines))

    def test_check_detects_stale_missing_and_unresolvable_without_writing(self):
        self.select(['writing'])
        toolkit.install(self.project, ['codex'])
        with self.assertRaisesRegex(RuntimeError, 'Missing or stale'):
            toolkit.emit_routes(self.project, ['codex'], check=True)
        self.assertFalse((self.project / 'AGENTS.md').exists())
        toolkit.emit_routes(self.project, ['codex'])
        header = self.project / 'AGENTS.md'
        stale = header.read_text().replace(': humanizer', ': obsolete-fixture')
        header.write_text(stale)
        with self.assertRaisesRegex(RuntimeError, 'Stale route'):
            toolkit.verify(self.project, ['codex'])
        self.assertEqual(header.read_text(), stale)
        toolkit.install(self.project, ['codex'])
        toolkit.emit_routes(self.project, ['codex'], check=True)
        link = self.project / '.agents/skills/humanizer'
        link.unlink()
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            toolkit.emit_routes(self.project, ['codex'], check=True)

    def test_markers_preflight_both_headers_before_install_mutates(self):
        (self.project / 'AGENTS.md').write_text(routes.START + '\nOld\n' + routes.END)
        malformed = routes.START + '\nMissing closing marker'
        (self.project / 'CLAUDE.md').write_text(malformed)
        before = (self.project / 'AGENTS.md').read_text()
        with self.assertRaisesRegex(ValueError, 'markers'):
            toolkit.install(self.project, ['codex', 'claude'])
        self.assertFalse((self.project / '.agents').exists())
        self.assertEqual((self.project / 'AGENTS.md').read_text(), before)

    def test_symlink_header_and_wrong_source_are_rejected(self):
        self.select(['writing'])
        target = self.project / 'keep.md'
        target.write_text('Never replace this file')
        (self.project / 'CLAUDE.md').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'regular file'):
            toolkit.install(self.project, ['codex', 'claude'])
        self.assertFalse((self.project / '.agents').exists())
        self.assertEqual(target.read_text(), 'Never replace this file')
        (self.project / 'CLAUDE.md').unlink()
        toolkit.install(self.project, ['codex', 'claude'])
        link = self.project / '.agents/skills/humanizer'
        link.unlink()
        link.symlink_to(ROOT / 'vendor/verification-before-completion/skills')
        with self.assertRaisesRegex(RuntimeError, 'another version'):
            toolkit.emit_routes(self.project, ['codex', 'claude'])
        self.assertFalse((self.project / 'AGENTS.md').exists())

    def test_updated_guide_and_selection_regenerate_on_setup(self):
        root = Path(self.tmp.name) / 'toolkit'
        shutil.copytree(ROOT / 'catalog', root / 'catalog')
        shutil.copy(ROOT / 'toolkit.lock.json', root)
        for relative in toolkit.lock()['files']:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, target)
        self.select(['writing'])
        with patch.object(toolkit, 'ROOT', root):
            toolkit.install(self.project, ['codex', 'claude'])
            toolkit.emit_routes(self.project, ['codex', 'claude'])
            guide = root / 'catalog/humanizer.md'
            guide.write_text(guide.read_text().replace('Write or edit text for a person', 'Prepare reader-facing prose'))
            with self.assertRaisesRegex(RuntimeError, 'Stale route'):
                toolkit.verify(self.project, ['codex', 'claude'])
            toolkit.install(self.project, ['codex', 'claude'])
            self.assertIn('Prepare reader-facing prose: humanizer', (self.project / 'CLAUDE.md').read_text())
            self.select(['development'])
            toolkit.install(self.project, ['codex', 'claude'])
            self.assertNotIn(': humanizer\n', (self.project / 'CLAUDE.md').read_text())

    def test_replace_preserves_every_unowned_byte_and_rejects_bad_markers(self):
        generated = 'new\n'
        old = '# Project\n' + routes.START + '\nold\n' + routes.END + '\nLocal rules\n'
        self.assertEqual(routes.replace_block(old, generated), generated + '# Project\nLocal rules\n')
        for text in (routes.START, routes.END, routes.END + routes.START,
                     routes.START + routes.END + routes.START + routes.END):
            with self.assertRaisesRegex(ValueError, 'markers'):
                routes.replace_block(text, generated)

    def test_cli_drift_check(self):
        self.select(['writing'])
        toolkit.install(self.project, ['codex', 'claude'])
        cmd = [sys.executable, str(ROOT / 'scripts/toolkit.py'), 'emit-routes', '--project', str(self.project)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(cmd + ['--check'], check=True, stdout=subprocess.DEVNULL)
        (self.project / 'CLAUDE.md').write_text('Missing generated block')
        result = subprocess.run(cmd + ['--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Missing or stale', result.stderr)


if __name__ == '__main__':
    unittest.main()
