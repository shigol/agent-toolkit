#!/usr/bin/env python3
"""Install and verify shared project skills. Python 3.9+, no third-party packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lock():
    return json.loads((ROOT / 'toolkit.lock.json').read_text())


def verify_sources():
    data = lock()
    for relative, expected in data['files'].items():
        path = ROOT / relative
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f'Vendored file missing or changed: {relative}')
    names = [s['name'] for s in data['skills']]
    if len(names) != len(set(names)):
        raise RuntimeError('Duplicate skill names in manifest')
    packages = {p['name'] for p in data['packages']}
    for skill in data['skills']:
        source = ROOT / skill['path']
        if (not re.fullmatch(r'[a-z0-9][a-z0-9-]*', skill['name'])
                or not skill['path'].startswith('vendor/')
                or ROOT.resolve() not in source.resolve().parents
                or skill['package'] not in packages
                or skill['path'] + '/SKILL.md' not in data['files']):
            raise RuntimeError('Invalid registered skill: ' + skill['name'])
    for group, members in data.get('groups', {}).items():
        if not re.fullmatch(r'[a-z0-9-]+', group) or not isinstance(members, list) or not set(members) <= packages:
            raise RuntimeError('Invalid skill group: ' + group)
    return data


def selection(project, data):
    """Project selection is shared by both agents; no file preserves legacy all-skills behavior."""
    config = project / '.agent-toolkit.json'
    if not os.path.lexists(config):
        return data['skills']
    if config.is_symlink():
        raise RuntimeError('Project selection must be a regular file')
    settings = json.loads(config.read_text())
    if not isinstance(settings, dict) or settings.get('schema') != 1 or set(settings) - {'schema', 'groups', 'include', 'exclude', 'native_limit', 'entry_cache'}:
        raise RuntimeError('Invalid project selection format')
    if 'entry_cache' in settings and type(settings['entry_cache']) is not bool:
        raise RuntimeError('entry_cache must be boolean')
    groups = settings.get('groups')
    include, exclude = settings.get('include', []), settings.get('exclude', [])
    for values in (groups, include, exclude):
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise RuntimeError('Selection groups/include/exclude must be string lists')
    available = {s['name'] for s in data['skills']}
    if set(groups) - set(data.get('groups', {})) or (set(include) | set(exclude)) - available:
        raise RuntimeError('Unknown group or skill in project selection')
    packages = {p for g in groups for p in data['groups'][g]}
    selected = [s for s in data['skills'] if (s['package'] in packages or s['name'] in include) and s['name'] not in exclude]
    limit = settings.get('native_limit')
    if 'native_limit' not in settings:
        return selected
    if type(limit) is not int or limit < 1:
        raise RuntimeError('native_limit must be a positive integer')
    forced = [s for s in selected if s['name'] in include]
    if len(forced) > limit:
        raise RuntimeError('Explicit includes exceed native_limit; adjust the project selection')
    remaining = [s for s in selected if s['name'] not in include]
    chosen = {s['name'] for s in forced + remaining[:limit - len(forced)]}
    return [s for s in selected if s['name'] in chosen]


def cache_enabled(project):
    path = project / '.agent-toolkit.json'
    return path.exists() and json.loads(path.read_text()).get('entry_cache', False)


def destinations(project, agents, data, cached=None):
    if cached is None:
        cached = cache_enabled(project)
    for agent in agents:
        folder = '.agents' if agent == 'codex' else '.claude'
        parent = project / folder / 'skills'
        for ancestor in (project / folder, parent):
            if ancestor.is_symlink():
                raise RuntimeError(f'Refusing redirected installation directory: {ancestor}')
            if ancestor.exists() and not ancestor.is_dir():
                raise RuntimeError(f'Installation directory is a file: {ancestor}')
        for skill in data['skills']:
            yield parent / skill['name'], (project / '.agent-skill-cache' / skill['path'] if cached else ROOT / skill['path'])


def preflight_install(project, agents, data, selected, cached=None, root=None):
    import entry_cache
    root = ROOT if root is None else root
    cached = cache_enabled(project) if cached is None else cached
    plan = entry_cache.prepare(root, project, data, selected) if cached or os.path.lexists(project / entry_cache.DIRECTORY) else None
    links = list(destinations(project, agents, {**data, 'skills': selected}, cached))
    list(destinations(project, agents, data, cached))  # Validate parents even for an empty selection.
    old_skills = plan['old']['skills'] if plan else {}
    if plan:
        remaining = plan['manifest']['skills'] if cached else {}
        for agent in set(('codex', 'claude')) - set(agents):
            folder = project / ('.agents' if agent == 'codex' else '.claude') / 'skills'
            for name, item in old_skills.items():
                link = folder / name
                source = project / entry_cache.DIRECTORY / item['source'].removesuffix('/SKILL.md')
                retained = remaining.get(name, {}).get('source') == item['source']
                if not retained and link.is_symlink() and link.resolve() == source.resolve():
                    raise RuntimeError('Removing/remapping cached entries requires installation for both agents')
    known = {s['name']: s['path'] for s in data['skills']}
    known.update({name: item['source'].removesuffix('/SKILL.md') for name, item in old_skills.items() if name not in known})
    owned = {}
    for name, source in known.items():
        candidates = {root / source}
        if cached:
            candidates.add(project / entry_cache.DIRECTORY / source)
        if name in old_skills:
            candidates.add(project / entry_cache.DIRECTORY / old_skills[name]['source'].removesuffix('/SKILL.md'))
        owned[name] = {p.resolve() for p in candidates}
    for target, source in links:
        if os.path.lexists(target) and (not target.is_symlink() or target.resolve() not in owned[target.name]):
            raise RuntimeError(f'Existing skill conflict (left untouched): {target}')
    targets = {p for p, _ in links}
    stale = []
    for agent in agents:
        folder = project / ('.agents' if agent == 'codex' else '.claude') / 'skills'
        for name in known:
            target = folder / name
            if target not in targets and target.is_symlink() and target.resolve() in owned[name]:
                stale.append(target)
    return links, stale, plan


def install(project, agents):
    import commit_hooks
    hook = None
    if ROOT.resolve() == (project / '.agent-toolkit').resolve():
        try: hook = commit_hooks.plan(project)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as e:   # never block skill setup on hook ownership
            print(f'WARN: shared commit audit not installed: {e}', file=sys.stderr)
    data = verify_sources()
    selected = selection(project, data)
    links, stale, cache = preflight_install(project, agents, data, selected)
    from routes import plan_updates, write_updates
    route_updates = plan_updates(ROOT, project, selected, agents, existing_only=True)
    import entry_cache
    if cache_enabled(project):
        entry_cache.apply(cache)
    for target in stale:
        target.unlink()
    for target, source in links:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() and target.resolve() != source.resolve():
            target.unlink()
        if not os.path.lexists(target):
            target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=True)
    if cache and not cache_enabled(project):
        shutil.rmtree(project / entry_cache.DIRECTORY)
    write_updates(route_updates)
    try: commit_hooks.install(project, hook)
    except (OSError, subprocess.CalledProcessError) as e:   # e.g. read-only .git/config on a runner
        print(f'WARN: shared commit audit not activated: {e}', file=sys.stderr)
    verify(project, agents)


def verify(project, agents, check_routes=True):
    if ROOT.resolve() == (project / '.agent-toolkit').resolve():
        import commit_hooks
        try: commit_hooks.verify(project)
        except (RuntimeError, OSError, subprocess.CalledProcessError) as e:   # report, never fail skill verification
            print(f'WARN: {e}', file=sys.stderr)
    data = verify_sources()
    selected = selection(project, data)
    if cache_enabled(project):
        import entry_cache
        entry_cache.verify(entry_cache.prepare(ROOT, project, data, selected))
    for target, source in destinations(project, agents, {**data, 'skills': selected}):
        if not target.is_symlink() or target.resolve() != source.resolve() or not (target / 'SKILL.md').is_file():
            raise RuntimeError(f'Skill missing or points to another version: {target}')
    names = {s['name'] for s in selected}
    for target, source in destinations(project, agents, data):
        if target.name not in names and target.is_symlink() and target.resolve() == source.resolve():
            raise RuntimeError(f'Unselected toolkit link remains; rerun install: {target}')
    from routes import plan_updates
    if check_routes and plan_updates(ROOT, project, selected, agents, existing_only=True):
        raise RuntimeError('Stale route block; run emit-routes after reviewing catalogue changes')
    print(f'PASS: {len(selected)} selected skill files installed for {", ".join(agents)} in {project}')
    for package in data['packages']:
        print(f'  {package["name"]}: {package["commit"]}')


def status(project, agents):
    data = verify_sources()
    selected = selection(project, data)
    result = {'project': str(project), 'library_skills': len(data['skills']),
              'selected': [s['name'] for s in selected], 'agents': {},
              'entry_cache': 'enabled; pinned references/runtime still require setup' if cache_enabled(project) else 'disabled',
              'library_access': 'Search the full catalogue with scripts/skills.py; native links are only a subset. Explicit exclusions still apply.',
              'session_discovery': 'Not verified. Reload the agent or read the selected SKILL.md directly.'}
    missing = False
    for agent in agents:
        links = list(destinations(project, [agent], {**data, 'skills': selected}))
        absent = [p.name for p, source in links if not p.is_symlink()
                  or p.resolve() != source.resolve() or not (p / 'SKILL.md').is_file()]
        result['agents'][agent] = {'installed': len(links) - len(absent), 'missing': absent}
        missing = missing or bool(absent)
    print(json.dumps(result, indent=2))
    if missing:
        raise RuntimeError('Some selected skills are missing; run project setup')


def emit_routes(project, agents, check=False):
    from routes import plan_updates, write_updates
    selected = selection(project, verify_sources())
    updates = plan_updates(ROOT, project, selected, agents)
    verify(project, agents, check_routes=False)
    if check and updates:
        raise RuntimeError('Missing or stale route block: ' + ', '.join(str(path) for path, _ in updates))
    if not check:
        write_updates(updates)
    print(f'PASS: {len(selected)} skill routes {"checked" if check else "generated"} for {", ".join(agents)}')


def engine_details():
    scripts = ROOT / 'vendor/impeccable/skills/scripts'
    version = (scripts / 'VERSION').read_text().strip()
    system = {'Darwin': 'darwin', 'Linux': 'linux'}.get(platform.system())
    arch = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
    if not system or not arch:
        raise RuntimeError('Runtime setup supports macOS and Linux; use WSL on Windows.')
    asset = f'impeccable-{system}-{arch}'
    for line in (scripts / 'engine-checksums.txt').read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[:2] == [version, asset]:
            return scripts / 'bin' / f'{system}-{arch}' / 'impeccable', version, asset, parts[2]
    raise RuntimeError(f'No pinned checksum for {asset}')


def setup_engine():
    verify_sources()
    binary, version, asset, checksum = engine_details()
    if binary.exists():
        if digest(binary) != checksum:
            raise RuntimeError(f'Existing engine failed checksum: {binary}')
    else:
        binary.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://github.com/pbakaus/impeccable/releases/download/engine-v{version}/{asset}'
        # Preserve the session proxy and CA configuration through urllib defaults.
        with urllib.request.urlopen(url, timeout=60) as response:
            with tempfile.NamedTemporaryFile(dir=binary.parent, delete=False) as output:
                tmp = Path(output.name)
                try:
                    shutil.copyfileobj(response, output)
                except BaseException:
                    tmp.unlink(missing_ok=True)
                    raise
        try:
            if digest(tmp) != checksum:
                raise RuntimeError('Downloaded engine failed its pinned checksum')
            tmp.chmod(0o755)
            tmp.replace(binary)
        finally:
            tmp.unlink(missing_ok=True)
    binary.chmod(0o755)
    print(f'Installed verified Impeccable engine {version}: {binary}')


def verify_engine():
    verify_sources()
    binary, version, _, checksum = engine_details()
    if not binary.is_file() or digest(binary) != checksum:
        raise RuntimeError('Pinned Impeccable engine missing or changed; run setup-runtime')
    result = subprocess.check_output([str(binary), 'engine-probe'], text=True, timeout=15).strip()
    if result != f'impeccable-engine {version}':
        raise RuntimeError(f'Unexpected engine response: {result}')
    launcher = ROOT / 'vendor/impeccable/skills/scripts/impeccable'
    # Explicit overrides defeat pinning; do not silently claim reproducibility.
    if os.environ.get('IMPECCABLE_BIN'):
        raise RuntimeError('IMPECCABLE_BIN overrides the pinned engine; unset it for this project')
    launched = subprocess.check_output([str(launcher), 'engine-probe'], text=True, timeout=15).strip()
    if launched != result:
        raise RuntimeError('Impeccable launcher selected a different engine')
    print(f'PASS: Impeccable engine {version} checksum and launcher')


def verify_taste():
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Taste Skill requires Node.js 22 or newer')
    major = int(subprocess.check_output([node, '-p', 'process.versions.node.split(".")[0]'], text=True))
    if major < 22:
        raise RuntimeError('Taste Skill requires Node.js 22 or newer')
    # Use Taste's own browser discovery, ensuring our check matches its runtime.
    module = (ROOT / 'vendor/taste/skills/scripts/lib/cdp.mjs').as_uri()
    chrome = subprocess.check_output([
        node, '--input-type=module', '-e',
        'const {findChrome} = await import(process.argv[1]); '
        'const path = findChrome(); if (!path) process.exit(1); console.log(path);', module
    ], text=True, timeout=15).strip()
    subprocess.run([chrome, '--version'], check=True, timeout=15, stdout=subprocess.DEVNULL)
    print(f'PASS: Taste runtime; Node.js {major}; browser {chrome}')



def runtime_packages(project=None):
    data = verify_sources()
    skills = selection(project, data) if project else data['skills']
    return {s['package'] for s in skills}


def verify_runtime(project=None):
    packages = runtime_packages(project)
    if 'impeccable' in packages:
        verify_engine()
    if 'taste' in packages:
        verify_taste()
    if 'hyperframes' in packages:
        print('NOTE: HyperFrames skill files installed; its CLI/render runtime is verified per video task.')
    if not packages & {'impeccable', 'taste'}:
        print('PASS: no design runtime required by this selection')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'verify', 'status', 'emit-routes', 'init-project', 'bootstrap-global', 'handoff-config', 'verify-cache', 'verify-sources', 'setup-runtime', 'verify-runtime'])
    parser.add_argument('target', nargs='?', type=Path, help='Git repository root for init-project')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--agents', nargs='+', choices=['codex', 'claude'], default=['codex', 'claude'])
    parser.add_argument('--check', action='store_true', help='Check routes without writing; with verify-cache also require committed clean outputs')
    parser.add_argument('--codex-home', type=Path, help='With bootstrap-global, defaults to CODEX_HOME or ~/.codex')
    args = parser.parse_args()
    if args.check and args.command not in ('emit-routes', 'verify-cache'):
        parser.error('--check is only valid with emit-routes or verify-cache')
    if args.target and args.command != 'init-project':
        parser.error('A positional target is only valid with init-project')
    if args.codex_home and args.command != 'bootstrap-global':
        parser.error('--codex-home is only valid with bootstrap-global')
    if args.project and not args.project.is_dir():
        parser.error('--project must name an existing project directory')
    if args.command == 'init-project':
        if bool(args.target) == bool(args.project):
            parser.error('Provide one target repository, positionally or with --project')
        if args.agents != ['codex', 'claude']:
            parser.error('init-project initializes both agents; use install for individual-agent changes')
        from project_setup import init_project
        verify_sources()
        print(json.dumps(init_project(args.target or args.project, ROOT), indent=2))
    elif args.command == 'bootstrap-global':
        from project_setup import bootstrap_global
        verify_sources()
        home = args.codex_home or Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
        print(json.dumps(bootstrap_global(ROOT, home), indent=2))
    elif args.command == 'verify-cache':
        if not args.project:
            parser.error('verify-cache requires --project')
        data = verify_sources()
        selected = selection(args.project, data)
        if cache_enabled(args.project):
            import entry_cache
            entry_cache.verify(entry_cache.prepare(ROOT, args.project, data, selected), tracked=args.check)
            verify(args.project, args.agents, check_routes=False)
            print('PASS: readable entry cache matches the pinned sources' + (' and committed files' if args.check else ''))
        elif os.path.lexists(args.project / '.agent-skill-cache'):
            raise RuntimeError('Disabled readable cache must be removed through project setup')
        else:
            print('PASS: readable entry cache not enabled')
    elif args.command == 'handoff-config':
        from handoff import resolve
        print(json.dumps(resolve(ROOT, args.project or Path.cwd()), indent=2))
    elif args.command == 'verify-sources':
        data = verify_sources()
        print(f'PASS: {len(data["files"])} vendored files match toolkit.lock.json')
    elif args.command == 'setup-runtime':
        if 'impeccable' in runtime_packages(args.project):
            setup_engine()
        else:
            print('No Impeccable engine required by this selection')
    elif args.command == 'verify-runtime':
        verify_runtime(args.project)
    else:
        if not args.project or not args.project.is_dir():
            parser.error('--project must name an existing project directory')
        project = args.project.resolve()
        if args.command == 'emit-routes':
            emit_routes(project, args.agents, check=args.check)
        else:
            {'install': install, 'verify': verify, 'status': status}[args.command](project, args.agents)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
