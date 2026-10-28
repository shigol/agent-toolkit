"""Fixed, fictional cloud acceptance worker; no model, credentials or external API calls."""
import json
from pathlib import Path
import re
import sys

from codex_task_run import run


def main(brief, request, output):
    match = re.fullmatch(r'continuity-\d+-\d+-([12])', request)
    if not match:
        raise ValueError('This fixture requires a reserved continuity attempt')
    attempt = int(match.group(1))
    names = {
        'docs/continuity-fixtures/success.md': 'success',
        'docs/continuity-fixtures/fail-once.md': 'fail-once',
        'docs/continuity-fixtures/always-fail.md': 'always-fail',
        'docs/continuity-fixtures/timeout-partial.md': 'timeout-partial',
    }
    mode = names.get(brief)
    if mode is None:
        raise ValueError('Only the fixed harmless fixture briefs are supported')
    if mode == 'timeout-partial':
        source = "from pathlib import Path;import time;Path('docs/continuity-fixtures/partial-result.txt').write_text('Fictional partial checkpoint, retained before the deadline.\\n');print('partial saved',flush=True);time.sleep(30)"
        return run([sys.executable, '-u', '-c', source], output, seconds=1, stale_seconds=5, interval=.2)
    fail = mode == 'always-fail' or (mode == 'fail-once' and attempt == 1)
    source = "import json;print(json.dumps({'type':'turn.completed','usage':{'input_tokens':0,'output_tokens':0}}));raise SystemExit(" + ('1' if fail else '0') + ')'
    return run([sys.executable, '-u', '-c', source], output, seconds=10, stale_seconds=5, interval=.2)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1], sys.argv[2], Path(sys.argv[3])))
