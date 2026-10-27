import importlib.util
import json
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('toolkit', Path(__file__).parents[1] / 'scripts/toolkit.py')
toolkit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toolkit)


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='toolkit project ')
        self.project = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_install_idempotent_both_agents(self):
        toolkit.install(self.project, ['codex', 'claude'])
        toolkit.install(self.project, ['codex', 'claude'])
        for skill in toolkit.lock()['skills']:
            a = self.project / '.agents/skills' / skill['name']
            b = self.project / '.claude/skills' / skill['name']
            self.assertEqual(a.resolve(), b.resolve())
            self.assertFalse(Path(a.readlink()).is_absolute())

    def test_conflict_causes_no_partial_install(self):
        conflict = self.project / '.claude/skills' / toolkit.lock()['skills'][-1]['name']
        conflict.mkdir(parents=True)
        (conflict / 'keep.txt').write_text('user-owned')
        with self.assertRaisesRegex(RuntimeError, 'conflict'):
            toolkit.install(self.project, ['codex', 'claude'])
        self.assertFalse((self.project / '.agents').exists())
        self.assertEqual((conflict / 'keep.txt').read_text(), 'user-owned')

    def test_broken_existing_symlink_is_preserved(self):
        folder = self.project / '.agents/skills'
        folder.mkdir(parents=True)
        target = folder / toolkit.lock()['skills'][0]['name']
        target.symlink_to('missing')
        with self.assertRaisesRegex(RuntimeError, 'conflict'):
            toolkit.install(self.project, ['codex'])
        self.assertEqual(str(target.readlink()), 'missing')

    def test_missing_link_detected(self):
        toolkit.install(self.project, ['codex'])
        (self.project / '.agents/skills' / toolkit.lock()['skills'][0]['name']).unlink()
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            toolkit.verify(self.project, ['codex'])

    def test_redirected_parent_is_rejected(self):
        (self.project / 'elsewhere').mkdir()
        (self.project / '.agents').symlink_to('elsewhere')
        with self.assertRaisesRegex(RuntimeError, 'redirected'):
            toolkit.install(self.project, ['codex'])

    def test_source_tampering_detected(self):
        original = toolkit.ROOT
        try:
            toolkit.ROOT = self.project
            (self.project / 'toolkit.lock.json').write_text('{"files":{"file":"wrong"},"skills":[]}')
            (self.project / 'file').write_text('tampered')
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                toolkit.verify_sources()
        finally:
            toolkit.ROOT = original

    def test_vendored_integrity(self):
        names = {s['name'] for s in toolkit.verify_sources()['skills']}
        self.assertTrue({'impeccable', 'humanizer', 'motion-graphics', 'product-strategy'} <= names)

    def select(self, groups, **extra):
        (self.project / '.agent-toolkit.json').write_text(json.dumps({'schema': 1, 'groups': groups, **extra}))

    def test_app_selection_excludes_writing_and_product(self):
        self.select(['design', 'video'])
        toolkit.install(self.project, ['codex', 'claude'])
        for folder in ['.agents', '.claude']:
            skills = self.project / folder / 'skills'
            self.assertTrue((skills / 'impeccable/SKILL.md').is_file())
            self.assertTrue((skills / 'motion-graphics/SKILL.md').is_file())
            self.assertFalse((skills / 'humanizer').exists())
            self.assertFalse((skills / 'product-strategy').exists())

    def test_narrowing_removes_only_exact_managed_links(self):
        toolkit.install(self.project, ['codex', 'claude'])
        own = self.project / '.claude/skills/app-sync'
        own.mkdir(); (own / 'SKILL.md').write_text('local procedure')
        foreign = self.project / '.agents/skills/local-link'
        foreign.symlink_to(own)
        self.select(['writing'])
        toolkit.install(self.project, ['codex', 'claude'])
        for folder in ['.agents', '.claude']:
            self.assertFalse((self.project / folder / 'skills/impeccable').exists())
            self.assertTrue((self.project / folder / 'skills/humanizer/SKILL.md').is_file())
        self.assertEqual((own / 'SKILL.md').read_text(), 'local procedure')
        self.assertTrue(foreign.is_symlink())

    def test_conflict_does_not_remove_deselected_links(self):
        self.select(['design'])
        toolkit.install(self.project, ['codex', 'claude'])
        conflict = self.project / '.claude/skills/humanizer'
        conflict.mkdir()
        self.select(['writing'])
        with self.assertRaisesRegex(RuntimeError, 'conflict'):
            toolkit.install(self.project, ['codex', 'claude'])
        self.assertTrue((self.project / '.agents/skills/impeccable/SKILL.md').is_file())
        self.assertFalse((self.project / '.agents/skills/humanizer').exists())

    def test_invalid_selection_makes_no_changes(self):
        for config in [dict(schema=1, groups=['typo']), dict(schema=2, groups=[]),
                       dict(schema=1, groups='design'), dict(schema=1, groups=[], include=['../outside'])]:
            (self.project / '.agent-toolkit.json').write_text(json.dumps(config))
            with self.assertRaises(RuntimeError):
                toolkit.install(self.project, ['codex', 'claude'])
            self.assertFalse((self.project / '.agents').exists())

    def test_explicit_include_and_exclude(self):
        self.select(['design'], include=['humanizer'], exclude=['write-swift'])
        toolkit.install(self.project, ['codex'])
        skills = self.project / '.agents/skills'
        self.assertTrue((skills / 'humanizer/SKILL.md').is_file())
        self.assertFalse((skills / 'write-swift').exists())

    def test_status_distinguishes_installed_files_from_session_discovery(self):
        self.select(['writing'])
        toolkit.install(self.project, ['codex'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            toolkit.status(self.project, ['codex'])
        result = json.loads(output.getvalue())
        self.assertEqual(result['agents']['codex']['installed'], 1)
        self.assertEqual(result['agents']['codex']['missing'], [])
        self.assertIn('Not verified', result['session_discovery'])

    def test_status_fails_for_missing_selected_files(self):
        self.select(['writing'])
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'missing'):
            toolkit.status(self.project, ['claude'])

    def test_new_skills_follow_selected_package_groups(self):
        data = toolkit.lock()
        data['skills'] += [dict(name='future-design', package='emil', path='vendor/emil/future'),
                           dict(name='future-writing', package='humanizer', path='vendor/humanizer/future')]
        self.select(['design'])
        names = {s['name'] for s in toolkit.selection(self.project, data)}
        self.assertIn('future-design', names)
        self.assertNotIn('future-writing', names)

    def test_text_only_selection_does_not_require_design_runtime(self):
        self.select(['writing', 'product'])
        with patch.object(toolkit, 'verify_engine') as engine, patch.object(toolkit, 'verify_taste') as taste:
            toolkit.verify_runtime(self.project)
        engine.assert_not_called()
        taste.assert_not_called()

    def test_broken_selection_link_is_not_treated_as_all_skills(self):
        (self.project / '.agent-toolkit.json').symlink_to('missing-config')
        with self.assertRaisesRegex(RuntimeError, 'regular file'):
            toolkit.install(self.project, ['codex'])
        self.assertFalse((self.project / '.agents').exists())


if __name__ == '__main__':
    unittest.main()
