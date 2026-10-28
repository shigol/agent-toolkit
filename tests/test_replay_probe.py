import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import replay_probe as probe


def case(case_id='X01', required=None):
    return {'id': case_id, 'repository': probe.REPOSITORIES[1] if case_id in ('X12', 'X17') else probe.REPOSITORIES[0],
            'brief': 'Use actual repository facts.', 'must_read': required or {},
            'acceptable_additional_shared_reads': [],
            'forbidden_if_unrequested': ['prototype', 'pick-ui-library', 'review-animations', 'design-taste-frontend'],
            'maximum_unrelated_shared_bodies': 0}


def event(name, body, code=0):
    return {'type': 'item.completed', 'item': {'type': 'command_execution',
            'command': f'cat .agents/skills/{name}/SKILL.md', 'aggregated_output': body, 'exit_code': code}}


def commit(project):
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    subprocess.run(['git', '-C', str(project), 'add', '--all'], check=True)
    subprocess.run(['git', '-C', str(project), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.invalid', '-c', 'core.hooksPath=/dev/null',
                    'commit', '-qm', 'Fixture'], check=True)


class ReplayProbeTests(unittest.TestCase):
    def test_only_recommended_repo_cases_and_prompt_has_no_grading_fields(self):
        cases = [case(name) for name in (*probe.SMOKE, 'X42')]
        selected = probe.select_cases({'cases': cases}, probe.REPOSITORIES[0])
        self.assertEqual([row['id'] for row in selected], ['X01', 'X07', 'X32'])
        self.assertEqual([row['id'] for row in probe.select_cases({'cases': cases}, probe.REPOSITORIES[1])], ['X12', 'X17'])
        brief = case(required={'humanizer': 'full'})
        text = probe.prompt(brief)
        self.assertEqual(text, 'Repository: shigol/career\n\nUse actual repository facts.\n\n' + probe.LOCAL_ONLY + '\n')
        for label in ('X01', 'must_read', 'humanizer', 'forbidden', 'expected'):
            self.assertNotIn(label, text)
        with self.assertRaises(ValueError):
            probe.select_cases({'cases': cases + [cases[0]]}, probe.REPOSITORIES[0])
        with self.assertRaises(ValueError):
            probe.select_cases({'cases': []}, probe.REPOSITORIES[1])

    def test_read_grading_requires_all_successful_source_lines_and_separates_correctness(self):
        required = case(required={'verification-before-completion': 'full'})
        body = (probe.ROOT / 'vendor/verification-before-completion/skills/SKILL.md').read_text()
        for events in ([], [event('verification-before-completion', body[:200])],
                       [event('verification-before-completion', body, 1)]):
            result = probe.grade(required, events, 'Missing fixture, cannot verify.', probe.ROOT)
            self.assertFalse(result['source_selection_passed'])
            self.assertEqual(result['task_correctness']['state'], 'pending_review')
        lines = body.splitlines(keepends=True)
        events = [event('verification-before-completion', ''.join(lines[:20])),
                  event('verification-before-completion', ''.join(lines[20:]))]
        self.assertTrue(probe.grade(required, events, 'Evidence.', probe.ROOT)['source_selection_passed'])

    def test_patterns_allowed_for_short_report_but_not_full_document(self):
        body = (probe.ROOT / 'vendor/humanizer/skills/SKILL.md').read_text()
        headings = '\n'.join(re.findall(r'^### \d+\..+$', body, re.M))
        patterns = '### 1.' + body.split('### 1.', 1)[1].split('\n## When not to act', 1)[0]
        self.assertFalse(probe.grade(case(required={'humanizer': 'patterns-or-full'}),
                         [event('humanizer', headings)], '', probe.ROOT)['source_selection_passed'])
        events = [event('humanizer', patterns)]
        self.assertTrue(probe.grade(case(required={'humanizer': 'patterns-or-full'}), events, '', probe.ROOT)['source_selection_passed'])
        self.assertFalse(probe.grade(case('X07', {'humanizer': 'full'}), events, '', probe.ROOT)['source_selection_passed'])

    def test_forbidden_manual_unrelated_reads_count_even_without_declaration(self):
        body = (probe.ROOT / 'vendor/emil/skills/prototype/SKILL.md').read_text()
        result = probe.grade(case('X32'), [event('prototype', body)], '92', probe.ROOT)
        self.assertEqual(result['forbidden_reads'], ['prototype'])
        self.assertEqual(result['manual_unrequested_reads'], ['prototype'])
        self.assertEqual(result['unrelated_body_count'], 1)
        self.assertFalse(result['source_selection_passed'])
        self.assertEqual(result['task_correctness']['state'], 'passed')
        self.assertEqual(probe.grade(case('X32'), [], '92\nSkills: none', probe.ROOT)['task_correctness']['state'], 'failed')

    def test_snapshot_preserves_native_links_facts_and_excludes_history_labels_untracked(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            source.mkdir()
            (source / 'facts.txt').write_text('Real committed facts\n')
            (source / 'docs').mkdir()
            (source / 'docs/schema.json').write_text('PRIVATE LABELS')
            (source / 'docs/codex-replay-v1.json').write_text('PRIVATE LABELS')
            (source / '.env.local').write_text('PRIVATE CONFIG')
            skill = source / '.agent-toolkit/vendor/test/skills'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('Native source\n')
            native = source / '.agents/skills'
            native.mkdir(parents=True)
            (native / 'test').symlink_to('../../.agent-toolkit/vendor/test/skills')
            commit(source)
            (source / 'untracked-secret').write_text('Do not copy')
            (source / 'facts.txt').write_text('Dirty working tree is not the fixture')
            popen = subprocess.Popen
            with patch.object(probe.subprocess, 'Popen', wraps=popen) as calls:
                stats = probe.snapshot(source, target, hidden_paths=('docs/schema.json',))
            batches = [call for call in calls.call_args_list if 'cat-file' in call.args[0]]
            self.assertEqual(len(batches), 1)
            self.assertIn('--batch', batches[0].args[0])
            self.assertEqual(stats['files'], 3)
            self.assertGreater(stats['bytes'], 0)
            self.assertGreaterEqual(stats['elapsed_seconds'], 0)
            self.assertEqual((target / 'facts.txt').read_text(), 'Real committed facts\n')
            self.assertEqual((target / '.agents/skills/test/SKILL.md').read_text(), 'Native source\n')
            self.assertFalse((target / '.git').exists())
            self.assertFalse((target / 'untracked-secret').exists())
            self.assertFalse((target / '.env.local').exists())
            self.assertEqual(list((target / 'docs').glob('*')), [])
            with patch.object(probe, 'MAX_SNAPSHOT_BYTES', 1):
                with self.assertRaises(probe.SnapshotError) as failure:
                    probe.snapshot(source, Path(folder) / 'too-large')
            self.assertGreater(failure.exception.stats['bytes'], 1)
            self.assertIn('elapsed_seconds', failure.exception.stats)

    def test_declared_runner_dependency_links_keep_common_caches_local(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            (source / 'node_modules/package').mkdir(parents=True)
            (source / 'node_modules/.vite').mkdir()
            target.mkdir()
            probe.link_dependencies(source, target)
            self.assertTrue((target / 'node_modules/package').is_symlink())
            self.assertFalse((target / 'node_modules/.vite').exists())
            self.assertFalse((target / 'node_modules/.cache').exists())

    def test_observed_label_schema_or_unique_grading_keys_invalidate_evidence(self):
        for text in ('must_read', '/runner/private-cases.json', 'private-cases.json',
                     'codex-replay-v1.json', 'maximum_unrelated_shared_bodies'):
            self.assertEqual(probe.label_leaks([event('humanizer', text)],
                             ('/runner/private-cases.json',))['state'], 'leaked')
        self.assertEqual(probe.label_leaks([event('humanizer', 'must_read', 1)])['state'], 'no_observed_leak')
        self.assertEqual(probe.label_leaks([event('humanizer', 'Actual source text')])['state'], 'no_observed_leak')

    def test_explicit_career_profile_matches_prepush_and_records_exact_archive_omissions(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            (source / 'tools').mkdir(parents=True)
            sparse = ['/*', *('!/' + prefix for prefix in probe.CAREER_SPARSE_PREFIXES)]
            (source / 'tools/prepush.py').write_text('SPARSE = ' + repr(sparse) + '\n')
            for prefix in probe.CAREER_SPARSE_PREFIXES:
                (source / prefix).mkdir(parents=True)
                (source / prefix / 'archive.json').write_text('a' * 1000)
            retained = ['profile/cv.md', 'job-market/reports/current.md', 'job-market/board/gaps.json',
                        'job-market/db/postings.jsonl', 'job-market/crawler/check.py']
            for name in retained:
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                (source / name).write_text('current facts')
            commit(source)
            with patch.object(probe, 'MAX_SNAPSHOT_BYTES', 512):
                stats = probe.snapshot(source, target, profile='career-prepush')
            self.assertEqual(stats['profile']['name'], 'career-prepush')
            for prefix in probe.CAREER_SPARSE_PREFIXES:
                self.assertEqual(stats['profile']['omitted_prefixes'][prefix], {'files': 1, 'bytes': 1000})
                self.assertFalse((target / prefix).exists())
            self.assertTrue(all((target / name).read_text() == 'current facts' for name in retained))
            self.assertIn('archive-dependent findings remain unverified', stats['profile']['limitation'])
            (source / 'tools/prepush.py').write_text("SPARSE = ['/*']\n")
            commit(source)
            with self.assertRaisesRegex(ValueError, 'SPARSE changed'):
                probe.snapshot(source, Path(folder) / 'drifted', profile='career-prepush')

    def test_only_pinned_engine_is_copied_with_verified_checksum_and_executable_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source', Path(folder) / 'target'
            scripts = target / 'vendor/impeccable/skills/scripts'
            scripts.mkdir(parents=True)
            (scripts / 'VERSION').write_text('1.2.3\n')
            body = b'Verified fixture engine; never executed\n'
            digest = hashlib.sha256(body).hexdigest()
            (scripts / 'engine-checksums.txt').write_text('1.2.3 impeccable-linux-x64 ' + digest + '\n')
            binary = source / 'vendor/impeccable/skills/scripts/bin/linux-x64/impeccable'
            binary.parent.mkdir(parents=True)
            (binary.parent / 'unrelated-profile').write_text('must not copy')
            import toolkit
            with patch.object(toolkit.platform, 'system', return_value='Linux'), patch.object(toolkit.platform, 'machine', return_value='x86_64'):
                self.assertEqual(probe.copy_pinned_engine(source, target)['state'], 'missing')
                binary.write_bytes(b'wrong checksum')
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    probe.copy_pinned_engine(source, target)
                self.assertFalse((scripts / 'bin/linux-x64/impeccable').exists())
                binary.write_bytes(body)
                binary.chmod(0o600)
                report = probe.copy_pinned_engine(source, target)
            copied = scripts / 'bin/linux-x64/impeccable'
            self.assertEqual(report['state'], 'copied_verified')
            self.assertEqual(copied.read_bytes(), body)
            self.assertEqual(copied.stat().st_mode & 0o777, 0o755)
            self.assertFalse((copied.parent / 'unrelated-profile').exists())

    def test_executor_boundary_retains_real_patch_usage_and_removes_snapshot(self):
        # This is a deterministic fake CLI boundary test, never live-pass evidence.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / 'source'
            project.mkdir()
            (project / 'facts.txt').write_text('original\n')
            toolkit = project / '.agent-toolkit'
            (toolkit / 'vendor/humanizer/skills').mkdir(parents=True)
            (toolkit / 'toolkit.lock.json').write_text(json.dumps({'skills': [{'name': 'humanizer', 'path': 'vendor/humanizer/skills'}]}))
            (toolkit / 'vendor/humanizer/skills/SKILL.md').write_text('Humanizer fixture\n')
            commit(project)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            executable = bin_dir / 'codex'
            executable.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv
workspace = pathlib.Path(args[args.index('-C') + 1])
assert sys.stdin.read() == 'Repository: shigol/career\\n\\nUse actual repository facts.\\n\\nLocal only: do not commit, push, open a PR, send or publish anything.\\n'
assert not (workspace / '.git/logs').exists()
(workspace / 'facts.txt').write_text('changed\\n')
(workspace / 'new.txt').write_text('added\\n')
pathlib.Path(args[args.index('-o') + 1]).write_text('92')
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 20, 'output_tokens': 2}}))
''')
            executable.chmod(0o755)
            with patch.dict(os.environ, {'PATH': str(bin_dir) + os.pathsep + os.environ['PATH']}):
                report = probe.execute(case('X32'), project, root / 'output', 'medium', 30)
            self.assertEqual(report['execution_state'], 'completed')
            self.assertEqual(report['usage']['total']['input_tokens'], 20)
            self.assertEqual(report['task_correctness']['state'], 'passed')
            patch_text = (root / 'output/changes.patch').read_text()
            self.assertIn('+changed', patch_text)
            self.assertIn('+added', patch_text)
            self.assertEqual((project / 'facts.txt').read_text(), 'original\n')
            self.assertFalse((root / 'output/project').exists())


if __name__ == '__main__':
    unittest.main()
