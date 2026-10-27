"""Compare declared shared-skill use with successful Codex CLI command output."""
import argparse
import json
from pathlib import Path
import re

from selection_probe import source_reads

ROOT = Path(__file__).resolve().parents[1]


def audit(events, answer, root=ROOT, short_prose=False):
    reads = source_reads(events, root)
    declarations = re.findall(r'^\s*(?:\*\*)?Skills:(?:\*\*)?\s*(.+)$', answer, re.M | re.I)
    claims = []
    none = False
    for declaration in declarations:
        if re.match(r'none\s*\(', declaration, re.I):
            none = True
        else:
            claims.extend(s.strip().strip('` .') for s in re.split(r'[,;]', declaration) if s.strip())
    claims = sorted(set(claims))
    manifest = json.loads((root / 'toolkit.lock.json').read_text())
    humanizer = next(s for s in manifest['skills'] if s['name'] == 'humanizer')
    if short_prose and reads['humanizer']['state'] == 'partial':
        headings = re.findall(r'^### \d+\..+$', (root / humanizer['path'] / 'SKILL.md').read_text(), re.M)
        outputs = '\n'.join(row.get('item', {}).get('aggregated_output', '') for row in events
                            if row.get('type') == 'item.completed'
                            and row.get('item', {}).get('type') == 'command_execution'
                            and row.get('item', {}).get('exit_code') == 0
                            and 'SKILL.md' in row['item'].get('command', '')
                            and (humanizer['path'] in row['item']['command']
                                 or 'skills/humanizer/' in row['item']['command']))
        if len(headings) == 26 and all(heading in outputs for heading in headings):
            reads['humanizer']['state'] = 'short_prose_patterns'
    insufficient = [name for name in claims if name in reads and reads[name]['state'] not in ('full', 'short_prose_patterns')]
    unknown = [name for name in claims if name not in reads]
    declared = bool(declarations) and not (none and claims)
    return {'declared': declared, 'claims': claims, 'insufficient_shared_reads': insufficient,
            'unverifiable_names': unknown, 'reads': reads,
            'passed': declared and not insufficient and not unknown,
            'scope': 'Successful CLI command output and answer declarations only. Selection quality, application, commit attribution and output value require separate checks.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace', type=Path, required=True)
    p.add_argument('--answer', type=Path, required=True)
    p.add_argument('--short-prose', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    events = [json.loads(line) for line in args.trace.read_text().splitlines() if line.strip()]
    report = audit(events, args.answer.read_text(), short_prose=args.short_prose)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'reads'}))
