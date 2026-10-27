import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import intake
import skills


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / 'toolkit'
        self.root.mkdir()
        shutil.copytree(ROOT / 'catalog', self.root / 'catalog')
        shutil.copy(ROOT / 'toolkit.lock.json', self.root)
        manifest = json.loads((ROOT / 'toolkit.lock.json').read_text())
        for relative in manifest['files']:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, target)
        self.source = base / 'source'
        self.source.mkdir()
        self.git('init', '--quiet')
        self.git('remote', 'add', 'origin', 'https://example.invalid/reviewed-skill')
        (self.source / 'LICENSE').write_text('Test-only license fixture')
        (self.source / 'skill').mkdir()
        self.body = self.source / 'skill/SKILL.md'
        self.body.write_text('---\nname: intake-fixture\n---\nA fixture capability.')
        self.commit()
        self.guide = base / 'guide.md'
        self.guide.write_text((ROOT / 'catalog/animate.md').read_text().replace(
            '../vendor/emil/skills/animate/SKILL.md', '../vendor/intake-fixture/skills/SKILL.md'))
        self.request = dict(name='intake-fixture', checkout=str(self.source), source_path='skill',
                            license_path='LICENSE', repository='https://example.invalid/reviewed-skill',
                            revision=self.git('rev-parse', 'HEAD'), guide=str(self.guide), group='development',
                            review_notes='Test fixture only; no live compatibility claim.')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), '-c', 'user.name=Fixture',
                                       '-c', 'user.email=fixture@example.invalid', *args], text=True).strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'Fixture revision')

    def test_dry_run_apply_idempotent_edit_and_rollback_revision(self):
        before = (self.root / 'toolkit.lock.json').read_bytes()
        self.assertEqual(intake.intake(self.request, root=self.root)['state'], 'validated-proposal')
        self.assertEqual(before, (self.root / 'toolkit.lock.json').read_bytes())
        first_revision = self.request['revision']
        intake.intake(self.request, root=self.root, apply=True)
        dest = self.root / 'vendor/intake-fixture/skills/SKILL.md'
        first_content = dest.read_bytes()
        self.assertEqual(intake.intake(self.request, root=self.root, apply=True)['changed_files'], [])
        # Uncommitted source changes must not be imported.
        self.body.write_text('New committed guidance')
        self.assertEqual(intake.intake(self.request, root=self.root, apply=True)['changed_files'], [])
        self.commit()
        self.request['revision'] = self.git('rev-parse', 'HEAD')
        intake.intake(self.request, root=self.root, apply=True)
        self.assertEqual(dest.read_text(), 'New committed guidance')
        self.git('checkout', '--quiet', first_revision)
        self.request['revision'] = first_revision
        intake.intake(self.request, root=self.root, apply=True)
        self.assertEqual(dest.read_bytes(), first_content)

    def test_manual_restriction_rejected_before_changes(self):
        self.body.write_text('---\ndisable-model-invocation: true\n---\nManual only')
        self.commit()
        self.request['revision'] = self.git('rev-parse', 'HEAD')
        before = (self.root / 'toolkit.lock.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'restriction mismatch'):
            intake.intake(self.request, root=self.root, apply=True)
        self.assertEqual(before, (self.root / 'toolkit.lock.json').read_bytes())
        self.assertFalse((self.root / 'vendor/intake-fixture').exists())

    def test_symlinks_traversal_and_stale_revision_rejected(self):
        for key, value in [('source_path', '../skill'), ('repository', 'https://token@example.invalid/repo'),
                           ('revision', '0' * 40)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.intake({**self.request, key: value}, root=self.root, apply=True)
        (self.source / 'skill/escape').symlink_to('/etc/passwd')
        self.commit()
        self.request['revision'] = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'regular committed'):
            intake.intake(self.request, root=self.root, apply=True)

    def test_redirected_destination_and_concurrent_intake_rejected(self):
        (self.root / '.intake-lock').mkdir()
        with self.assertRaisesRegex(ValueError, 'Another intake'):
            intake.intake(self.request, root=self.root)
        (self.root / '.intake-lock').rmdir()
        (self.root / 'vendor/intake-fixture').symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            intake.intake(self.request, root=self.root, apply=True)

    def test_partial_write_failure_restores_existing_files(self):
        before = (self.root / 'catalog/README.md').read_bytes()
        original = Path.write_bytes
        fired = False

        def fail_once(path, content):
            nonlocal fired
            if path == self.root / 'vendor/intake-fixture/skills/SKILL.md' and not fired:
                fired = True
                raise OSError('Injected write failure')
            return original(path, content)

        with patch.object(Path, 'write_bytes', fail_once), self.assertRaisesRegex(OSError, 'Injected'):
            intake.intake(self.request, root=self.root, apply=True)
        self.assertEqual(before, (self.root / 'catalog/README.md').read_bytes())
        self.assertFalse((self.root / 'catalog/intake-fixture.md').exists())
        self.assertFalse((self.root / '.intake-lock').exists())
        self.assertFalse((self.root / 'vendor/intake-fixture').exists())
        skills.catalogue(self.root)
        self.assertEqual(intake.intake(self.request, root=self.root, apply=True)['state'], 'applied')


if __name__ == '__main__':
    unittest.main()
