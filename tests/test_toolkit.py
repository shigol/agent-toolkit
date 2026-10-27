import importlib.util
from pathlib import Path
import tempfile
import unittest

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
        self.assertEqual(len(toolkit.verify_sources()['skills']), 17)


if __name__ == '__main__':
    unittest.main()
