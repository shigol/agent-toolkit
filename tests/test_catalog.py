"""Admission checks for the shared selection catalogue."""
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('Purpose', 'Invocation', 'Use when', 'Do not use when',
          'Overlaps and default', 'Requirements', 'Expected output',
          'Positive example', 'Negative example', 'Source')


def validate(root):
    skills = json.loads((root / 'toolkit.lock.json').read_text())['skills']
    if {p.stem for p in (root / 'catalog').glob('*.md') if p.name != 'README.md'} != {s['name'] for s in skills}:
        raise ValueError('Catalogue inventory differs from registered skills')
    index = (root / 'catalog/README.md').read_text()
    for skill in skills:
        name = skill['name']
        text = (root / 'catalog' / (name + '.md')).read_text()
        values = {}
        for field in FIELDS:
            found = re.findall(r'^\*\*' + re.escape(field) + r':\*\* (\S.*)$', text, re.M)
            if len(found) != 1:
                raise ValueError(f'{name}: missing or repeated {field}')
            values[field] = found[0].strip()
        if values['Source'] != f"[Pinned SKILL.md](../{skill['path']}/SKILL.md)":
            raise ValueError(f'{name}: incorrect source link')
        body = (root / skill['path'] / 'SKILL.md').read_text()
        frontmatter = body.split('---', 2)[1] if body.startswith('---\n') else ''
        manual = bool(re.search(r'^disable-model-invocation:\s*true\s*$', frontmatter, re.M))
        invocation = values['Invocation']
        if invocation not in {'automatic', 'explicit-only', 'explicit-direction'}:
            raise ValueError(f'{name}: invalid invocation')
        if manual != (invocation == 'explicit-only'):
            raise ValueError(f'{name}: source invocation restriction mismatch')
        row = rf'^\| \[{re.escape(name)}\]\({re.escape(name)}\.md\) \| .+ \| {invocation} \|$'
        if len(re.findall(row, index, re.M)) != 1:
            raise ValueError(f'{name}: missing or inconsistent index row')


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


if __name__ == '__main__':
    unittest.main()
