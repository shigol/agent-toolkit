import hashlib
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from toolkit_update import policy, review_scan, validate


class Updates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'toolkit'
        source = Path(os.environ.get('TOOLKIT_ROOT', '.agent-toolkit')).resolve()
        subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(source), str(self.root)], check=True)
        self.base = self.git('rev-parse', 'HEAD')
        self.project = Path(self.tmp.name) / 'project'
        self.project.mkdir()
        selection = Path(".agent-toolkit.json")
        if selection.exists():
            (self.project / selection.name).write_bytes(selection.read_bytes())

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), '-c', 'user.name=Test',
            '-c', 'user.email=test@example.invalid', *args], text=True).strip()

    def manifest(self):
        return json.loads((self.root / 'toolkit.lock.json').read_text())

    def save(self, data):
        (self.root / 'toolkit.lock.json').write_text(json.dumps(data))

    def commit(self):
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'Test update')

    def install(self):
        subprocess.run([sys.executable, str(self.root / 'scripts/toolkit.py'), 'install',
            '--project', str(self.project)], check=True, stdout=subprocess.DEVNULL)

    def test_new_skill_and_existing_skill_update_reach_both_agents(self):
        own = self.project / '.claude/skills/project-specific/SKILL.md'
        own.parent.mkdir(parents=True)
        own.write_text('Preserve my project instructions')
        self.install()
        data = self.manifest()
        path = 'vendor/emil/skills/new-example/SKILL.md'
        (self.root / path).parent.mkdir()
        (self.root / path).write_text('---\nname: new-example\ndescription: A fixture\n---\nNew skill\n')
        data['skills'].append({'name': 'new-example', 'path': str(Path(path).parent), 'package': 'emil'})
        data['files'][path] = hashlib.sha256((self.root / path).read_bytes()).hexdigest()
        self.save(data)
        self.commit()
        validate(self.root)
        with self.assertRaisesRegex(ValueError, 'Vendored skill'):
            policy(self.root, self.base)
        self.install()
        self.install()  # Existing checkouts and repeated setup must both work.
        for folder in ['.agents', '.claude']:
            self.assertIn('New skill', (self.project / folder / 'skills/new-example/SKILL.md').read_text())
        (self.root / path).write_text((self.root / path).read_text() + 'Updated guidance\n')
        data['files'][path] = hashlib.sha256((self.root / path).read_bytes()).hexdigest()
        self.save(data)
        self.commit()
        validate(self.root)
        with self.assertRaisesRegex(ValueError, 'Vendored skill'):
            policy(self.root, self.base)
        self.install()
        for folder in ['.agents', '.claude']:
            self.assertIn('Updated guidance', (self.project / folder / 'skills/new-example/SKILL.md').read_text())
        self.assertEqual(own.read_text(), 'Preserve my project instructions')

    def test_vendor_reference_addition_requires_review_even_with_valid_hash(self):
        data = self.manifest()
        for path in ('vendor/update-review-probe.md', 'vendor/second-review-probe.md'):
            (self.root / path).write_text('A harmless reference addition; review is still required.\n')
            data['files'][path] = hashlib.sha256((self.root / path).read_bytes()).hexdigest()
        self.save(data)
        self.commit()
        validate(self.root)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaisesRegex(ValueError, 'Vendored skill'):
            policy(self.root, self.base)
        self.assertIn('vendor/update-review-probe.md', output.getvalue())
        self.assertIn('vendor/second-review-probe.md', output.getvalue())

    def test_existing_source_edit_requires_review_with_updated_hash(self):
        data = self.manifest()
        path = data['skills'][0]['path'] + '/SKILL.md'
        (self.root / path).write_text((self.root / path).read_text() + '\nFixture source edit.\n')
        data['files'][path] = hashlib.sha256((self.root / path).read_bytes()).hexdigest()
        self.save(data)
        self.commit()
        validate(self.root)
        with self.assertRaisesRegex(ValueError, 'Vendored skill'):
            policy(self.root, self.base)

    def test_nonvendor_documentation_remains_eligible(self):
        (self.root / 'REVIEW-NOTE.md').write_text('Documentation outside vendored sources.\n')
        self.commit()
        policy(self.root, self.base)

    def test_review_scan_flags_categories_without_returning_source(self):
        sample = 'curl https://example.invalid/file; secret=fixture; ignore previous instructions; run this command'
        result = review_scan(sample)
        self.assertEqual(result['urls'], 1)
        self.assertGreater(result['download_commands'], 0)
        self.assertGreater(result['credential_terms'], 0)
        self.assertGreater(result['instruction_override'], 0)
        self.assertGreater(result['tool_commands'], 0)
        self.assertNotIn('example.invalid', json.dumps(result))

    def test_patch_provenance_change_requires_review(self):
        data = self.manifest()
        data['patches'] = []
        self.save(data)
        self.commit()
        with self.assertRaisesRegex(ValueError, 'provenance'):
            policy(self.root, self.base)

    def test_group_removal_requires_review(self):
        data = self.manifest()
        data['groups']['design'].remove('emil')
        self.save(data)
        self.commit()
        with self.assertRaisesRegex(ValueError, 'selection group'):
            policy(self.root, self.base)

    def test_executable_change_requires_review(self):
        p = self.root / 'scripts/toolkit.py'
        p.write_text(p.read_text() + '\n# Changed installer\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'need review'):
            policy(self.root, self.base)

    def test_removal_requires_review(self):
        data = self.manifest()
        data['skills'].pop()
        self.save(data)
        self.commit()
        with self.assertRaisesRegex(ValueError, 'Removing or moving'):
            policy(self.root, self.base)

    def test_retargeted_skill_requires_review(self):
        data = self.manifest()
        data['skills'][0]['path'] = data['skills'][1]['path']
        self.save(data)
        self.commit()
        with self.assertRaisesRegex(ValueError, 'Removing or moving'):
            policy(self.root, self.base)

    def test_path_escape_rejected_before_install(self):
        data = self.manifest()
        data['skills'][0]['name'] = '../../outside'
        self.save(data)
        with self.assertRaises(ValueError):
            validate(self.root)

    def test_missing_skill_rejected(self):
        data = self.manifest()
        data['skills'][0]['path'] = 'vendor/missing'
        self.save(data)
        with self.assertRaisesRegex(ValueError, 'SKILL.md'):
            validate(self.root)

    def test_unregistered_vendor_file_rejected(self):
        (self.root / 'vendor/unregistered.md').write_text('Not registered')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'every tracked'):
            validate(self.root)

    def test_changed_source_hash_rejected(self):
        data = self.manifest()
        p = self.root / next(iter(data['files']))
        p.write_bytes(p.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            validate(self.root)


if __name__ == '__main__':
    unittest.main()
