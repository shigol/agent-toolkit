import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('native_probe', Path(__file__).resolve().parents[1] / 'scripts/selection_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
TOOLKIT = Path(__file__).resolve().parents[1]


def event(command, output, exit_code=0):
    return {'type': 'item.completed', 'item': {'type': 'command_execution',
            'command': command, 'aggregated_output': output, 'exit_code': exit_code}}


class NativeProbeTests(unittest.TestCase):
    def test_source_claims_require_actual_successful_output(self):
        source = TOOLKIT / 'vendor/verification-before-completion/skills/SKILL.md'
        command = 'cat .agents/skills/verification-before-completion/SKILL.md'
        for events in ([], [event(command, '')], [event(command, source.read_text(), 1)],
                       [event('cat catalog/verification-before-completion.md', source.read_text())]):
            self.assertEqual(probe.source_reads(events, TOOLKIT)['verification-before-completion']['state'], 'unread')
        full = [event(command, source.read_text())]
        self.assertEqual(probe.source_reads(full, TOOLKIT)['verification-before-completion']['state'], 'full')
        self.assertEqual(probe.source_reads([event(command, source.read_text()[:200])], TOOLKIT)
                         ['verification-before-completion']['state'], 'partial')

    def test_chunked_reads_can_cover_whole_source(self):
        body = (TOOLKIT / 'vendor/humanizer/skills/SKILL.md').read_text()
        lines = body.splitlines(keepends=True)
        first, second = ''.join(lines[:len(lines) // 2]), ''.join(lines[len(lines) // 2:])
        command = 'cat .agents/skills/humanizer/SKILL.md'
        result = probe.source_reads([event(command, first), event(command, second)], TOOLKIT)
        self.assertEqual(result['humanizer']['state'], 'full')

    def test_global_fixture_has_no_project_toolkit_or_native_links(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / 'global-only'
            probe.prepare(project, TOOLKIT, global_only=True)
            for name in ('.agent-toolkit', '.agent-toolkit.json', '.agents'):
                self.assertFalse((project / name).exists())
            self.assertNotIn('catalogue', (project / 'AGENTS.md').read_text())

    def test_correct_answer_alone_does_not_pass(self):
        answer = dict(unit_tests_passed=False, build_passed=True, completion_supported=False,
                      reason='Retry exceeds its limit', release_note='The release remains blocked.',
                      skills_used=['humanizer'])
        result = probe.evaluate([], answer, TOOLKIT)
        self.assertTrue(result['assessment_correct'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['unread_claims'], ['humanizer'])

    def test_fixture_has_real_failing_check_and_passing_build(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, text in probe.FIXTURES.items():
                (Path(folder) / name).write_text(text)
            checks = subprocess.run(['python3', '-B', 'checks.py'], cwd=folder, capture_output=True, text=True)
            self.assertEqual(checks.returncode, 1)
            self.assertIn('4 != 3', checks.stderr)
            self.assertIn('Ran 2 tests', checks.stderr)
            build = subprocess.run(['python3', '-B', 'build.py'], cwd=folder, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0)
            self.assertIn('BUILD_OK', build.stdout)
            path = Path(folder) / 'retry.py'
            path.write_text(path.read_text().replace('range(max_attempts + 1)', 'range(max_attempts)'))
            green = subprocess.run(['python3', '-B', 'checks.py'], cwd=folder, capture_output=True, text=True)
            self.assertEqual(green.returncode, 0)


if __name__ == '__main__':
    unittest.main()
