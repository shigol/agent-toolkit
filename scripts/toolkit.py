#!/usr/bin/env python3
"""Install and verify shared project skills. Python 3.9+, no third-party packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
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
    return data


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
    links = list(destinations(project, agents, data))
    # Preflight every destination before making any changes.
    for target, source in links:
        if os.path.lexists(target):
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise RuntimeError(f'Existing skill conflict (left untouched): {target}')
    for target, source in links:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.lexists(target):
            target.symlink_to(os.path.relpath(source, target.parent), target_is_directory=True)
    verify(project, agents)


def verify(project, agents):
    data = verify_sources()
    for target, source in destinations(project, agents, data):
        if not target.is_symlink() or target.resolve() != source.resolve():
            raise RuntimeError(f'Skill missing or points to another version: {target}')
    print(f'PASS: {len(data["skills"])} skills available to {", ".join(agents)} in {project}')
    for package in data['packages']:
        print(f'  {package["name"]}: {package["commit"]}')


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


def verify_runtime():
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
    print(f'PASS: Impeccable engine {version}; Node.js {major}; browser {chrome}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'verify', 'verify-sources', 'setup-runtime', 'verify-runtime'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--agents', nargs='+', choices=['codex', 'claude'], default=['codex', 'claude'])
    args = parser.parse_args()
    if args.command == 'verify-sources':
        data = verify_sources()
        print(f'PASS: {len(data["files"])} vendored files match toolkit.lock.json')
    elif args.command == 'setup-runtime':
        setup_engine()
    elif args.command == 'verify-runtime':
        verify_runtime()
    else:
        if not args.project or not args.project.is_dir():
            parser.error('--project must name an existing project directory')
        project = args.project.resolve()
        {'install': install, 'verify': verify}[args.command](project, args.agents)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
