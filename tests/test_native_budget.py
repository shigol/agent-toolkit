import copy
import json
from pathlib import Path
import tempfile
import unittest
from test_toolkit import toolkit


class NativeBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)

    def config(self, **extra):
        (self.project / '.agent-toolkit.json').write_text(json.dumps({'schema': 1, 'groups': ['design'], **extra}))

    def test_new_registered_entries_do_not_expand_capped_native_catalogue(self):
        data = copy.deepcopy(toolkit.lock())
        self.config(native_limit=17)
        before = toolkit.selection(self.project, data)
        data['skills'].append({'name': 'new-design-fixture', 'path': 'vendor/fixture', 'package': 'emil'})
        after = toolkit.selection(self.project, data)
        self.assertEqual(before, after)
        self.assertEqual(len(after), 17)
        self.config()
        self.assertEqual(len(toolkit.selection(self.project, data)), 18)

    def test_explicit_include_has_priority_inside_limit(self):
        self.config(native_limit=2, include=['market-sizing'])
        names = [s['name'] for s in toolkit.selection(self.project, toolkit.lock())]
        self.assertEqual(len(names), 2)
        self.assertIn('market-sizing', names)
        self.config(native_limit=1, include=['market-sizing', 'humanizer'])
        with self.assertRaisesRegex(RuntimeError, 'Explicit includes'):
            toolkit.selection(self.project, toolkit.lock())

    def test_invalid_limit_fails_before_install_mutates_files(self):
        for value in (None, 0, -1, True, '3', 2.5):
            with self.subTest(value=value):
                self.config(native_limit=value)
                with self.assertRaisesRegex(RuntimeError, 'native_limit'):
                    toolkit.install(self.project, ['codex', 'claude'])
                self.assertFalse((self.project / '.agents').exists())

    def test_budgeted_install_preserves_local_skill(self):
        local = self.project / '.claude/skills/local-procedure'
        local.mkdir(parents=True)
        (local / 'SKILL.md').write_text('Local task procedure')
        self.config(native_limit=2)
        toolkit.install(self.project, ['codex', 'claude'])
        toolkit.install(self.project, ['codex', 'claude'])
        self.assertEqual(len(list((self.project / '.agents/skills').iterdir())), 2)
        self.assertEqual((local / 'SKILL.md').read_text(), 'Local task procedure')


if __name__ == '__main__':
    unittest.main()
