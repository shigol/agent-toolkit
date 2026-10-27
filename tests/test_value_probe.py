import random
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import value_probe


class ValueProbeTests(unittest.TestCase):
    def test_nine_pairs_both_conditions_and_swapped_positions(self):
        pairs = value_probe.slots(random.Random(24))
        self.assertEqual(len(pairs), 9)
        self.assertEqual(len({p['pair'] for p in pairs}), 9)
        for p in pairs:
            self.assertEqual({p['A'], p['B']}, {'with', 'without'})
        for task in value_probe.TASKS:
            self.assertEqual({p['A'] for p in pairs if p['task'] == task}, {'with', 'without'})

    def test_render_accepts_static_fixture_and_rejects_active_or_remote_content(self):
        self.assertTrue(value_probe.safe_static(value_probe.UI))
        self.assertTrue(value_probe.safe_static('<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M0 0L10 10" stroke="currentColor"/></svg><div data-state="saved"></div>'))
        for body in ['<script>alert(1)</script>', '<button onclick="x()">', '<img src="https://example.invalid/x">', '<style>@import "x";</style>', '<style>body{background:url(x)}</style>', '<object data="data:text/html,anything">', '<meta http-equiv="refresh" content="0;url=file:///etc/hosts">', '<a href="&#106;avascript:alert(1)">x</a>']:
            self.assertFalse(value_probe.safe_static(body))

    def test_task_facts_and_target_sources_resolve(self):
        import json
        manifest = json.loads((value_probe.ROOT / 'toolkit.lock.json').read_text())
        names = {s['name'] for s in manifest['skills']}
        for task in value_probe.TASKS.values():
            self.assertIn(task['skill'], names)
        self.assertIn('location eligibility remains unknown', value_probe.TASKS['outreach']['task'])
        self.assertIn('Do not edit files', value_probe.TASKS['verification']['task'])
        self.assertIn('Salary not provided', value_probe.UI)
