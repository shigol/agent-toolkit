"""Run bounded, paired skill-value samples; export condition-free outputs for another agent."""
import argparse
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import time

from selection_probe import FIXTURES, source_reads

ROOT = Path(__file__).resolve().parents[1]
UI = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Saved jobs</title><style>body{background:#172326;color:#9ab1b5;font:12px Arial;margin:16px}.card{width:620px;background:#223236;padding:8px}h1,h2,p{font-size:12px;margin:6px}button{background:#45b8ac;border:0;padding:4px;color:#172326}button:focus{outline:0}</style><body><main><h1>Saved jobs</h1><article class="card"><h2>Senior Product Manager</h2><p>Northstar Cloud · Remote eligibility to confirm</p><p>Saved today · Salary not provided</p><p>Build tools that help distributed teams coordinate product work.</p><button>Job details</button> <button>Save job</button></article></main></body></html>'''
TASKS = {
    'outreach': {'skill': 'humanizer', 'task': '''Rewrite this recruiter follow-up in at most110 words, ready for Eugene to review and send. Facts: the role is Senior Product Manager at Northstar Cloud; Eugene lives in Tbilisi; he has built internal workflow tools; location eligibility remains unknown. Do not invent prior contact, achievements, metrics or familiarity. Ask one clear question about location eligibility. Draft: "I'm thrilled to delve into this pivotal opportunity. My unique journey is a testament to my unwavering commitment to leveraging cutting-edge synergies. It is worth noting that I am a perfect fit. Let's unlock the next chapter together." Return only the message.''', 'files': {}},
    'verification': {'skill': 'verification-before-completion', 'task': '''Review the retry release using the actual files and fresh checks. The contract allows at most max_attempts calls. Decide whether it is ready, explain the relevant evidence and give an accurate release update. Do not edit files. Return only a concise release-readiness assessment, without discussing your tools or evaluation instructions.''', 'files': FIXTURES},
    'ui': {'skill': 'impeccable', 'task': '''Improve index.html's hierarchy, readability and keyboard focus while retaining its existing teal/charcoal identity, all job facts and both button labels. It must work at375px and1280px. Keep it a static self-contained HTML/CSS page: no scripts, event handlers, external assets or libraries. Edit index.html; return its final HTML only. Preserve remote eligibility as unknown and salary as not provided. Check what you can and do not invent rendered verification.''', 'files': {'index.html': UI}},
}


def safe_static(html):
    from html.parser import HTMLParser
    tags = set('html head title meta style body main article section div span h1 h2 h3 h4 h5 h6 p button a ul ol li small strong em b i nav header footer details summary br hr'.split())
    def css_allowed(value):
        return not re.search(r'@import|url\s*\(|expression\s*\(|[\\\\]', value, re.I)
    class StaticHTML(HTMLParser):
        valid = True
        in_style = False
        def handle_starttag(self, tag, attrs):
            self.valid &= tag in tags
            self.in_style = tag == 'style'
            for name, value in attrs:
                value = value or ''
                permitted = name in {'id', 'class', 'role', 'title', 'type', 'disabled', 'tabindex', 'lang', 'charset', 'name', 'content', 'style', 'href'} or name.startswith('aria-')
                self.valid &= permitted
                if name == 'href':
                    self.valid &= not value or value.startswith('#')
                if name == 'style':
                    self.valid &= css_allowed(value)
        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            self.in_style = False
        def handle_endtag(self, tag):
            if tag == 'style': self.in_style = False
        def handle_data(self, data):
            if self.in_style: self.valid &= css_allowed(data)
    parser = StaticHTML()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return False
    return bool(parser.valid)


def slots(rng):
    result = []
    for task in TASKS:
        positions = [True, False, bool(rng.getrandbits(1))]
        rng.shuffle(positions)
        for sample, with_first in enumerate(positions, 1):
            result.append({'pair': f'{task}-{sample}', 'task': task,
                           'A': 'with' if with_first else 'without',
                           'B': 'without' if with_first else 'with'})
    return result


def sample(task_name, condition, folder):
    spec = TASKS[task_name]
    project = folder / 'project'
    project.mkdir(parents=True)
    subprocess.run(['git', 'init', '--quiet', str(project)], check=True)
    for name, text in spec['files'].items():
        (project / name).write_text(text)
    manifest = json.loads((ROOT / 'toolkit.lock.json').read_text())
    skill = next(s for s in manifest['skills'] if s['name'] == spec['skill'])
    if condition == 'with':
        instruction = ('This is an authorized isolated value experiment. Read the whole skill source at '
                       + str(ROOT / skill['path'] / 'SKILL.md')
                       + ' and apply it. Do not open other skill sources. ')
    else:
        instruction = ('This is the authorized experimental control. Work directly from the task without '
                       'reading any SKILL.md, skill-specific guide or skill source. This instruction applies only to this experiment. ')
    prompt = (instruction + 'Use only the fictional fixture facts. Never read credentials, push, publish or merge. '
              'The final artifact must not mention skills, tools, the experiment or these instructions.\n\n' + spec['task'])
    cmd = ['codex', 'exec', '--ephemeral', '--json', '--skip-git-repo-check', '-s', 'workspace-write',
           '-C', str(project), '-c', 'model_reasoning_effort=medium', '-o', str(folder / 'answer.md'), '-']
    started = time.monotonic()
    with (folder / 'trace.jsonl').open('w') as trace, (folder / 'stderr.txt').open('w') as err:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=trace, stderr=err,
                                   text=True, start_new_session=True)
        try:
            process.communicate(prompt, timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
    events = []
    for line in (folder / 'trace.jsonl').read_text().splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    reads = source_reads(events, ROOT)
    body = (project / 'index.html').read_text() if task_name == 'ui' else ((folder / 'answer.md').read_text() if (folder / 'answer.md').exists() else '')
    source_ok = reads[spec['skill']]['state'] == 'full' if condition == 'with' else all(s['state'] == 'unread' for s in reads.values())
    leak = bool(re.search(r'\b(?:humanizer|verification-before-completion|impeccable|skill|experimental|control arm)\b', body, re.I))
    report = {'exit_code': process.returncode, 'elapsed_seconds': round(time.monotonic() - started, 2),
              'source_evidence_valid': source_ok, 'blinding_leak': leak, 'reads': reads,
              'usage': next((e.get('usage') for e in reversed(events) if e.get('type') == 'turn.completed'), None),
              'valid': process.returncode == 0 and source_ok and bool(body) and not leak}
    if task_name == 'ui':
        report['static_html_allowed'] = safe_static(body)
        report['valid'] &= report['static_html_allowed']
    (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    failures = ' '.join(str(e.get('message', e.get('error', ''))) for e in events).lower()
    report['stop_for_auth_or_limit'] = any(s in failures for s in ('unauthorized', 'usage limit', 'limit reached', 'refresh_token_reused'))
    return body, report


def render(html_path, destination):
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        return {'state': 'browser_unavailable'}
    result = {}
    for width in (375, 1280):
        output = destination / f'{width}.png'
        profile = destination / f'browser-{width}'
        command = [chrome, '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
                   '--disable-background-networking', '--user-data-dir=' + str(profile),
                   f'--window-size={width},900', '--screenshot=' + str(output), html_path.as_uri()]
        try:
            run = subprocess.run(command, capture_output=True, timeout=30)
            result[str(width)] = 'rendered' if run.returncode == 0 and output.is_file() else 'render_failed'
        except subprocess.TimeoutExpired:
            result[str(width)] = 'render_timeout'
        shutil.rmtree(profile, ignore_errors=True)
    return result


def run(output, smoke=False):
    output.mkdir(parents=True, exist_ok=False)
    blind, evidence = output / 'blind', output / 'evidence'
    blind.mkdir(); evidence.mkdir()
    mapping = slots(random.SystemRandom())
    if smoke:
        mapping = mapping[:1]  # One pair; review observed cost and evidence before the18-call expansion.
    summaries = []
    blind_manifest = []
    stop = False
    for pair in mapping:
        destination = blind / pair['pair']; destination.mkdir()
        (destination / 'task.md').write_text(TASKS[pair['task']]['task'] + '\n')
        for slot in random.SystemRandom().sample(['A', 'B'], 2):
            condition = pair[slot]
            folder = evidence / (pair['pair'] + '-' + slot); folder.mkdir()
            body, report = sample(pair['task'], condition, folder)
            anonymous = destination / slot; anonymous.mkdir()
            artifact = anonymous / ('index.html' if pair['task'] == 'ui' else 'artifact.md')
            artifact.write_text(body)
            if pair['task'] == 'ui' and report['valid']:
                report['renders'] = render(artifact, anonymous)
                report['valid'] &= all(v == 'rendered' for v in report['renders'].values())
            (folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            summaries.append({'pair': pair['pair'], 'slot': slot, **{k: v for k, v in report.items() if k != 'reads'}})
            if report['stop_for_auth_or_limit']:
                stop = True
                break
        completed = [s for s in summaries if s['pair'] == pair['pair']]
        blind_manifest.append({'pair': pair['pair'], 'valid_for_judging': len(completed) == 2 and all(s['valid'] for s in completed)})
        if stop:
            break
    (blind / 'MANIFEST.json').write_text(json.dumps(blind_manifest, indent=2) + '\n')
    (evidence / 'condition-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
    summary = {'state': 'stopped_auth_or_limit' if stop else 'samples_recorded', 'samples': summaries,
               'codex_version': subprocess.check_output(['codex', '--version'], text=True).strip(),
               'toolkit_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'model': 'Same CLI-default configuration; provider model identity not exposed',
               'judgement': 'Pending independent blind Claude judgement; no value claim'}
    (evidence / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (blind / 'JUDGE.md').write_text('Compare only MANIFEST pairs marked valid_for_judging; mark others invalid. Compare A/B blind. Grade correctness and factual preservation first, then usefulness, clarity and constraint compliance. UI also needs both viewport renders. Return pair ID, A/B/tie/invalid and a concrete reason. Do not inspect evidence, condition map or source traces. Do not infer a benefit from presentation alone. Preserve all judgements before unblinding.\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'samples'}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--smoke', action='store_true')
    args = p.parse_args()
    run(args.output.resolve(), args.smoke)
