"""Reviewable entry texts, licensed from the pinned library; never a second authority."""
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

DIRECTORY = '.agent-skill-cache'
MANIFEST = 'manifest.json'
README = ("# Generated readable skill entries\n\n"
          "Selected SKILL.md texts and license/notices are exact copies from the project's pinned .agent-toolkit. "
          "Do not edit them manually. Regenerate with project setup after a reviewed source/selection update. "
          "The manifest records canonical paths and SHA-256 hashes, not an independent source revision.\n\n"
          "Agent links can read these entries before submodule setup. Relative reference aliases and runtimes "
          "still require the pinned library: git submodule update --init -- .agent-toolkit for references, "
          "then this project's documented setup script for runtimes when needed. This cache is not a standalone runtime.\n")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(value):
    return (isinstance(value, str) and value.startswith('vendor/') and '\\' not in value
            and all(x not in ('', '.', '..') for x in value.split('/'))
            and not any(ord(x) < 32 for x in value))


def parent_paths(names):
    return {str(parent) for name in names for parent in PurePosixPath(name).parents if str(parent) != '.'}


def expected(root, project, data, selected):
    packages = {skill['package'] for skill in selected}
    entries = {skill['path'] + '/SKILL.md' for skill in selected}
    licenses = {name for name in data['files'] if name.split('/')[1] in packages
                and PurePosixPath(name).name.upper().startswith(('LICENSE', 'LICENCE', 'NOTICE', 'COPYING'))}
    for package in packages:
        if not any(name.startswith('vendor/' + package + '/') for name in licenses):
            raise RuntimeError('Cache requires a recorded license for package: ' + package)
    files = {}
    for name in entries | licenses:
        if not safe(name):
            raise RuntimeError('Unsafe cache source path')
        value = (root / name).read_bytes()
        if sha(value) != data['files'][name]:
            raise RuntimeError('Cache source hash mismatch: ' + name)
        files[name] = value
    files['README.md'] = README.encode()
    files['.gitignore'] = b'# Generated cache files must remain reviewable and tracked.\n!*/\n!**/*\n'
    parents = parent_paths(entries | licenses)
    links = {}
    for source in data['files']:
        if not safe(source):
            raise RuntimeError('Unsafe cache reference path')
        parts = PurePosixPath(source).parts
        for index in range(1, len(parts)):
            parent, child = '/'.join(parts[:index]), '/'.join(parts[:index + 1])
            if parent in parents and child not in parents and child not in files:
                if PurePosixPath(child).name in ('.gitignore', '.gitattributes'):
                    break
                target = project / '.agent-toolkit' / child
                links[child] = os.path.relpath(target, (project / DIRECTORY / child).parent)
                break
    manifest = {'schema': 1,
                'skills': {s['name']: {'source': s['path'] + '/SKILL.md', 'sha256': data['files'][s['path'] + '/SKILL.md']}
                           for s in selected},
                'packages': {p['name']: {'repository': p['repository'],
                                        'licenses': sorted(x for x in licenses if x.startswith('vendor/' + p['name'] + '/'))}
                             for p in data['packages'] if p['name'] in packages},
                'files': {name: sha(value) for name, value in sorted(files.items())},
                'links': dict(sorted(links.items()))}
    return manifest, files


