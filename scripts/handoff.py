"""Resolve nonsecret handoff metadata; never inspect credentials or provider access."""
import json
from pathlib import Path
import re


def resolve(root, project=None):
    root = Path(root)
    path, source = root / 'HANDOFF.json', 'toolkit-default'
    override = Path(project) / '.agent-handoff.json' if project else None
    if override and (override.exists() or override.is_symlink()):
        path, source = override, 'project-override'
    result = {'credentials': 'not_checked', 'provider_access': 'not_checked', 'source': source}
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Handoff profile must be a regular file')
    if not path.exists():
        return {**result, 'status': 'not_configured'}
    if path.stat().st_size > 4096:
        raise ValueError('Handoff profile exceeds 4 KiB')
    data = json.loads(path.read_text())
    allowed = {'schema', 'gateway_repository', 'gateway_issue', 'brief_directory', 'disabled'}
    if not isinstance(data, dict) or set(data) - allowed or type(data.get('schema')) is not int or data['schema'] != 1:
        raise ValueError('Invalid handoff profile schema or fields')
    if 'disabled' in data and type(data['disabled']) is not bool:
        raise ValueError('Handoff disabled flag must be boolean')
    if data.get('disabled'):
        return {**result, 'status': 'disabled'}
    repo, issue, directory = (data.get(key) for key in ('gateway_repository', 'gateway_issue', 'brief_directory'))
    if not isinstance(repo, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}', repo) or any(x in ('.', '..') for x in repo.split('/')):
        raise ValueError('Invalid handoff gateway repository')
    if type(issue) is not int or issue < 1 or issue > 2**53 - 1:
        raise ValueError('Invalid handoff gateway issue')
    if not isinstance(directory, str) or not re.fullmatch(r'(?:docs|codex|tools)/[A-Za-z0-9_./-]+', directory) or any(x in ('', '.', '..') for x in directory.split('/')):
        raise ValueError('Invalid handoff brief directory')
    return {**result, 'schema': 1, 'status': 'profile_resolved', 'gateway_repository': repo,
            'gateway_issue': issue, 'brief_directory': directory}
