"""Initialize pinned shared skills without overwriting project-owned configuration."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

from routes import block
from skills import catalogue

PUBLIC_SOURCE = 'https://github.com/shigol/agent-toolkit.git'
NATIVE_START = '<!-- toolkit-native:start -->'
NATIVE_END = '<!-- toolkit-native:end -->'
GLOBAL_START = '<!-- toolkit-global:start -->'
GLOBAL_END = '<!-- toolkit-global:end -->'


def git(root, *args, check=True):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    if check:
        result.check_returncode()
    return result.stdout.strip()


def marked(text, generated, start, end):
    if text.count(start) != text.count(end) or text.count(start) > 1:
        raise ValueError('Repeated or incomplete toolkit instruction markers')
    if start in text:
        first, last = text.index(start), text.index(end)
        if last < first:
            raise ValueError('Reversed toolkit instruction markers')
        last += len(end)
        if text[last:last + 1] == '\n':
            last += 1
        text = text[:first] + text[last:]
    return generated + text


def native_block():
    return (NATIVE_START + '\n'
            'Codex skills: choose from native descriptions and read selected SKILL.md files in full. '
            'If native coverage is missing or incomplete, follow .agent-toolkit/SELECTION.md, '
            'then the catalogue index; search last. Missing files: bash tools/setup-agent-toolkit.sh --skills-only.\n'
            'Use one primary UI workflow: impeccable by default; design-taste-frontend only for an explicit alternative direction. '
            'Use humanizer for prose, including replies reporting code work (whole source for documents/outside messages; pattern text for short replies/PR bodies) '
            'and verification-before-completion for technical completion claims. '
            'This Codex selection rule takes precedence over Claude-specific routing in CLAUDE.md; its other project rules still apply. '
            'Project rules and factual/template constraints win. Each commit/PR names only skills actually read: '
            'Skills: <names>, or Skills: none (<why>).\n'
            'Unfinished work at turn end needs a verified cloud run and saved checkpoint, or an explicit paused status. '
            'No idle-chat background promises; see .agent-toolkit/CONTINUITY.md.\n' + NATIVE_END + '\n')


def regular(project, path):
    for item in (path, *path.parents):
        if item == project:
            break
        if item.is_symlink():
            raise ValueError('Refusing redirected project path: ' + str(item))
    if path.exists() and not path.is_file():
        raise ValueError('Expected a regular configuration file: ' + str(path))


def init_project(project, root, source=PUBLIC_SOURCE):
    project, root = project.resolve(), root.resolve()
    if Path(git(project, 'rev-parse', '--show-toplevel')).resolve() != project:
        raise ValueError('init-project requires an existing Git repository root')
    if git(root, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Use a committed toolkit checkout for reproducible initialization')
    revision = git(root, 'rev-parse', 'HEAD')
    entries = catalogue(root)
    manifest = json.loads((root / 'toolkit.lock.json').read_text())
    templates = root / 'integrations/github'
    files = {'.github/scripts/' + name: (templates / name).read_bytes() for name in
             ('toolkit_update.py', 'test_toolkit_update.py', 'merge_toolkit.cjs', 'merge_toolkit.test.cjs', 'codex_request.cjs',
              'codex_request.test.cjs', 'codex_task_patch.py', 'codex_task_run.py', 'codex_result.cjs',
              'codex_continuity.cjs', 'codex_continuity.test.cjs', 'codex_monitor.cjs', 'codex_monitor.test.cjs', 'codex_recover.cjs', 'claude_wake.cjs', 'claude_wake.test.cjs')}
    files.update({'.github/workflows/' + name: (templates / name).read_bytes() for name in
                  ('agent-toolkit-check.yml', 'agent-toolkit-merge.yml', 'codex-request.yml', 'codex-task.yml',
                   'codex-continuity.yml', 'codex-continuity-watchdog.yml', 'codex-monitor.yml', 'codex-recover.yml', 'claude-wake.yml')})
    files['.github/dependabot.yml'] = (templates / 'dependabot.yml').read_bytes()
    files['tools/setup-agent-toolkit.sh'] = (templates / 'setup-agent-toolkit.sh').read_bytes()
    for name in ('AGENTS.md', 'CLAUDE.md', '.agent-toolkit.json', '.gitmodules'):
        regular(project, project / name)
    config = project / '.agent-toolkit.json'
    if not config.exists():
        files[config.name] = (json.dumps({'schema': 1, 'groups': list(manifest['groups']), 'entry_cache': True}, indent=2) + '\n').encode()
    # Existing project selection is preserved, not broadened by initialization.
    import toolkit
    packages = {package for members in manifest['groups'].values() for package in members}
    selected = toolkit.selection(project, manifest) if config.exists() else [
        entry for entry in manifest['skills'] if entry['package'] in packages]
    from routes import replace_block
    original_native = (project / 'AGENTS.md').read_text() if (project / 'AGENTS.md').exists() else ''
    # Adopt the old toolkit-owned table without touching project instructions.
    original_native = replace_block(original_native, '')
    files['AGENTS.md'] = marked(original_native,
                               native_block(), NATIVE_START, NATIVE_END).encode()
    claude_text = (project / 'CLAUDE.md').read_text() if (project / 'CLAUDE.md').exists() else ''
    startup = 'Shared toolkit startup: bash tools/setup-agent-toolkit.sh --skills-only when source files are absent.\n'
    if startup not in claude_text:
        claude_text = startup + claude_text
    files['CLAUDE.md'] = replace_block(claude_text, block(root, selected)).encode()
    for name in [*files, '.gitmodules']:
        regular(project, project / name)
    for name, content in files.items():
        path = project / name
        if path.exists() and name not in ('AGENTS.md', 'CLAUDE.md') and path.read_bytes() != content:
            raise ValueError('Existing integration differs; merge it deliberately: ' + name)
    target = project / '.agent-toolkit'
    if target.is_symlink():
        raise ValueError('Refusing redirected toolkit directory')
    existing = target.exists()
    if existing and (git(target, 'rev-parse', 'HEAD') != revision
                     or git(target, 'status', '--porcelain', '--untracked-files=no')
                     or git(target, 'remote', 'get-url', 'origin').removesuffix('.git') != source.removesuffix('.git')):
        raise ValueError('Existing toolkit differs; use the reviewed update process')
    module_dir = Path(git(project, 'rev-parse', '--git-path', 'modules/agent-toolkit'))
    if not module_dir.is_absolute():
        module_dir = project / module_dir
    if not existing and (module_dir.exists() or git(project, 'config', '--name-only', '--get-regexp',
                                                    r'^submodule\.agent-toolkit\.', check=False)):
        raise ValueError('Existing submodule metadata; resume documented setup instead')
    snapshots = {name: ((project / name).read_bytes(), stat.S_IMODE((project / name).stat().st_mode))
                 if (project / name).exists() else None for name in [*files, '.gitmodules']}
    for agent in ('.agents', '.claude'):
        for folder in (project / agent, project / agent / 'skills'):
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                raise ValueError('Refusing redirected skill directory: ' + str(folder))
    # Pure ownership checks before cloning, creating headers, or staging integration.
    toolkit.preflight_install(project, ['codex', 'claude'], manifest, selected,
                              cached=toolkit.cache_enabled(project) if config.exists() else True, root=target if existing else root)
    parents = {parent for name in files for parent in (project / name).parents
               if parent != project and project in parent.parents}
    parents.update(project / agent / suffix for agent in ('.agents', '.claude') for suffix in ('', 'skills'))
    new_dirs = {path for path in parents if not path.exists()}
    index = git(project, 'ls-files', '--stage', '--', '.gitmodules', '.agent-toolkit')
    if any(line.split('\t', 1)[0].split()[-1] != '0' for line in index.splitlines()):
        raise ValueError('Resolve the existing submodule index conflict first')
    if not existing and (git(project, 'diff', '--name-only', '--', '.gitmodules', '.agent-toolkit')
                         or git(project, 'diff', '--cached', '--name-only', '--', '.gitmodules', '.agent-toolkit')):
        raise ValueError('Existing submodule configuration has uncommitted changes')
    old_links = {(agent, entry['name']) for agent in ('.agents', '.claude') for entry in entries
                 if os.path.lexists(project / agent / 'skills' / entry['name'])}
    cache_existed = (project / '.agent-skill-cache').exists()
    try:
        if not existing:
            options = []
            if source == str(root):  # Offline self-mirror validation only; not a CLI option.
                options = ['-c', 'protocol.file.allow=always']
            git(project, *options, 'submodule', 'add', '--name', 'agent-toolkit', '--', source, '.agent-toolkit')
            git(target, 'fetch', 'origin', revision)
            git(target, 'checkout', '--detach', revision)
            git(project, 'add', '--', '.gitmodules', '.agent-toolkit')
        for name, content in files.items():
            path = project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            if name.endswith('.sh') and snapshots[name] is None:
                path.chmod(0o755)
        subprocess.run([os.sys.executable, str(target / 'scripts/toolkit.py'), 'install',
                        '--project', str(project)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([os.sys.executable, str(target / 'scripts/toolkit.py'), 'emit-routes',
                        '--project', str(project), '--agents', 'claude', '--check'],
                       check=True, stdout=subprocess.DEVNULL)
    except BaseException:
        for name, snapshot in snapshots.items():
            path = project / name
            if snapshot is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(snapshot[0])
                path.chmod(snapshot[1])
        if not existing:
            for agent in ('.agents', '.claude'):
                for entry in entries:
                    link = project / agent / 'skills' / entry['name']
                    if (agent, entry['name']) not in old_links and link.is_symlink():
                        link.unlink()
            shutil.rmtree(target, ignore_errors=True)
            if not cache_existed:
                shutil.rmtree(project / '.agent-skill-cache', ignore_errors=True)
            shutil.rmtree(module_dir, ignore_errors=True)
            git(project, 'config', '--remove-section', 'submodule.agent-toolkit', check=False)
            git(project, 'update-index', '--force-remove', '--', '.gitmodules', '.agent-toolkit')
            for line in index.splitlines():
                metadata, name = line.split('\t', 1)
                mode, sha, stage = metadata.split()
                if stage != '0':
                    raise ValueError('Cannot restore an unmerged index')
                git(project, 'update-index', '--add', '--cacheinfo', f'{mode},{sha},{name}')
        for directory in sorted(new_dirs, key=lambda path: len(path.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    return {'state': 'initialized', 'project': str(project), 'toolkit_commit': revision,
            'skills': len(selected), 'agents': ['codex', 'claude'],
            'publication': 'not performed; review and commit the generated integration'}


def bootstrap_global(root, codex_home):
    root, codex_home = root.resolve(), codex_home.resolve()
    catalogue(root)
    codex_home.mkdir(parents=True, exist_ok=True)
    target = codex_home / 'AGENTS.md'
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError('Global AGENTS.md must be a regular file')
    generated = (GLOBAL_START + '\n'
                 'Shared skills: prefer the current project\'s pinned library and native skill descriptions. '
                 'Read each relevant SKILL.md before applying it. If native coverage is missing or incomplete, '
                 f'the fallback library is {root}. Open its SELECTION.md, catalogue index and chosen guide Source; '
                 'search last. This works even when the current repository has no .agent-toolkit. '
                 'Do not fetch a mutable latest revision or duplicate skill sources. Project rules win.\n'
                 'Use humanizer for prose including replies reporting code work, verification-before-completion before technical completion claims, '
                 'and only one primary design workflow (impeccable by default; Taste requires an explicit alternative). '
                 'Name only skills actually read in each commit/PR. Installation is not proof of runtime readiness.\n'
                 'Unfinished work at turn end needs a verified cloud run and saved checkpoint, or an explicit paused status. '
                 f'No idle-chat background promises; see {root}/CONTINUITY.md.\n'
                 + GLOBAL_END + '\n')
    original = target.read_text() if target.exists() else ''
    target.write_text(marked(original, generated, GLOBAL_START, GLOBAL_END))
    return {'state': 'configured', 'file': str(target), 'fallback_source': str(root),
            'credentials': 'not read or changed', 'native_discovery': 'not asserted'}
