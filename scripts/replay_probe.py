"""Run only the five held-out smoke cases in isolated, real-repository snapshots.

Keep case labels outside the executor prompt and snapshot. Run this trusted harness
outside the model sandbox, with the current repository's existing Codex login.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

from audit_skill_reads import audit

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ('X01', 'X07', 'X12', 'X17', 'X32')
REPOSITORIES = ('shigol/career', 'shigol/eugene-s-job-hub')
LOCAL_ONLY = 'Local only: do not commit, push, open a PR, send or publish anything.'
MAX_ARTIFACT = 16 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 1024 * 1024 * 1024
MAX_SNAPSHOT_FILES = 200000
MAX_SNAPSHOT_SECONDS = 180
GRADING_KEYS = ('must_read', 'acceptable_additional_shared_reads',
                'forbidden_if_unrequested', 'maximum_unrelated_shared_bodies')


class SnapshotError(ValueError):
    def __init__(self, message, stats):
        super().__init__(message)
        self.stats = stats


def git(project, *args):
    return subprocess.check_output(['git', '-C', str(project), *args])


def select_cases(document, repository):
    if repository not in REPOSITORIES:
        raise ValueError('Replay smoke requires a supported actual repository')
    cases = document.get('cases', [])
    ids = [case.get('id') for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate replay case IDs')
    selected = [case for case in cases if case.get('id') in SMOKE
                and case.get('repository') == repository]
    expected = {'X01', 'X07', 'X32'} if repository == REPOSITORIES[0] else {'X12', 'X17'}
    if {case['id'] for case in selected} != expected:
        raise ValueError('Missing recommended smoke cases for this repository')
    for case in selected:
        if not isinstance(case.get('brief'), str) or not case['brief'].strip():
            raise ValueError('Missing replay brief')
        if not isinstance(case.get('must_read'), dict) or any(
                mode not in ('full', 'patterns-or-full') for mode in case['must_read'].values()):
            raise ValueError('Invalid replay read requirements')
        for key in ('acceptable_additional_shared_reads', 'forbidden_if_unrequested'):
            if not isinstance(case.get(key), list) or not all(isinstance(x, str) for x in case[key]):
                raise ValueError('Invalid replay read labels')
        if case.get('maximum_unrelated_shared_bodies') != 0:
            raise ValueError('Smoke requires zero unrelated shared bodies')
    return sorted(selected, key=lambda case: SMOKE.index(case['id']))


def prompt(case):
    # Deliberately no ID, source path, expected skills, grading or extra hints.
    return f"Repository: {case['repository']}\n\n{case['brief']}\n\n{LOCAL_ONLY}\n"


def excluded(path):
    parts = Path(path).parts
    name = Path(path).name
    return ('.git' in parts or any(part in ('.aws', '.codex') for part in parts)
            or name == '.env' or name.startswith('.env.')
            or name in ('auth.json', 'credentials', 'credentials.json', '.npmrc', '.pypirc', 'id_rsa', 'id_ed25519')
            or bool(re.search(r'(?:replay|held[-_]?out)', name, re.I)))


def snapshot(source, destination, prefix='', hidden_paths=(), stats=None, deadline=None):
    """Copy committed files, never history, untracked runtime files or replay labels."""
    started = time.monotonic()
    stats = stats if stats is not None else {'files': 0, 'bytes': 0}
    deadline = deadline if deadline is not None else started + MAX_SNAPSHOT_SECONDS
    destination.mkdir(parents=True, exist_ok=True)
    records = git(source, 'ls-tree', '-rz', 'HEAD').split(b'\0')
    batch = subprocess.Popen(['git', '-C', str(source), 'cat-file', '--batch'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        for record in records:
            if time.monotonic() > deadline:
                raise ValueError('Snapshot exceeded 180-second limit; no task facts pruned')
            if not record:
                continue
            header, raw_path = record.split(b'\t', 1)
            mode, kind, object_id = header.decode().split()
            path = os.fsdecode(raw_path)
            if excluded(prefix + path) or prefix + path in hidden_paths:
                continue
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if kind == 'commit':
                submodule = source / path
                if not (submodule / '.git').exists() or git(submodule, 'rev-parse', 'HEAD').decode().strip() != object_id:
                    raise ValueError(f'Initialize the exact pinned submodule: {prefix + path}')
                snapshot(submodule, target, prefix + path + '/', hidden_paths, stats, deadline)
            elif kind == 'blob':
                batch.stdin.write((object_id + '\n').encode())
                batch.stdin.flush()
                response = batch.stdout.readline().split()
                if len(response) != 3 or response[1] != b'blob':
                    raise ValueError('Invalid committed blob response')
                size = int(response[2])
                stats['files'] += 1
                stats['bytes'] += size
                if stats['files'] > MAX_SNAPSHOT_FILES or stats['bytes'] > MAX_SNAPSHOT_BYTES:
                    raise ValueError('Snapshot exceeded 200000-file/1-GiB limit; no task facts pruned')
                body = batch.stdout.read(size)
                if len(body) != size or batch.stdout.read(1) != b'\n':
                    raise ValueError('Incomplete committed blob response')
                if mode == '120000':
                    link = os.fsdecode(body)
                    resolved = (target.parent / link).resolve()
                    if Path(link).is_absolute() or not resolved.is_relative_to(destination.resolve()):
                        raise ValueError(f'Snapshot symlink escapes repository: {prefix + path}')
                    target.symlink_to(link)
                else:
                    target.write_bytes(body)
                    target.chmod(0o755 if mode == '100755' else 0o644)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SnapshotError(str(error), stats) from error
    finally:
        batch.stdin.close()
        if batch.poll() is None:
            batch.terminate()
        batch.wait(timeout=5)
        batch.stdout.close()
        stats['elapsed_seconds'] = round(time.monotonic() - started, 2)
    return stats


def grade(case, events, answer, toolkit):
    report = audit(events, answer, toolkit, short_prose=True)
    reads = report['reads']
    observed = {name for name, read in reads.items() if read['state'] != 'unread'}
    required = case['must_read']
    missing = sorted(name for name, mode in required.items()
                     if reads.get(name, {}).get('state') not in
                     (('full',) if mode == 'full' else ('full', 'short_prose_patterns')))
    allowed = set(required) | set(case['acceptable_additional_shared_reads'])
    forbidden = sorted(observed & set(case['forbidden_if_unrequested']))
    manual = []
    for name in observed:
        guide = toolkit / 'catalog' / (name + '.md')
        if guide.exists() and re.search(r'\*\*Invocation:\*\* explicit-(?:only|direction)', guide.read_text()):
            if name not in required and name not in case['brief']:
                manual.append(name)
    unrelated = sorted(observed - allowed)
    source_passed = not (missing or forbidden or manual or unrelated)
    return {
        'reads': reads, 'missing_required_reads': missing,
        'forbidden_reads': forbidden, 'manual_unrequested_reads': sorted(manual),
        'unrelated_reads': unrelated, 'unrelated_body_count': len(unrelated),
        'source_selection_passed': source_passed,
        'declared_read_audit': {key: value for key, value in report.items() if key != 'reads'},
        'task_correctness': ({'state': 'passed' if answer.strip() == '92' else 'failed',
                              'method': 'Exact numeric answer'} if case['id'] == 'X32' else
                             {'state': 'pending_review', 'method': 'Review answer, trace and patch independently; missing-fixture honesty does not prove invocation'}),
        'render_validation': {'state': 'not_performed',
                              'reason': 'Trusted runner validation required for UI; no render claim inferred from answer'},
    }


def read_events(path):
    events, invalid = [], False
    for line in path.read_text(errors='replace').splitlines():
        if line.strip():
            try:
                events.append(json.loads(line))
            except ValueError:
                invalid = True
    return events, invalid


def measured_usage(events):
    usage = [row.get('usage') for row in events if row.get('type') == 'turn.completed']
    if not usage or any(not isinstance(row, dict) for row in usage):
        return {'state': 'unavailable', 'turns': usage}
    keys = set().union(*(row.keys() for row in usage))
    return {'state': 'measured', 'turns': usage,
            'total': {key: sum(row.get(key, 0) for row in usage) for key in keys
                      if all(isinstance(row.get(key, 0), (int, float)) for row in usage)}}


def label_leaks(events, label_paths=()):
    """Conservative trace audit, not a claim of filesystem read isolation."""
    markers = set(GRADING_KEYS) | {'codex-replay-v1.json'}
    for path in label_paths:
        markers.update((str(path), Path(path).name))
    seen = set()
    for row in events:
        item = row.get('item', {})
        if row.get('type') != 'item.completed':
            continue
        if item.get('type') == 'command_execution' and item.get('exit_code') == 0:
            output = item.get('command', '') + '\n' + item.get('aggregated_output', '')
        elif item.get('type') == 'mcp_tool_call' and item.get('status') == 'completed' and not item.get('error'):
            output = json.dumps(item.get('result', {}))
        else:
            continue
        seen.update(marker for marker in markers if marker and marker in output)
    return {'state': 'leaked' if seen else 'no_observed_leak', 'markers': sorted(seen),
            'scope': 'Successful recorded tool outputs only; no hard host read isolation claim'}


def link_dependencies(project, workspace):
    """Opt-in runner dependencies only; common writable build caches stay local."""
    source = project / 'node_modules'
    if not source.is_dir() or source.is_symlink():
        raise ValueError('--node-modules needs a real runner-installed node_modules directory')
    target = workspace / 'node_modules'
    target.mkdir(exist_ok=True)
    for entry in source.iterdir():
        if entry.name in ('.cache', '.vite', '.vite-temp'):
            continue
        (target / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())


def execute(case, project, folder, effort, timeout, hidden_paths=(), node_modules=False, label_paths=()):
    folder.mkdir()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='codex-replay-') as temporary:
        workspace = Path(temporary) / 'project'
        snapshot_stats = snapshot(project, workspace, hidden_paths=hidden_paths)
        toolkit = workspace / '.agent-toolkit'
        if not (toolkit / 'toolkit.lock.json').is_file():
            raise ValueError('Actual repository needs its initialized pinned toolkit')
        git(workspace, 'init', '--quiet')
        (workspace / '.git/info/exclude').write_text('/node_modules/\n')
        git(workspace, 'add', '--force', '--all')
        baseline = git(workspace, 'write-tree').decode().strip()
        if node_modules:
            link_dependencies(project, workspace)
        command = ['codex', 'exec', '--ephemeral', '--json', '--skip-git-repo-check',
                   '-s', 'workspace-write', '-C', str(workspace), '-c',
                   f'model_reasoning_effort={effort}', '-o', str(folder / 'answer.md'), '-']
        timed_out = False
        with (folder / 'trace.jsonl').open('w') as trace, (folder / 'stderr.txt').open('w') as errors:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=trace, stderr=errors,
                                       text=True, start_new_session=True)
            try:
                process.communicate(prompt(case), timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
        git(workspace, 'add', '-N', '--all')
        patch = git(workspace, 'diff', '--binary', baseline)
        if len(patch) <= MAX_ARTIFACT:
            (folder / 'changes.patch').write_bytes(patch)
        oversized = False
        for artifact in ('trace.jsonl', 'stderr.txt', 'answer.md'):
            path = folder / artifact
            if path.is_file() and path.stat().st_size > MAX_ARTIFACT:
                oversized = True
                with path.open('r+b') as stream:
                    stream.truncate(MAX_ARTIFACT)
        events, invalid = read_events(folder / 'trace.jsonl')
        invalid |= oversized
        answer_path = folder / 'answer.md'
        answer = answer_path.read_text(errors='replace') if answer_path.is_file() else ''
        result = grade(case, events, answer, toolkit)
        leakage = label_leaks(events, label_paths)
        invalid |= leakage['state'] == 'leaked'
        result['label_audit'] = leakage
        result['source_selection_passed'] &= not (invalid or timed_out or process.returncode != 0)
        result.update({'exit_code': process.returncode, 'elapsed_seconds': round(time.monotonic() - started, 2),
                       'execution_state': 'time_limit' if timed_out else 'invalid_evidence' if invalid else
                                          'completed' if process.returncode == 0 else 'execution_failed',
                       'patch_state': 'retained' if len(patch) <= MAX_ARTIFACT else 'exceeded_artifact_limit',
                       'usage': measured_usage(events),
                       'snapshot': snapshot_stats,
                       'runtime_scope': 'Committed files only; ignored engines, browsers and profiles are not copied',
                       'dependencies': 'Explicit existing runner node_modules links; common build caches local' if node_modules else 'Not shared; locked dependency install required separately',
                       'pinned_engine': 'Not copied from ignored files; runtime availability must be checked, never inferred'})
        result['stop_for_auth_or_limit'] = bool(re.search(
            r'unauthorized|usage limit|limit reached|refresh_token_reused',
            '\n'.join(str(row.get('message', row.get('error', ''))) for row in events)
            + (folder / 'stderr.txt').read_text(errors='replace'), re.I))
        # Labels are returned to the trusted caller; no reports are written until
        # all paid calls finish, so later executors cannot discover earlier labels.
        return result


def run(cases_path, repository, project, output, effort='medium', timeout=600, node_modules=False):
    document = json.loads(cases_path.read_text())
    cases = select_cases(document, repository)
    # Match the requested actual origin without changing authentication or refs.
    origin = git(project, 'remote', 'get-url', 'origin').decode().strip()
    if not re.search(r'github\.com[:/]' + re.escape(repository) + r'(?:\.git)?$', origin):
        raise ValueError('Project origin does not match requested replay repository')
    output.mkdir(parents=True, exist_ok=False)
    hidden_paths = (str(cases_path.relative_to(project)),) if cases_path.is_relative_to(project) else ()
    reports = {}
    for case in cases:
        try:
            reports[case['id']] = execute(case, project, output / case['id'], effort, timeout, hidden_paths, node_modules, (cases_path,))
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            (output / case['id']).mkdir(exist_ok=True)
            reports[case['id']] = {'execution_state': 'harness_failed', 'error': str(error),
                                   'snapshot': getattr(error, 'stats', None),
                                   'usage': {'state': 'unavailable'},
                                   'task_correctness': {'state': 'not_graded'},
                                   'source_selection_passed': False}
            break
        if reports[case['id']]['stop_for_auth_or_limit']:
            break
    for case_id, report in reports.items():
        (output / case_id / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    summary = {'scope': 'Recommended five-case smoke only; no automatic expansion or overall task pass',
               'repository': repository, 'project_commit': git(project, 'rev-parse', 'HEAD').decode().strip(),
               'toolkit_commit': git(project / '.agent-toolkit', 'rev-parse', 'HEAD').decode().strip(),
               'case_file_sha256': hashlib.sha256(cases_path.read_bytes()).hexdigest(),
               'codex_version': subprocess.check_output(['codex', '--version'], text=True).strip(),
               'model': 'CLI default; exact provider model not reported', 'effort': effort,
               'cases': reports, 'not_run': [case['id'] for case in cases if case['id'] not in reports]}
    (output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: value for key, value in summary.items() if key != 'cases'}))
    return 0 if len(reports) == len(cases) and all(
        row['execution_state'] == 'completed' for row in reports.values()) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--repository', choices=REPOSITORIES, required=True)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--effort', choices=['low', 'medium', 'high'], default='medium')
    parser.add_argument('--timeout', type=int, choices=range(30, 901), default=600, metavar='30..900')
    parser.add_argument('--node-modules', action='store_true', help='Use this runner checkout\'s already-installed locked dependencies; never installs them')
    args = parser.parse_args()
    raise SystemExit(run(args.cases.resolve(), args.repository, args.project.resolve(),
                         args.output.resolve(), args.effort, args.timeout, args.node_modules))
