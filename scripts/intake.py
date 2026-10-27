#!/usr/bin/env python3
"""Stage and validate a reviewed skill from a pinned local Git checkout. No network or model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from skills import catalogue, fields

ROOT = Path(__file__).resolve().parents[1]


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid relative source path')
    parts = value.split('/')
    if PurePosixPath(value).is_absolute() or any(p in ('', '.', '..', '.git') for p in parts):
        raise ValueError('Source paths must stay inside their checkout')
    return value


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], timeout=30)


def target_path(root, value):
    path = root / relative(value)
    if any(p.is_symlink() for p in [path, *path.parents] if p != root and root in p.parents):
        raise ValueError('Refusing redirected toolkit path: ' + value)
    return path


def intake(request, root=ROOT, apply=False):
    required = {'name', 'checkout', 'source_path', 'license_path', 'repository', 'revision', 'guide', 'group', 'review_notes'}
    if set(request) != required or not all(isinstance(v, str) and v.strip() for v in request.values()):
        raise ValueError('Intake requires exactly: ' + ', '.join(sorted(required)))
    name, group = request['name'], request['group']
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', group):
        raise ValueError('Invalid name or group')
    url = urlsplit(request['repository'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Use a public HTTPS repository URL without credentials')
    source = Path(request['checkout']).resolve()
    source_path, license_path = relative(request['source_path']), relative(request['license_path'])
    revision = request['revision']
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or git(source, 'rev-parse', 'HEAD').decode().strip() != revision:
        raise ValueError('Source checkout must be at the exact reviewed 40-character revision')
    if git(source, 'config', '--get', 'remote.origin.url').decode().strip().removesuffix('.git') != request['repository'].removesuffix('.git'):
        raise ValueError('Source origin does not match the reviewed repository')
    # Read committed blobs, never uncommitted content or Git symlink targets.
    objects = git(source, 'ls-tree', '-rz', 'HEAD', '--', source_path, license_path).split(b'\0')
    imported = {}
    for obj in filter(None, objects):
        metadata, raw_path = obj.split(b'\t', 1)
        mode, kind, _ = metadata.decode().split()
        path = relative(raw_path.decode())
        if mode not in ('100644', '100755') or kind != 'blob':
            raise ValueError('Only regular committed source files are accepted')
        if path == license_path:
            dest = f'vendor/{name}/LICENSE'
        elif path.startswith(source_path + '/'):
            dest = f'vendor/{name}/skills/' + path[len(source_path) + 1:]
        else:
            raise ValueError('source_path must be a skill directory')
        imported[dest] = (git(source, 'show', revision + ':' + path), int(mode, 8) & 0o777)
    if f'vendor/{name}/LICENSE' not in imported or f'vendor/{name}/skills/SKILL.md' not in imported:
        raise ValueError('Committed license and SKILL.md are required')
    if len(imported) > 2000 or sum(len(b) for b, _ in imported.values()) > 32 * 1024 * 1024:
        raise ValueError('Large collections need deliberate maintenance review')
    guide = Path(request['guide']).read_text()
    values = fields(guide)
    lock_path = root / '.intake-lock'
    try:
        lock_path.mkdir()
    except FileExistsError:
        raise ValueError('Another intake is running; retry after it completes')
    try:
        if (root / 'catalog').is_symlink() or (root / 'vendor').is_symlink():
            raise ValueError('Refusing redirected catalogue/vendor directory')
        data = json.loads(target_path(root, 'toolkit.lock.json').read_text())
        catalogue(root)
        old = next((s for s in data['skills'] if s['name'] == name), None)
        expected = {'name': name, 'path': f'vendor/{name}/skills', 'package': name}
        packages = [p for p in data['packages'] if p['name'] == name]
        if (old and (old != expected or len(packages) != 1 or packages[0]['repository'] != request['repository']
                     or any(s['package'] == name and s['name'] != name for s in data['skills']))) or (not old and packages):
            raise ValueError('Name/package collision; existing multi-skill collections need deliberate maintenance')
        if not old and (root / 'vendor' / name).exists():
            raise ValueError('Vendor directory already exists')
        prefix = f'vendor/{name}/'
        old_files = {p for p in data['files'] if p.startswith(prefix)}
        for path in old_files:
            del data['files'][path]
        data['files'].update({p: hashlib.sha256(content).hexdigest() for p, (content, _) in imported.items()})
        package = {'name': name, 'repository': request['repository'], 'commit': revision,
                   'source_path': source_path, 'license_path': license_path, 'review_notes': request['review_notes']}
        data['packages'] = [p for p in data['packages'] if p['name'] != name] + [package]
        if not old:
            data['skills'].append(expected)
        members = data.setdefault('groups', {}).setdefault(group, [])
        if name not in members:
            members.append(name)
        index = (root / 'catalog/README.md').read_text()
        row = f"| [{name}]({name}.md) | {values['Purpose'][:180].replace('|', '/')} | {values['Invocation']} |"
        row_pattern = rf'^\| \[{re.escape(name)}\]\({re.escape(name)}\.md\) .*?$'
        if old:
            index = re.sub(row_pattern, lambda _: row, index, flags=re.M)
        else:
            anchor = '\n## Before adding or changing a skill'
            if anchor not in index:
                raise ValueError('Catalogue index admission section is missing')
            table, rest = index.split(anchor, 1)
            index = table.rstrip() + '\n' + row + '\n' + anchor + rest
        changes = {**imported, f'catalog/{name}.md': (guide.encode(), 0o644),
                   'catalog/README.md': (index.encode(), 0o644),
                   'toolkit.lock.json': ((json.dumps(data, indent=2) + '\n').encode(), 0o644)}
        removals = old_files - imported.keys()
        with tempfile.TemporaryDirectory(prefix='skill-admission-') as folder:
            staged = Path(folder)
            shutil.copytree(root / 'catalog', staged / 'catalog')
            for path, checksum in json.loads((root / 'toolkit.lock.json').read_text())['files'].items():
                relative(path)
                original = target_path(root, path)
                if original.is_symlink() or hashlib.sha256(original.read_bytes()).hexdigest() != checksum:
                    raise ValueError('Existing vendored source changed: ' + path)
                target = staged / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original.read_bytes())
            for path in removals:
                (staged / path).unlink()
            for path, (content, _) in changes.items():
                target = staged / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            catalogue(staged)  # All guides, restrictions and links must validate before mutation.
        touched = sorted(set(changes) | removals)
        for path in touched:
            target_path(root, path)
        changed = [p for p in touched if (p in removals or not (root / p).exists()
                   or (root / p).read_bytes() != changes[p][0] or (root / p).stat().st_mode & 0o777 != changes[p][1])]
        if apply:
            backups = {p: ((root / p).read_bytes(), (root / p).stat().st_mode & 0o777)
                       if (root / p).exists() else None for p in changed}
            try:
                for path in changed:
                    target = root / path
                    if path in removals:
                        target.unlink()
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(changes[path][0])
                        target.chmod(changes[path][1])
            except BaseException:
                for path, backup in backups.items():
                    target = root / path
                    if backup is None:
                        target.unlink(missing_ok=True)
                    else:
                        target.write_bytes(backup[0])
                        target.chmod(backup[1])
                raise
        return {'name': name, 'revision': revision, 'state': 'applied' if apply else 'validated-proposal',
                'changed_files': changed, 'publication': 'not performed; inspect diff and use checked PR workflow'}
    finally:
        lock_path.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Apply validated local diff; never publishes')
    args = parser.parse_args()
    print(json.dumps(intake(json.loads(args.request.read_text()), apply=args.apply), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
