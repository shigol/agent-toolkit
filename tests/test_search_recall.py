"""Deterministic fallback retrieval regression; not live agent-selection proof."""
import json
from pathlib import Path
import unittest

from test_search import skills

ROOT = Path(__file__).resolve().parents[1]


class RecallTests(unittest.TestCase):
    def test_labeled_task_recall_and_abstention(self):
        cases = json.loads((ROOT / 'tests/search-cases.json').read_text())
        self.assertGreaterEqual(len(cases['positive']), 40)
        self.assertEqual(len({row['query'] for row in cases['positive']}), len(cases['positive']))
        hits, misses = 0, []
        registered = {row['name'] for row in skills.catalogue(ROOT)}
        for row in cases['positive']:
            self.assertIn(row['expected'], registered)
            result = skills.search(row['query'], limit=3)
            names = [candidate['name'] for candidate in result]
            self.assertTrue(all(candidate['score'] >= skills.MIN_SCORE for candidate in result))
            if row['expected'] in names:
                hits += 1
            else:
                misses.append((row['query'], row['expected'], names))
        self.assertGreaterEqual(hits / len(cases['positive']), .9, misses)
        for query in cases['abstain']:
            with self.subTest(query=query):
                self.assertEqual(skills.search(query), [])

    def test_reported_misses_stay_fixed(self):
        for query, expected in (
            ('write cover letter email', 'humanizer'),
            ('review PR for bugs', 'systematic-debugging'),
            ('debug why scoring job failed', 'systematic-debugging'),
        ):
            with self.subTest(query=query):
                self.assertEqual(expected, skills.search(query, limit=3)[0]['name'])


if __name__ == '__main__':
    unittest.main()
