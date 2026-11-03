"""Save a bounded review patch without granting a model the repository write token."""
import json
import os
import re
import tempfile
from pathlib import Path
import subprocess
import sys


ROOTS = ('src', 'public', 'scripts', 'tools', 'tests', 'docs', 'codex', 'catalogue')
NAME = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9._-]*(/[A-Za-z0-9_-][A-Za-z0-9._-]*)*')


def review_paths(config='.agent-toolkit.json'):
    """Project-declared extra source roots and held subtrees (for example a data store the agent must not write)."""
    path = Path(config)
    if not os.path.lexists(path):
        return ROOTS, ()
    if path.is_symlink() or not path.is_file():
        raise ValueError('Project review settings must be a regular file')
    review = json.loads(path.read_text()).get('review', {})
    if not isinstance(review, dict) or set(review) - {'roots', 'held'}:
        raise ValueError('Invalid project review settings')
    roots, held = review.get('roots', []), review.get('held', [])
    for values in (roots, held):
        if not isinstance(values, list) or not all(isinstance(v, str) and NAME.fullmatch(v) for v in values):
            raise ValueError('Review roots/held must be plain relative paths')
    if any('/' in root for root in roots):
        raise ValueError('Review roots are top-level directories')
    return ROOTS + tuple(roots), tuple(held)


def allowed(name, paths=None):
    roots, held = paths or review_paths()
    path = Path(name)
    return (not path.is_absolute() and '..' not in path.parts
            and not any(part.startswith('.') or part in ('node_modules', '__pycache__', 'vendor') for part in path.parts)
            and path.suffix not in ('.pyc', '.enc', '.pem', '.key')
            and path.name.lower() not in ('auth.json', 'credentials.json')
            and (len(path.parts) == 1 or path.parts[0] in roots)
            and not any(name == h or name.startswith(h + '/') for h in held))


def quiet(name):
    """Held for hygiene (hidden, cache or generated files) rather than for being outside the review roots."""
    path = Path(name)
    return any(part.startswith('.') or part in ('node_modules', '__pycache__', 'vendor') for part in path.parts) or path.suffix == '.pyc'


def save(output):
    output.mkdir(parents=True, exist_ok=True)
    # Tracked edits and untracked source files; never stage submodules or generated hidden directories.
    names = set()
    for args in (['diff', '--name-only', '-z', 'HEAD'], ['ls-files', '--others', '--exclude-standard', '-z']):
        names.update(p for p in subprocess.check_output(['git', *args]).decode().split('\0') if p)
    paths = review_paths()
    selected, held = [], []
    for name in sorted(names):
        path = Path(name)
        if allowed(name, paths) and not path.is_symlink() and (not path.exists() or path.is_file()):
            selected.append(name)
        else:
            held.append(name)
    if selected:
        subprocess.run(['git', 'add', '--', *selected], check=True)
        patch = subprocess.check_output(['git', 'diff', '--cached', '--binary', '--', *selected])
        if len(patch) > 5_000_000:
            raise ValueError('Review patch exceeds 5 MB')
        (output / 'changes.patch').write_bytes(patch)
    (output / 'patch-report.json').write_text(json.dumps({'saved': selected, 'held': held,
        'blocked': [name for name in held if not quiet(name)],
        'meaning': 'Review transport only. Tests and skill claims must be checked in the trace; held paths are not pushed. '
                   'Blocked paths are source changes outside the review roots: the result is incomplete.'}, indent=2) + '\n')


def snapshot(output):
    """Read-only partial checkpoint: never stage files while the model is working."""
    output.mkdir(parents=True, exist_ok=True)
    tracked = {p for p in subprocess.check_output(['git', 'diff', '--name-only', '-z', 'HEAD']).decode().split('\0') if p}
    untracked = {p for p in subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z']).decode().split('\0') if p}
    paths = review_paths()
    selected, held = [], []
    for name in sorted(tracked | untracked):
        candidate = Path(name)
        (selected if allowed(name, paths) and not candidate.is_symlink() and
         (not candidate.exists() or candidate.is_file()) else held).append(name)
    pieces = []
    old = [name for name in selected if name in tracked]
    if old:
        pieces.append(subprocess.check_output(['git', 'diff', '--binary', 'HEAD', '--', *old]))
    for name in selected:
        if name not in untracked:
            continue
        result = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', name], capture_output=True)
        if result.returncode not in (0, 1):
            raise ValueError('Could not capture an untracked checkpoint file')
        pieces.append(result.stdout)
    patch = b''.join(pieces)
    if len(patch) > 5_000_000:
        raise ValueError('Review checkpoint exceeds5MB')
    temporary = output / 'partial.patch.tmp'
    temporary.write_bytes(patch)
    temporary.replace(output / 'partial.patch')
    (output / 'partial-report.json').write_text(json.dumps({'saved': selected, 'held': held,
        'meaning': 'Partial read-only checkpoint; not an accepted result or automatic merge.'}) + '\n')


def git(*arguments, env=None, check=True):
    # Applies to every transport operation, including push. Candidate hooks never run.
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *arguments],
                          env=env, check=check, capture_output=True, timeout=120)