def encoded(manifest):
    return (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()


def regular_parents(base, name):
    path = base / name
    for parent in (path.parent, *path.parents):
        if parent == base.parent:
            break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise RuntimeError('Redirected cache parent: ' + str(parent))
    return path


def read_manifest(project, desired):
    base = project / DIRECTORY
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        raise RuntimeError('Readable cache must be a regular directory')
    path = base / MANIFEST
    if not os.path.lexists(path):
        return desired
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
        raise RuntimeError('Invalid readable-cache ownership manifest')
    raw = path.read_bytes()
    old = json.loads(raw)
    if (not isinstance(old, dict) or set(old) != {'schema', 'skills', 'packages', 'files', 'links'}
            or type(old['schema']) is not int or old['schema'] != 1
            or any(not isinstance(old[key], dict) for key in ('skills', 'packages', 'files', 'links'))):
        raise RuntimeError('Invalid readable-cache ownership schema')
    if raw != encoded(desired):
        previous = subprocess.run(['git', '-C', str(project), 'show', 'HEAD:' + DIRECTORY + '/' + MANIFEST],
                                  capture_output=True)
        if previous.returncode or previous.stdout != raw:
            raise RuntimeError('Modified/unowned readable-cache manifest; left untouched')
    for name, item in old['skills'].items():
        if (not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name)
                or not isinstance(item, dict) or set(item) != {'source', 'sha256'}
                or not safe(item['source']) or not item['source'].endswith('/SKILL.md')
                or not isinstance(item['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
            raise RuntimeError('Unsafe readable-cache skill mapping')
    if set(old['files']) & set(old['links']):
        raise RuntimeError('Overlapping readable-cache ownership entries')
    for name, value in old['files'].items():
        if ((name not in ('README.md', '.gitignore') and not safe(name))
                or not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)):
            raise RuntimeError('Unsafe readable-cache ownership entry')
    for name, value in old['links'].items():
        if not safe(name) or value != os.path.relpath(project / '.agent-toolkit' / name, (base / name).parent):
            raise RuntimeError('Unsafe readable-cache reference alias')
    return old


def prepare(root, project, data, selected):
    desired, files = expected(root, project, data, selected)
    old = read_manifest(project, desired)
    base = project / DIRECTORY
    owned = set(old['files']) | set(old['links']) | {MANIFEST}
    directories = parent_paths(owned)
    if base.exists():
        for directory, folders, names in os.walk(base, followlinks=False):
            for name in folders + names:
                path = Path(directory) / name
                relative = path.relative_to(base).as_posix()
                if relative not in owned and relative not in directories:
                    raise RuntimeError('Foreign cache path (left untouched): ' + relative)
        for name, checksum in old['files'].items():
            path = regular_parents(base, name)
            if os.path.lexists(path) and (path.is_symlink() or not path.is_file() or sha(path.read_bytes()) != checksum):
                raise RuntimeError('Modified cached source (left untouched): ' + name)
        for name, target in old['links'].items():
            path = regular_parents(base, name)
            if os.path.lexists(path) and (not path.is_symlink() or os.readlink(path) != target):
                raise RuntimeError('Modified cache reference (left untouched): ' + name)
    for name in set(files) | set(desired['links']):
        if name not in owned and name not in directories and not any(name.startswith(alias + '/') for alias in old['links']) and os.path.lexists(base / name):
            raise RuntimeError('New cache path conflicts with existing content: ' + name)
    return {'project': project, 'manifest': desired, 'files': files, 'old': old}


def verify(plan, tracked=False):
    project, manifest = plan['project'], plan['manifest']
    base = project / DIRECTORY
    path = base / MANIFEST
    if not path.is_file() or path.is_symlink() or path.read_bytes() != encoded(manifest):
        raise RuntimeError('Missing or stale readable-cache manifest; regenerate with project setup')
    for name, checksum in manifest['files'].items():
        path = regular_parents(base, name)
        if path.is_symlink() or not path.is_file() or sha(path.read_bytes()) != checksum:
            raise RuntimeError('Missing or stale cached source: ' + name)
    for name, target in manifest['links'].items():
        path = regular_parents(base, name)
        if not path.is_symlink() or os.readlink(path) != target:
            raise RuntimeError('Missing or stale cache reference: ' + name)
    if tracked:
        wanted = {DIRECTORY + '/' + name for name in set(manifest['files']) | set(manifest['links']) | {MANIFEST}}
        actual = subprocess.check_output(['git', '-C', str(project), 'ls-files', '--', DIRECTORY], text=True).splitlines()
        dirty = subprocess.check_output(['git', '-C', str(project), 'status', '--porcelain', '--untracked-files=all', '--', DIRECTORY], text=True)
        if set(actual) != wanted or dirty:
            raise RuntimeError('Readable cache must be committed/tracked and clean; stage reviewed generated outputs')


def apply(plan):
    try:
        verify(plan)
        return
    except RuntimeError:
        pass  # prepare() already refused modified/foreign data; missing/stale owned output is repairable.
    project, manifest = plan['project'], plan['manifest']
    base = project / DIRECTORY
    stage = Path(tempfile.mkdtemp(prefix=DIRECTORY + '-stage-', dir=project))
    backup = None
    try:
        for name, content in plan['files'].items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        for name, target in manifest['links'].items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
        (stage / MANIFEST).write_bytes(encoded(manifest))
        if base.exists():
            backup = Path(tempfile.mkdtemp(prefix=DIRECTORY + '-backup-', dir=project))
            backup.rmdir()
            base.rename(backup)
        stage.rename(base)
    except BaseException:
        if backup and backup.exists() and not base.exists():
            backup.rename(base)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if backup and backup.exists():
            shutil.rmtree(backup)
