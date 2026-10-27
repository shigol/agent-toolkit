#!/usr/bin/env python3
"""Validate the shared manifest and decide which updates can merge unattended."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def safe_path(value):
    return (isinstance(value, str) and value.startswith('vendor/')
            and '\\' not in value and not any(ord(c) < 32 for c in value)
            and all(part not in ('', '.', '..') for part in value.split('/'))
            and not PurePosixPath(value).is_absolute())


def validate(root):
    data = json.loads((root / 'toolkit.lock.json').read_text())
    if data['schema'] != 1:
        raise ValueError('Unsupported manifest schema')
    tracked = {}
    for entry in git(root, 'ls-files', '-s', '--', 'vendor').splitlines():
        metadata, path = entry.split('\t', 1)
        mode, _, stage = metadata.split()
        if mode not in ('100644', '100755') or stage != '0':
            raise ValueError('Vendor sources must be regular tracked files')
        tracked[path] = mode
    if set(tracked) != set(data['files']):
        raise ValueError('Manifest must cover every tracked vendor file exactly')
    for path, expected in data['files'].items():
        if not safe_path(path) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError('Invalid source path or checksum')
        source = root / path
        if source.is_symlink() or not source.is_file() or root.resolve() not in source.resolve().parents:
            raise ValueError('Source must stay inside the toolkit')
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Source checksum mismatch: ' + path)
    names = set()
    for skill in data['skills']:
        name, path = skill['name'], skill['path']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name) or name in names:
            raise ValueError('Invalid or duplicate skill name')
        if not safe_path(path) or path + '/SKILL.md' not in data['files']:
            raise ValueError('Every skill needs a checksum-covered SKILL.md')
        names.add(name)
    if not names:
        raise ValueError('Empty skill inventory')
    packages = {p['name'] for p in data['packages']}
    for group, members in data.get('groups', {}).items():
        if not isinstance(members, list) or not set(members) <= packages:
            raise ValueError('Invalid package selection group: ' + group)
    return data


def review_scan(text):
    """Report categories only: never echo a possible credential or source instruction."""
    patterns = {
        'urls': r'https?://',
        'download_commands': r'\b(?:curl|wget)\b',
        'credential_terms': r'\b(?:api[-_ ]?key|token|password|secret|credential)s?\b',
        'instruction_override': r'\b(?:ignore|override|bypass)\b.{0,60}\b(?:previous|prior|system|developer|instructions)\b',
        'tool_commands': r'\b(?:bash|sh|python3?|node|npm|npx|pip|uv|git|exec|rm)\s+|tool[_ -]?call|run (?:this|the) command',
    }
    return {name: len(re.findall(pattern, text, re.I)) for name, pattern in patterns.items()}


def policy(root, base, head='HEAD'):
    """Documentation/metadata may merge unattended; vendored sources always need review."""
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, head], check=True)
    changes = [line.split('\t', 1) for line in
               git(root, 'diff', '--raw', '--no-abbrev', '--no-renames', base, head).splitlines()]
    vendors = [path for _, path in changes if path.startswith('vendor/')]
    for path in vendors:
        diff = git(root, 'diff', '--no-ext-diff', '--unified=0', base, head, '--', path)
        added = '\n'.join(row[1:] for row in diff.splitlines()
                          if row.startswith('+') and not row.startswith('+++'))
        print('REVIEW SCAN: ' + json.dumps({'path': path, 'categories': review_scan(added)}))
    old = json.loads(git(root, 'show', base + ':toolkit.lock.json'))
    new = json.loads(git(root, 'show', head + ':toolkit.lock.json'))
    if old['schema'] != new['schema']:
        raise ValueError('Manifest format changes need review')
    if old.get('patches', []) != new.get('patches', []):
        raise ValueError('Portability patch provenance changes need review')
    for group, members in old.get('groups', {}).items():
        if not set(members) <= set(new.get('groups', {}).get(group, [])):
            raise ValueError('Removing packages from a project selection group needs review')
    new_skills = {s['name']: s for s in new['skills']}
    if any(new_skills.get(s['name']) != s for s in old['skills']):
        raise ValueError('Removing or moving an existing skill needs review')
    if vendors:
        raise ValueError(f'Vendored skill text/source requires independent review: {len(vendors)} file(s)')
    for metadata, path in changes:
        old_mode, new_mode, _, _, status = metadata[1:].split()
        if path == 'toolkit.lock.json':
            raise ValueError('Manifest changes require independent review')
        if (status not in ('A', 'M') or new_mode != '100644'
                or old_mode not in ('000000', '100644')
                or not (path.endswith('.md') or path == 'toolkit.lock.json')):
            raise ValueError('Non-text, removed or executable toolkit files need review: ' + path)
    print('PASS: additive skill instructions; eligible for automatic merge')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'policy'])
    parser.add_argument('--root', type=Path, default=Path('.agent-toolkit'))
    parser.add_argument('--base')
    args = parser.parse_args()
    if args.command == 'policy':
        if not args.base:
            parser.error('--base is required for policy')
        policy(args.root, args.base)
    else:
        data = validate(args.root)
        print(f'PASS: {len(data["skills"])} registered skills and all source hashes')
