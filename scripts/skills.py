#!/usr/bin/env python3
"""Validate and search the shared skill catalogue without loading skill bodies."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('Purpose', 'Invocation', 'Use when', 'Do not use when',
          'Overlaps and default', 'Requirements', 'Expected output',
          'Positive example', 'Negative example', 'Source')
STOP = set('a an and are as at be build by can code create diagnose do existing find fix for from give help how i implement improve in into inspect is it make me my of on or our please project refine review some task that the their then these this to troubleshoot us use using want we with work you your'.split())


def fields(text):
    result = {}
    for field in FIELDS:
        found = re.findall(r'^\*\*' + re.escape(field) + r':\*\* (\S.*)$', text, re.M)
        if len(found) != 1:
            raise ValueError(f'Missing or repeated catalogue field: {field}')
        result[field] = found[0].strip()
    return result


def catalogue(root=ROOT):
    manifest = json.loads((root / 'toolkit.lock.json').read_text())
    skills = manifest['skills']
    names = {s['name'] for s in skills}
    if len(names) != len(skills):
        raise ValueError('Duplicate registered skill names')
    if {p.stem for p in (root / 'catalog').glob('*.md') if p.name != 'README.md'} != names:
        raise ValueError('Catalogue inventory differs from registered skills')
    index = (root / 'catalog/README.md').read_text()
    entries = []
    for skill in skills:
        name = skill['name']
        if (not re.fullmatch(r'[a-z0-9][a-z0-9-]*', name)
                or not skill['path'].startswith('vendor/')
                or any(p in ('', '.', '..') for p in skill['path'].split('/'))
                or '\\' in skill['path']):
            raise ValueError('Invalid registered skill path or name')
        guide = root / 'catalog' / (name + '.md')
        source = root / skill['path'] / 'SKILL.md'
        if any(root.resolve() not in p.resolve().parents or p.is_symlink() for p in (guide, source)):
            raise ValueError(f'{name}: source and guide must stay inside the toolkit')
        values = fields(guide.read_text())
        if values['Source'] != f"[Pinned SKILL.md](../{skill['path']}/SKILL.md)":
            raise ValueError(f'{name}: incorrect source link')
        body = source.read_text()
        frontmatter = body.split('---', 2)[1] if body.startswith('---\n') else ''
        manual = bool(re.search(r'^disable-model-invocation:\s*true\s*$', frontmatter, re.M))
        mode = values['Invocation']
        if mode not in {'automatic', 'explicit-only', 'explicit-direction'}:
            raise ValueError(f'{name}: invalid invocation')
        if manual != (mode == 'explicit-only'):
            raise ValueError(f'{name}: source invocation restriction mismatch')
        row = rf'^\| \[{re.escape(name)}\]\({re.escape(name)}\.md\) \| .+ \| {mode} \|$'
        if len(re.findall(row, index, re.M)) != 1:
            raise ValueError(f'{name}: missing or inconsistent index row')
        entries.append({**skill, 'guide': str(guide.resolve()),
                        'source': str(source.resolve()), 'fields': values})
    return entries


def tokens(text):
    words = re.findall(r'[a-z0-9]+', text.lower())
    # Only simple inflection normalization; task eligibility is decided by the agent.
    return [w[:-1] if len(w) > 4 and w.endswith('s') else w for w in words if w not in STOP]


def search(query, root=ROOT, project=None, limit=5, max_chars=4000, include_restricted=False):
    if not 1 <= limit <= 5 or not 256 <= max_chars <= 4000 or len(query) > 2000:
        raise ValueError('Search limits: 1–5 results, 256–4000 characters, query <=2000 characters')
    entries = catalogue(root)
    excluded = set()
    if project:
        import toolkit
        manifest = json.loads((root / 'toolkit.lock.json').read_text())
        toolkit.selection(project, manifest)  # Validate config; groups only control native exposure.
        config = project / '.agent-toolkit.json'
        if config.exists():
            excluded = set(json.loads(config.read_text()).get('exclude', []))
    docs = []
    for entry in entries:
        f = entry['fields']
        # Exclusions, negative examples and references to other skills are never positive bait.
        docs.append(Counter(tokens(entry['name'] + ' ' + f['Purpose'] + ' ' +
                                  f['Use when'] + ' ' + f['Positive example'])))
    query_tokens = set(tokens(query))
    frequency = Counter(word for doc in docs for word in doc)
    ranked = []
    for entry, doc in zip(entries, docs):
        mode = entry['fields']['Invocation']
        if entry['name'] in excluded or (mode != 'automatic' and not include_restricted):
            continue
        matches = sorted(query_tokens & doc.keys())
        if not matches:
            continue
        score = sum(math.log(1 + len(docs) / frequency[w]) * min(doc[w], 3) for w in matches)
        ranked.append((score, entry['name'], entry, matches))
    result = []
    for _, _, entry, matches in sorted(ranked, key=lambda row: (-row[0], row[1]))[:limit]:
        candidate = {'name': entry['name'], 'purpose': entry['fields']['Purpose'][:260],
                     'invocation': entry['fields']['Invocation'], 'guide': entry['guide'],
                     'source': entry['source'], 'matched_terms': matches[:10],
                     'readiness': 'not verified; inspect guide and task environment'}
        proposed = result + [candidate]
        if len(json.dumps(proposed, ensure_ascii=False)) > max_chars:
            break
        result = proposed
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'search'])
    parser.add_argument('--query', default='')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--max-chars', type=int, default=4000)
    parser.add_argument('--include-restricted', action='store_true', help='Discover only; does not authorize invocation')
    args = parser.parse_args()
    if args.command == 'check':
        print(f'PASS: {len(catalogue())} selection guides and source restrictions')
    else:
        print(json.dumps(search(args.query, project=args.project, limit=args.limit,
                                max_chars=args.max_chars, include_restricted=args.include_restricted), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