def validated_tree(patch):
    """Check the patch on a disposable index and return its tree; the real index and working tree are untouched."""
    if patch.is_symlink() or not patch.is_file() or patch.stat().st_size > 5_000_000:
        raise ValueError('Review patch must be a regular file under 5 MB')
    if git('diff', '--quiet', check=False).returncode or git('diff', '--cached', '--quiet', check=False).returncode:
        raise ValueError('Trusted transport checkout must be clean')
    # Validate a disposable index first. Rejected input cannot replace the trusted
    # helper used by the following always() status step, even transiently.
    with tempfile.TemporaryDirectory(prefix='codex-patch-index-') as directory:
        environment = {**os.environ, 'GIT_INDEX_FILE': str(Path(directory) / 'index')}
        git('read-tree', 'HEAD', env=environment)
        git('apply', '--cached', str(patch.resolve()), env=environment)
        changed = [p for p in git('diff', '--cached', '--name-only', '-z', 'HEAD', env=environment).stdout.decode().split('\0') if p]
        paths = review_paths()
        if not changed or any(not allowed(name, paths) for name in changed):
            raise ValueError('Patch includes a held path or no changes; it will not be pushed')
        staged = git('ls-files', '--stage', '-z', '--', *changed, env=environment).stdout.decode().split('\0')
        if any(row and row.split(' ', 1)[0] not in ('100644', '100755') for row in staged):
            raise ValueError('Symlink and submodule changes require direct review')
        # --missing-ok: the base tree's blobs exist upstream; checking them would lazily fetch a partial clone's
        # unrelated data (the new blobs were just written by git apply)
        return git('write-tree', '--missing-ok', env=environment).stdout.strip().decode()


def apply(patch):
    """Apply a validated patch to a full checkout's index and working tree."""
    validated_tree(patch)
    git('apply', '--check', str(patch.resolve()))
    git('apply', '--index', str(patch.resolve()))


def save_branch(patch, branch, run_id):
    """Idempotent result transport only: no model, candidate execution or forced push."""
    if not re.fullmatch(r'[1-9][0-9]{0,19}', str(run_id)) or branch != 'codex/task-' + str(run_id):
        raise ValueError('Invalid result branch/run')
    if not patch.exists():
        return ''
    # The commit is built from the validated tree alone: a sparse receiver checks out nothing more and fetches no
    # unrelated blob. Widening the sparse checkout to the touched directories timed out at 120 s on a project with a
    # large data tree (career run 41590842381, 11-03).
    tree = validated_tree(patch)
    reference = 'refs/heads/' + branch

    def existing():
        found = git('ls-remote', '--exit-code', '--heads', 'origin', reference, check=False)
        if found.returncode == 2:
            return False
        found.check_returncode()
        git('fetch', '--depth=1', 'origin', reference)
        if git('rev-parse', 'FETCH_HEAD^{tree}').stdout.strip().decode() != tree:
            raise ValueError('Existing review branch differs; independent recovery review required')
        return True

    if existing():
        return branch
    identity = {**os.environ, 'GIT_AUTHOR_NAME': 'github-actions[bot]', 'GIT_COMMITTER_NAME': 'github-actions[bot]',
                'GIT_AUTHOR_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com',
                'GIT_COMMITTER_EMAIL': '41898282+github-actions[bot]@users.noreply.github.com'}
    commit = git('commit-tree', tree, '-p', 'HEAD', '-m', f'Codex: save committed-brief result for review (run {run_id})', '-m',
                 "Skills: none (transport only; source claims remain in the worker answer and trace)", env=identity).stdout.strip().decode()
    # A past shallow source revision may no longer be an advertised remote tip.
    # Negotiate its known base before packing, avoiding lazy fetch of unrelated promisor blobs.
    pushed = git('-c', 'push.negotiate=true', 'push', 'origin', commit + ':' + reference, check=False)
    if pushed.returncode and not existing():
        pushed.check_returncode()
    return branch


def blocked(report):
    """Exit status for the result step: a dropped source change must never read as a saved result."""
    names = json.loads(report.read_text()).get('blocked', []) if report.is_file() and not report.is_symlink() else []
    if names:
        print(f'::error::{len(names)} changed file(s) are outside the review roots and were NOT saved: '
              + ', '.join(names[:20]), file=sys.stderr)
    return 3 if names else 0


if __name__ == '__main__':
    if sys.argv[1] == 'transport':
        print('branch=' + save_branch(Path(sys.argv[2]), sys.argv[3], sys.argv[4]))
        sys.exit(blocked(Path(sys.argv[2]).parent / 'patch-report.json'))
    elif sys.argv[1] == 'blocked':
        sys.exit(blocked(Path(sys.argv[2])))
    elif sys.argv[1] == 'apply':
        apply(Path(sys.argv[2]))
    elif sys.argv[1] == 'snapshot':
        snapshot(Path(sys.argv[2]))
    else:
        save(Path(sys.argv[1]))
