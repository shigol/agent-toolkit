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

    def test_rejected_helper_patch_cannot_mutate_trusted_status_code_or_index(self):
        helper = Path('.github/scripts/codex_result.cjs')
        helper.parent.mkdir(parents=True)
        helper.write_text('module.exports = {trusted: true};\n')
        self.git('add', '.'); self.git('commit', '-qm', 'Trusted receiver')
        original = helper.read_bytes()
        helper.write_text('throw Error("candidate code must never execute");\n')
        Path('docs').mkdir(); Path('docs/allowed.md').write_text('Allowed alongside held helper\n')
        self.git('add', '.')
        patch = self.root / 'candidate.patch'
        patch.write_bytes(self.git('diff', '--cached', '--binary'))
        self.git('reset', '--hard', '-q', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'held path'):
            PATCH.apply(patch)
        self.assertEqual(helper.read_bytes(), original)
        self.assertFalse(Path('docs/allowed.md').exists())
        self.assertEqual(self.git('diff', '--cached', '--binary'), b'')

    def test_transport_retries_existing_artifact_without_hooks_or_duplicate_commits(self):
        bare = self.root.parent / (self.root.name + '-remote.git')
        self.git('init', '--bare', '-q', str(bare))
        self.addCleanup(lambda: __import__('shutil').rmtree(bare, ignore_errors=True))
        self.git('remote', 'add', 'origin', str(bare))
        baseline = self.git('rev-parse', 'HEAD').strip().decode()
        hook = Path('.git/hooks/pre-push')
        hook.write_text('#!/bin/sh\ntouch HOOK-RAN\nexit 9\n'); hook.chmod(0o755)
        commit_hook = Path('.git/hooks/pre-commit')
        commit_hook.write_text('#!/bin/sh\ntouch HOOK-RAN\nexit 9\n'); commit_hook.chmod(0o755)
        patch = self.patch_for('docs/recovered.md', 'Already-completed worker output\n')
        branch = PATCH.save_branch(patch, 'codex/task-123', '123')
        first = self.git('ls-remote', 'origin', 'refs/heads/' + branch)
        self.assertFalse(Path('HOOK-RAN').exists())
        self.git('checkout', '--detach', '-q', baseline)
        self.assertEqual(PATCH.save_branch(patch, branch, '123'), branch)
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/' + branch), first)
        self.assertFalse(Path('HOOK-RAN').exists())
        # Recovery never force-replaces a separately edited review branch.
        self.git('reset', '--hard', '-q', baseline)
        other = self.patch_for('docs/different.md', 'A distinct candidate\n')
        with self.assertRaisesRegex(ValueError, 'Existing review branch differs'):
            PATCH.save_branch(other, branch, '123')
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/' + branch), first)

    def test_symlink_rejection_does_not_create_working_tree_link(self):
        patch = self.patch_for('docs/link.md', '/etc/hosts', symlink=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            PATCH.apply(patch)
        self.assertFalse(os.path.lexists('docs/link.md'))
        self.assertEqual(self.git('diff', '--cached', '--name-only'), b'')

    def test_sparse_receiver_preserves_excluded_data_when_applying_allowed_patch(self):
        omitted = Path('job-market/db/fixture.json')
        omitted.parent.mkdir(parents=True); omitted.write_text('Large unrelated tracked data fixture\n')
        self.git('add', '.'); self.git('commit', '-qm', 'Unrelated data')
        patch = self.patch_for('docs/recovered.md', 'Bounded allowed source change\n')
        self.git('sparse-checkout', 'set', 'docs')
        self.assertFalse(omitted.exists())
        PATCH.apply(patch)
        self.assertEqual(Path('docs/recovered.md').read_text(), 'Bounded allowed source change\n')
        self.assertEqual(self.git('diff', '--cached', '--name-only').strip(), b'docs/recovered.md')
        self.assertIn(b'Large unrelated tracked data fixture', self.git('show', ':job-market/db/fixture.json'))
