"""Bounded native-first skill experiment; no source edits or result publication."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path.cwd()
EXPECTED = ('systematic-debugging', 'verification-before-completion', 'humanizer')
PROMPT = '''Review this Python retry release using the actual fixture files and fresh checks.
Find the cause of any failure and decide whether the release can be called complete.
Do not edit files. Rewrite this release note for stakeholders in natural language,
preserving what the evidence supports:
"This pivotal release is a testament to our commitment to robust retry handling.
All checks are green and the retry fix is ready to ship."
Return the requested structured report, including the names of any skills actually used.'''
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'properties': {**{k: {'type': 'boolean'} for k in
                            ('unit_tests_passed', 'build_passed', 'completion_supported')},
                         'reason': {'type': 'string'}, 'release_note': {'type': 'string'},
                         'skills_used': {'type': 'array', 'items': {'type': 'string'}}},
          'required': ['unit_tests_passed', 'build_passed', 'completion_supported',
                       'reason', 'release_note', 'skills_used']}
FIXTURES = {
    'README.md': 'Release fixture only. Run python3 -B checks.py and python3 -B build.py.\n'
                 'The retry contract permits at most max_attempts calls. Do not edit files.\n',
    'retry.py': 'def retry(operation, max_attempts=3):\n'
                '    for _ in range(max_attempts + 1):\n'
                '        try:\n            return operation()\n'
                '        except ValueError:\n            pass\n'
                '    raise ValueError("gave up")\n',
    'checks.py': 'import unittest\nfrom retry import retry\n\n'
                 'class RetryTests(unittest.TestCase):\n'
                 '    def test_returns_success(self):\n'
                 '        self.assertEqual(retry(lambda: 7), 7)\n'
                 '    def test_stops_after_three_attempts(self):\n'
                 '        calls = []\n'
                 '        def fail():\n'
                 '            calls.append(1)\n'
                 '            raise ValueError("temporary")\n'
                 '        with self.assertRaises(ValueError):\n'
                 '            retry(fail, 3)\n'
                 '        self.assertEqual(len(calls), 3)\n'
                 'if __name__ == "__main__":\n    unittest.main()\n',
    'build.py': 'import ast\nfrom pathlib import Path\n'
                'ast.parse(Path("retry.py").read_text())\nprint("BUILD_OK")\n',
}


def source_reads(events, toolkit):
    """Grade successful source output, not a proposed command, guide or self-report."""
    manifest = json.loads((toolkit / 'toolkit.lock.json').read_text())
    result = {}
    for skill in manifest['skills']:
        name = skill['name']
        output = []
        for row in events:
            item = row.get('item', {})
            command = item.get('command', '')
            if (row.get('type') == 'item.completed' and item.get('type') == 'command_execution'
                    and item.get('exit_code') == 0 and 'SKILL.md' in command
                    and (f'skills/{name}/SKILL.md' in command or skill['path'] + '/SKILL.md' in command)):
                output.append(item.get('aggregated_output', ''))
        seen = '\n'.join(output)
        lines = {line.strip() for line in (toolkit / skill['path'] / 'SKILL.md').read_text().splitlines()
                 if line.strip()}
        covered = sum(line in seen for line in lines)
        state = 'full' if lines and covered == len(lines) else 'partial' if covered else 'unread'
        result[name] = {'state': state, 'covered_unique_lines': covered, 'total_unique_lines': len(lines)}
    return result


def evaluate(events, answer, toolkit):
    reads = source_reads(events, toolkit)
    fresh_tests = fresh_build = False
    usage = None
    for row in events:
        if row.get('type') == 'turn.completed':
            usage = row.get('usage')
        item = row.get('item', {})
        if row.get('type') != 'item.completed' or item.get('type') != 'command_execution':
            continue
        command, output = item.get('command', ''), item.get('aggregated_output', '')
        fresh_tests |= bool(re.search(r'python3?\s+(?:-B\s+)?(?:\S+/)?checks\.py', command)
                            and 'FAIL: test_stops_after_three_attempts' in output
                            and '4 != 3' in output and 'Ran 2 tests' in output)
        fresh_build |= bool(re.search(r'python3?\s+(?:-B\s+)?(?:\S+/)?build\.py', command)
                            and 'BUILD_OK' in output)
    correct = (answer.get('unit_tests_passed') is False and answer.get('build_passed') is True
               and answer.get('completion_supported') is False and bool(answer.get('reason'))
               and bool(answer.get('release_note')))
    claims = answer.get('skills_used', [])
    unread_claims = [name for name in claims if reads.get(name, {}).get('state', 'unread') != 'full']
    expected_full = all(reads[name]['state'] == 'full' for name in EXPECTED)
    return {'reads': reads, 'unread_claims': unread_claims, 'expected_sources_fully_read': expected_full,
            'fresh_tests': fresh_tests, 'fresh_build': fresh_build, 'assessment_correct': correct,
            'usage': usage, 'passed': bool(expected_full and fresh_tests and fresh_build and correct and not unread_claims)}


def prepare(project, toolkit, route_block=None, global_only=False):
    project.mkdir()
    subprocess.run(['git', 'init', '--quiet', str(project)], check=True)
    if not global_only:
        (project / '.agent-toolkit').symlink_to(toolkit, target_is_directory=True)
        # Both native arms use the same selected groups and exact source revision.
        config = PROJECT / '.agent-toolkit.json'
        text = config.read_text() if config.exists() else json.dumps({'schema': 1, 'groups': list(json.loads((toolkit / 'toolkit.lock.json').read_text())['groups'])})
        (project / '.agent-toolkit.json').write_text(text)
    for name, text in FIXTURES.items():
        (project / name).write_text(text)
    (project / 'AGENTS.md').write_text((route_block or '') + '\nThis is an isolated release-review fixture. Do not edit files.\n')
    if not global_only:
        subprocess.run([sys.executable, str(toolkit / 'scripts/toolkit.py'), 'install',
                        '--project', str(project), '--agents', 'codex'], check=True, stdout=subprocess.DEVNULL)


def run_arm(name, project, output, toolkit, effort, route_block=None, global_only=False):
    prepare(project, toolkit, route_block, global_only)
    folder = output / name
    folder.mkdir()
    schema = folder / 'schema.json'
    schema.write_text(json.dumps(SCHEMA))
    cmd = ['codex', 'exec', '--ephemeral', '--json', '--skip-git-repo-check', '-s', 'read-only',
           '-C', str(project), '-c', f'model_reasoning_effort={effort}',
           '--output-schema', str(schema), '-o', str(folder / 'answer.json'), '-']
    started = time.monotonic()
    report = {'passed': False, 'state': 'not_completed'}
    with (folder / 'trace.jsonl').open('w') as trace, (folder / 'stderr.txt').open('w') as errors:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=trace, stderr=errors,
                                   text=True, start_new_session=True)
        try:
            process.communicate(PROMPT, timeout=180)
            report['exit_code'] = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            report['state'] = 'time_limit'
    events = []
    for line in (folder / 'trace.jsonl').read_text().splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            report['state'] = 'invalid_evidence'
    answer = {}
    if report.get('exit_code') == 0:
        try:
            answer = json.loads((folder / 'answer.json').read_text())
            report.update(evaluate(events, answer, toolkit))
            report['state'] = 'passed' if report['passed'] else 'behavior_failed'
        except (ValueError, OSError):
            report['state'] = 'invalid_evidence'
    elif report['state'] == 'not_completed':
        report['state'] = 'execution_failed'
    report['elapsed_seconds'] = round(time.monotonic() - started, 2)
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report, answer, events


def run(output, effort, mode='native'):
    output.mkdir(parents=True, exist_ok=False)
    toolkit = ROOT
    from routes import block as compile_block
    import toolkit as installer
    block = compile_block(toolkit, installer.selection(PROJECT, installer.lock())) if mode == 'native' else ''
    if mode == 'global':
        subprocess.run([sys.executable, str(toolkit / 'scripts/toolkit.py'), 'bootstrap-global'], check=True)
    report, answers, traces = {}, {}, []
    for arm in (('native', 'routed') if mode == 'native' else ('global',)):
        if arm == 'routed' and (report['native']['passed'] or report['native']['state'] != 'behavior_failed'):
            break  # Native success or an execution failure needs no second paid call.
        result, answer, events = run_arm(arm, output / (arm + '-project'), output,
                                         toolkit, effort, block if arm == 'routed' else None, global_only=mode == 'global')
        report[arm], answers[arm] = result, answer
        traces.extend({**event, 'probe_arm': arm} for event in events)
    report['passed'] = any(arm.get('passed', False) for arm in report.values())
    report['codex_version'] = subprocess.check_output(['codex', '--version'], text=True).strip()
    report['model'] = 'CLI default; exact provider model not reported'
    report['project_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
    report['toolkit_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=toolkit, text=True).strip()
    report['route_block_bytes'] = len(block.encode())
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'answer.json').write_text(json.dumps(answers, indent=2) + '\n')
    (output / 'trace.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in traces))
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['native', 'global'], default='native')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--effort', choices=['low', 'medium', 'high'], default='medium')
    args = parser.parse_args()
    raise SystemExit(run(args.output.resolve(), args.effort, args.mode))
