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
    if not isinstance(settings, dict) or settings.get('schema') != 1 or set(settings) - {'schema', 'groups', 'include', 'exclude', 'native_limit'}:
        raise RuntimeError('Invalid project selection format')
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


def destinations(project, agents, data):
    for agent in agents:
        folder = '.agents' if agent == 'codex' else '.claude'
        parent = project / folder / 'skills'
        for ancestor in (project / folder, parent):
            if ancestor.is_symlink():
                raise RuntimeError(f'Refusing redirected installation directory: {ancestor}')
            if ancestor.exists() and not ancestor.is_dir():
                raise RuntimeError(f'Installation directory is a file: {ancestor}')
        for skill in data['skills']:
            yield parent / skill['name'], ROOT / skill['path']


def install(project, agents):
    data = verify_sources()
    selected = selection(project, data)
    links = list(destinations(project, agents, {**data, 'skills': selected}))
    # Check all parent paths before touching any link, including an empty selection.
    all_links = list(destinations(project, agents, data))
    from routes import plan_updates, write_updates
    route_updates = plan_updates(ROOT, project, selected, agents, existing_only=True)
    # Preflight every destination before making any changes.
    for target, source in links:
        if os.path.lexists(target):
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise RuntimeError(f'Existing skill conflict (left untouched): {target}')
    selected_targets = {target for target, _ in links}
    # Deselect only exact toolkit links. Never remove local copies or foreign links.
    stale = [target for target, source in all_links if target not in selected_targets
             and target.is_symlink() and target.resolve() == source.resolve()]
    for target in stale:
        target.unlink()
    for target, source in links:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.lexists(target):
            target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=True)
    write_updates(route_updates)
    verify(project, agents)


def verify(project, agents, check_routes=True):
    data = verify_sources()
    selected = selection(project, data)
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
    parser.add_argument('command', choices=['install', 'verify', 'status', 'emit-routes', 'verify-sources', 'setup-runtime', 'verify-runtime'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--agents', nargs='+', choices=['codex', 'claude'], default=['codex', 'claude'])
    parser.add_argument('--check', action='store_true', help='With emit-routes, fail on missing/stale blocks without changing files')
    args = parser.parse_args()
    if args.check and args.command != 'emit-routes':
        parser.error('--check is only valid with emit-routes')
    if args.project and not args.project.is_dir():
        parser.error('--project must name an existing project directory')
    if args.command == 'verify-sources':
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
