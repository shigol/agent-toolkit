import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('task_patch', Path(__file__).resolve().parents[1] / 'integrations/github/codex_task_patch.py')
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)


class TaskTransportTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.previous = Path.cwd()
        os.chdir(self.root)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        Path('README.md').write_text('baseline\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')

    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def patch_for(self, name, content='fixture\n', symlink=False):
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if symlink:
            path.symlink_to(content)
        else:
            path.write_text(content)
        self.git('add', '--', name)
        patch = self.root / 'candidate.patch'
        patch.write_bytes(self.git('diff', '--cached', '--binary'))
        self.git('reset', '--hard', '-q', 'HEAD')
        return patch

    def test_regular_new_document_and_deletion_roundtrip(self):
        patch = self.patch_for('docs/result.md')
        PATCH.apply(patch)
        self.assertEqual(Path('docs/result.md').read_text(), 'fixture\n')
        self.assertEqual(self.git('diff', '--cached', '--name-only').decode().strip(), 'docs/result.md')

    def test_trusted_receiver_rejects_workflow_patch(self):
        patch = self.patch_for('.github/workflows/evil.yml')
        with self.assertRaisesRegex(ValueError, 'held path'):
            PATCH.apply(patch)

    def test_trusted_receiver_rejects_symlink_patch(self):
        patch = self.patch_for('docs/link.md', '/etc/hosts', symlink=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            PATCH.apply(patch)

    def test_sender_holds_sensitive_and_hidden_paths(self):
        for name in ['.env', 'auth.json', 'tools/private.key', 'tools/__pycache__/file.pyc', '../escape.md']:
            self.assertFalse(PATCH.allowed(name), name)
        for name in ['README.md', 'docs/brief.md', 'src/index.ts']:
            self.assertTrue(PATCH.allowed(name), name)

    def test_sender_saves_new_and_tracked_changes_and_records_held(self):
        Path('README.md').write_text('changed\n')
        Path('docs').mkdir()
        Path('docs/new.md').write_text('new\n')
        Path('auth.json').write_text('not a real credential\n')
        # Store artifacts outside the checkout so they cannot be mistaken for source.
        with tempfile.TemporaryDirectory() as output:
            PATCH.save(Path(output))
            import json
            report = json.loads((Path(output) / 'patch-report.json').read_text())
            self.assertEqual(report['saved'], ['README.md', 'docs/new.md'])
            self.assertEqual(report['held'], ['auth.json'])
            self.assertNotIn(b'not a real credential', (Path(output) / 'changes.patch').read_bytes())
