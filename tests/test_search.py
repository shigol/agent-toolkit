import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shared_skills', ROOT / 'scripts/skills.py')
skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(skills)


class SearchTests(unittest.TestCase):
    def test_independent_tasks_and_abstention(self):
        for query, expected in [
            ('Refine the dashboard typography and hierarchy', 'impeccable'),
            ('Make this product update sound natural without changing claims', 'humanizer'),
            ('Estimate TAM SAM and SOM in the UK', 'market-sizing'),
            ('Animate a popover opening smoothly', 'animate'),
            ('The nightly import dropped half its rows since Tuesday; find why and fix it', 'systematic-debugging'),
        ]:
            with self.subTest(query=query):
                names = [r['name'] for r in skills.search(query)]
                self.assertIn(expected, names)
        self.assertEqual(skills.search('PostgreSQL replication deadlock retry'), [])
        self.assertEqual(skills.search('Diagnose database replication lag and retry deadlocks'), [])
        self.assertEqual(skills.search(''), [])

    def test_negative_examples_are_not_positive_matches(self):
        self.assertEqual(skills.search('authorship'), [])

    def test_restrictions_are_preserved(self):
        self.assertNotIn('prototype', [r['name'] for r in skills.search('prototype variants')])
        rows = skills.search('prototype variants', include_restricted=True)
        self.assertEqual(next(r for r in rows if r['name'] == 'prototype')['invocation'], 'explicit-only')

    def test_groups_do_not_hide_library_but_exclusions_do(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            config = project / '.agent-toolkit.json'
            config.write_text(json.dumps({'schema': 1, 'groups': ['design'], 'native_limit': 1}))
            cmd = [sys.executable, str(ROOT / 'scripts/skills.py'), 'search', '--project', folder,
                   '--query', 'Estimate TAM SAM and SOM']
            self.assertIn('market-sizing', subprocess.check_output(cmd, text=True))
            config.write_text(json.dumps({'schema': 1, 'groups': ['design'], 'exclude': ['market-sizing']}))
            self.assertNotIn('market-sizing', subprocess.check_output(cmd, text=True))

    def test_limits_and_determinism(self):
        query = 'animation motion interface video product'
        rows = skills.search(query, limit=2)
        self.assertLessEqual(len(rows), 2)
        self.assertEqual(rows, skills.search(query, limit=2))
        self.assertLessEqual(len(json.dumps(skills.search(query, max_chars=600), ensure_ascii=False)), 600)
        for kwargs in ({'limit': 6}, {'limit': 0}, {'max_chars': 100000}):
            with self.assertRaises(ValueError):
                skills.search(query, **kwargs)

    def test_three_hundred_entries_keep_output_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'catalog').mkdir()
            rows, manifest = [], {'skills': []}
            for i in range(320):
                name = f'fixture-{i}'
                path = f'vendor/{name}'
                (root / path).mkdir(parents=True)
                (root / path / 'SKILL.md').write_text('Test source')
                manifest['skills'].append({'name': name, 'path': path, 'package': 'fixture'})
                text = (ROOT / 'catalog/animate.md').read_text().replace(
                    '../vendor/emil/skills/animate/SKILL.md', f'../{path}/SKILL.md')
                if i == 319:
                    text = text.replace('**Purpose:** ', '**Purpose:** Uniquehelicopter ')
                (root / 'catalog' / (name + '.md')).write_text(text)
                rows.append(f'| [{name}]({name}.md) | Fixture | automatic |')
            (root / 'toolkit.lock.json').write_text(json.dumps(manifest))
            (root / 'catalog/README.md').write_text('\n'.join(rows))
            self.assertEqual(skills.search('uniquehelicopter', root=root)[0]['name'], 'fixture-319')
            result = skills.search('web motion', root=root)
            self.assertLessEqual(len(result), 5)
            self.assertLessEqual(len(json.dumps(result, ensure_ascii=False)), 4000)


if __name__ == '__main__':
    unittest.main()
