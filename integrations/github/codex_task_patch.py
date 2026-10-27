"""Save a bounded review patch without granting a model the repository write token."""
import json
from pathlib import Path
import subprocess
import sys


def allowed(name):
    path = Path(name)
    return (not path.is_absolute() and '..' not in path.parts
            and not any(part.startswith('.') or part in ('node_modules', '__pycache__', 'vendor') for part in path.parts)
            and path.suffix not in ('.pyc', '.enc', '.pem', '.key')
            and path.name.lower() not in ('auth.json', 'credentials.json')
            and (len(path.parts) == 1 or path.parts[0] in
                 ('src', 'public', 'scripts', 'tools', 'tests', 'docs', 'codex', 'catalogue')))


def save(output):
    output.mkdir(parents=True, exist_ok=True)
    # Tracked edits and untracked source files; never stage submodules or generated hidden directories.
    names = set()
    for args in (['diff', '--name-only', '-z', 'HEAD'], ['ls-files', '--others', '--exclude-standard', '-z']):
        names.update(p for p in subprocess.check_output(['git', *args]).decode().split('\0') if p)
    selected, held = [], []
    for name in sorted(names):
        path = Path(name)
        if allowed(name) and not path.is_symlink() and (not path.exists() or path.is_file()):
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
        'meaning': 'Review transport only. Tests and skill claims must be checked in the trace; held paths are not pushed.'}, indent=2) + '\n')


def apply(patch):
    if patch.stat().st_size > 5_000_000:
        raise ValueError('Review patch exceeds 5 MB')
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'apply', '--check', str(patch)], check=True)
    subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'apply', '--index', str(patch)], check=True)
    changed = [p for p in subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z']).decode().split('\0') if p]
    if any(not allowed(name) for name in changed):
        raise ValueError('Patch includes a held path; it will not be pushed')
    staged = subprocess.check_output(['git', 'ls-files', '--stage', '-z', '--', *changed]).decode().split('\0') if changed else []
    if any(row and row.split(' ', 1)[0] not in ('100644', '100755') for row in staged):
        raise ValueError('Symlink and submodule changes require direct review')


if __name__ == '__main__':
    if sys.argv[1] == 'apply':
        apply(Path(sys.argv[2]))
    else:
        save(Path(sys.argv[1]))
