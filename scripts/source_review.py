"""Report changed vendor-source review categories without printing source or secrets."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integrations/github'))
from toolkit_update import git, review_scan, safe_path


def scan(root, base, head='HEAD'):
    ancestor = git(root, 'merge-base', base, head)
    names = git(root, 'diff', '--name-only', '--no-renames', ancestor, head, '--', 'vendor').splitlines()
    rows = []
    for name in names:
        if not safe_path(name):
            raise ValueError('Invalid vendor review path')
        diff = git(root, 'diff', '--no-ext-diff', '--unified=0', ancestor, head, '--', name)
        added = '\n'.join(line[1:] for line in diff.splitlines()
                          if line.startswith('+') and not line.startswith('+++'))
        rows.append({'path': name, 'categories': review_scan(added)})
    totals = {name: sum(row['categories'][name] for row in rows)
              for name in review_scan('')}
    return {'review_required': bool(rows), 'files_scanned': len(rows), 'files': rows[:50],
            'files_omitted_from_output': max(0, len(rows) - 50), 'category_totals': totals,
            'meaning': 'Categories support independent review; they are not a safety verdict.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()
    result = scan(ROOT, args.base, args.head)
    output = json.dumps(result, indent=2)
    print(output)
    if args.summary:
        with args.summary.open('a') as handle:
            handle.write('\n### Vendor source review\n\n```json\n' + output + '\n```\n')
