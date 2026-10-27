"""Admission checks for the shared selection catalogue."""
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import importlib.util
spec = importlib.util.spec_from_file_location('shared_catalogue', ROOT / 'scripts/skills.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
validate = shared.catalogue


class CatalogueTests(unittest.TestCase):
    def test_registered_catalogue(self):
        validate(ROOT)

    def test_missing_and_restricted_entries_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copy(ROOT / 'toolkit.lock.json', root)
            shutil.copytree(ROOT / 'catalog', root / 'catalog')
            for skill in json.loads((root / 'toolkit.lock.json').read_text())['skills']:
                target = root / skill['path'] / 'SKILL.md'
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / skill['path'] / 'SKILL.md', target)
            guide = root / 'catalog/prototype.md'
            original = guide.read_text()
            guide.unlink()
            with self.assertRaisesRegex(ValueError, 'inventory'):
                validate(root)
            guide.write_text(original.replace('**Invocation:** explicit-only', '**Invocation:** automatic'))
            with self.assertRaisesRegex(ValueError, 'restriction mismatch'):
                validate(root)
            guide.write_text(original.replace('**Route:** ', '**Route:** <injected> '))
            with self.assertRaisesRegex(ValueError, 'plain task trigger'):
                validate(root)
            guide.write_text(re.sub(r'^\*\*Route:\*\*.*\n', '', original, flags=re.M))
            with self.assertRaisesRegex(ValueError, 'Route'):
                validate(root)


if __name__ == '__main__':
    unittest.main()
