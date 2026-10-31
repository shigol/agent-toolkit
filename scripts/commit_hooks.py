"""Install the shared commit audit, preserving project hook ownership."""
import os
from pathlib import Path
import subprocess

HOOK = '''#!/bin/sh
# agent-toolkit skills audit (implementation stays in the pinned submodule)
project_root="$(git rev-parse --show-toplevel)" || exit 1
git interpret-trailers --in-place --if-exists doNothing --trailer "Hooks: on" "$1" || exit 1
exec python3 "$project_root/.agent-toolkit/scripts/skills_audit.py" stamp "$1"
'''


def plan(project):
    project = Path(project)
    result = subprocess.run(['git', '-C', str(project), 'rev-parse', '--show-toplevel'],
                            capture_output=True, text=True)
    if result.returncode or Path(result.stdout.strip()).resolve() != project.resolve():
        return None  # Source-link-only installations outside Git have no commit hook.
    configured = subprocess.run(['git', '-C', str(project), 'config', '--get', 'core.hooksPath'],
                                capture_output=True, text=True).stdout.strip()
    if configured not in ('', '.githooks'):
        raise RuntimeError('Existing core.hooksPath differs; integrate the shared audit deliberately: ' + configured)
    directory = project / '.githooks'
    hook = directory / 'commit-msg'
    if directory.is_symlink() or hook.is_symlink():
        raise RuntimeError('Refusing redirected commit hook')
    if directory.exists() and not directory.is_dir():
        raise RuntimeError('Expected a commit hook directory')
    if hook.exists() and not hook.is_file():
        raise RuntimeError('Expected a regular commit hook')
    if hook.exists() and hook.read_text() != HOOK:
        # Career's existing hook already invokes the compatibility entry point.
        legacy = 'exec python3 "$(git rev-parse --show-toplevel)/tools/skills_audit.py" stamp "$1"'
        shim = project / 'tools/skills_audit.py'
        if legacy not in hook.read_text() or not shim.is_file() or 'runpy.run_path(_SHARED' not in shim.read_text():
            raise RuntimeError('Existing commit-msg differs; preserve it and integrate the shared audit deliberately')
    if not configured:
        gitdir = subprocess.check_output(['git', '-C', str(project), 'rev-parse', '--absolute-git-dir'], text=True).strip()
        if any(p.is_file() and os.access(p, os.X_OK) and not p.name.endswith('.sample')
               for p in (Path(gitdir) / 'hooks').glob('*')):
            raise RuntimeError('Existing default Git hooks; merge deliberately before changing core.hooksPath')
    return hook


def install(project, hook):
    if hook is None:
        return
    hook.parent.mkdir(parents=True, exist_ok=True)
    if not hook.exists():
        hook.write_text(HOOK)
    hook.chmod(hook.stat().st_mode | 0o111)
    subprocess.run(['git', '-C', str(project), 'config', '--local', 'core.hooksPath', '.githooks'], check=True)


def verify(project):
    hook = plan(project)
    if hook is None:
        return
    configured = subprocess.run(['git', '-C', str(project), 'config', '--get', 'core.hooksPath'],
                                capture_output=True, text=True).stdout.strip()
    if not hook.is_file() or not os.access(hook, os.X_OK) or configured != '.githooks':
        raise RuntimeError('Shared commit audit not active; rerun consumer setup')
