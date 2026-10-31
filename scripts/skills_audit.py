#!/usr/bin/env python3
"""Skills audit: does each commit's `Skills:` line match the SKILL.md files its session actually read? (EVG-124;
Eugene 2026-10-27: agents choose the right skills for every task; Probe 7 found a thread naming a skill it never opened.)

The nightly review (docs/nightly-review.md step 4d) runs it for the day that just ended:
    python3 tools/skills_audit.py sessions [--day YYYY-MM-DD] [--repo PATH ...]
        prints the Claude sessions (from commit trailers) whose transcripts to save: one `session_... <n commits>` per line
    python3 tools/skills_audit.py check --events DIR [--day YYYY-MM-DD] [--repo PATH ...]
        DIR holds <session id>.json per session: only the tool_use blocks whose input mentions skills/ or catalog/ (plus Skill
        tool calls) and their paired tool_result (IDs, is_error and complete selected-source output,
        at most 1 MiB per serialized result; preserve exit/truncation metadata), one JSON object per line, ending with {"has_more": false} once paging reached the session start, or
        {"has_more": false, "window_start": "<ISO time>"} once paging passed window_start (never whole pages: tokens).
        The window is the day's start in Tbilisi minus 2 hours (`window_start`, printed by `sessions`): long sessions
        need no paging back to their first day (10-28: one worker paged 2 of 13 sessions in 25 minutes)
    python3 tools/skills_audit.py stamp MSGFILE   (.githooks/commit-msg runs it on every Career commit)
        grades the commit's named skills from this session's own local transcript (~/.claude/projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl,
        events since window_start of today) and appends `Skills-Read: <name> <verdict>, ...` and `Skills-Window:` trailers.
        It refuses the commit (exit 1) only when a named skill is UNREAD, PARTIAL or GUIDE (10-29: 5 of 12 stamped names unread);
        errors and UNVERIFIED never block. `check` trusts a commit's Skills-Read trailer and `sessions` leaves out
        sessions whose commits are all stamped, so the nightly pages only unstamped sessions (10-28: paging 13 sessions did
        not fit 25 minutes). The trailer is computed evidence, not a proof against deliberate edits.
    python3 tools/skills_audit.py reports --events DIR [--save job-market/audit/skills/<day>-reports.txt]
        grades every saved session in DIR that posted a work report, with or without a commit (Probe 8, 10-28: fresh threads
        skipped a required read in 5 of 9 cases and named no Skills line, so the commit check never saw them). Besides the
        lines above, use report_record(FULL post_message text) to retain preview/chars/completion_claim; also save one
        {"edited": true|false|null} assessment across ALL tool calls, including Bash writes (null for ambiguous calls). A report of over 280 characters needs the
        humanizer pattern bodies; a report that claims done/fixed/passing/ready from a session that edited files also needs
        verification-before-completion. One `report` line per session, then the `skills_reports` summary.
    python3 tools/skills_audit.py selftest [--pinned-sources]
        deterministic offline fixtures always; --pinned-sources also checks actual pinned source objects with measured lengths
Default day: yesterday in Tbilisi; default repos: this one and ../eugene-s-job-hub when present. No network, no writes.

Each named skill prints one line:
  ok       successful paired output covers every unique nonblank pinned source line (humanizer pattern bodies also count)
  PARTIAL  successful matching output covers only part of the pinned source
  UNREAD   no successful paired matching source output in the saved evidence; input alone proves no read
  GUIDE    only the catalogue guide was read, not the SKILL.md: counts as unread
  account skills (docx, pdf, ...) require a paired successful Skill invocation; this does not prove source coverage
  a read whose tool result failed (error, file missing) is an attempt and does not count
  UNVERIFIED pinned source unavailable/unknown; no network fetch or installed-file substitution
  nolog    no transcript saved for that session
  partlog  the saved transcript stops before the session start or the window (paging ended while has_more was true,
           or its window_start is later than the day's window): page on, then rerun
Last line: `skills_audit day=D commits=N named=X read=Y partial=P unread=U` for the morning summary and the weekly line.
Exit 1 for UNREAD, GUIDE, PARTIAL, UNVERIFIED, nolog or partlog (or an empty reports collection).
Report metadata missing a full-message completion flag or known edit assessment is UNVERIFIED.
Commit checks use each commit's gitlink; reports use this checkout's committed HEAD pin. Regrading old logs is explicit,
not a rewrite of historical scores. This observes collector evidence; it is not a host enforcement or application proof.
"""
import datetime as dt, functools, hashlib, json, os, re, subprocess, sys

MAX_RESULT_BYTES = 1024 * 1024

ROOT = os.environ.get('SKILLS_AUDIT_PROJECT') or subprocess.run(
    ['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or os.getcwd()
ACCOUNT_SKILLS = {'docx', 'pdf', 'xlsx', 'pptx', 'dataviz', 'deep-research'}


def default_day():
    return (dt.datetime.now(dt.timezone(dt.timedelta(hours=4))) - dt.timedelta(days=1)).strftime('%Y-%m-%d')


def window_start(day):
    """Oldest event a collector must reach: the day's start in Tbilisi minus 2 hours (a read just before midnight still counts)."""
    try: return dt.datetime.fromisoformat(f'{day}T00:00:00+04:00') - dt.timedelta(hours=2)
    except ValueError: return None   # no valid day: only a full-session marker certifies


def default_repos():
    app = os.path.join(os.path.dirname(ROOT), 'eugene-s-job-hub')
    return [ROOT] + ([app] if os.path.isdir(os.path.join(app, '.git')) else [])


def skill_names(body):
    """Names on a message's `Skills:` line (not the subject), or None for none/missing."""
    line = re.search(r'^Skills:\s*(.+)$', body.split('\n', 1)[1] if '\n' in body else '', re.I | re.M)   # not the subject (a PR title)
    if not line or re.match(r'none\b', line.group(1), re.I): return None
    names = [n.strip().lower() for n in re.sub(r'\([^)]*\)', '', line.group(1)).replace(';', ',').split(',') if n.strip()]
    names = [n for n in names if not re.search(r'\snot (read|loaded|used|opened)\b', n)]   # "x not read" declares, never claims (10-29)
    return [re.sub(r'^.*?([^/\s]+)/skill\.md$', r'\1', n) for n in names]   # `.agents/skills/x/SKILL.md` names skill x (10-29)


def stamped(body):
    """{name: verdict} from a `Skills-Read:` trailer, or None when the commit was not stamped."""
    line = re.search(r'^Skills-Read:\s*(.+)$', body, re.M)
    if not line: return None
    out = {}
    for part in line.group(1).split(','):
        bits = part.split()
        if len(bits) == 2: out[bits[0].lower()] = bits[1]
    return out


def commits(repo, day):
    """-> [(sha, subject, session, [skill names] or None for none/missing)] for commits made on day (Tbilisi)."""
    out = subprocess.run(['git', '-C', repo, 'log', '--all', '--since', f'{day}T00:00:00+04:00',
                          '--until', f'{day}T23:59:59+04:00', '--format=%H%x1f%B%x1e'],
                         capture_output=True, text=True).stdout
    rows = []
    for rec in out.split('\x1e'):
        if '\x1f' not in rec: continue
        sha, body = rec.strip().split('\x1f', 1)
        ses = re.search(r'Claude-Session: \S*/(session_\w+)', body)
        if not ses: continue
        rows.append((sha[:8], body.splitlines()[0][:60], ses.group(1), skill_names(body)))
        STAMPS[sha[:8]] = stamped(body)
    return rows


STAMPS = {}   # short sha -> stamped(body) for the commits() rows read so far


def transcripts(session_id, home=None):
    """This session's own transcripts; scratch-project subagent transcripts (-tmp-...) are not the session's work."""
    import glob
    root = os.path.join(home or os.path.expanduser('~'), '.claude', 'projects')
    return sorted(p for p in glob.glob(os.path.join(root, '*', session_id + '.jsonl')) if not os.path.basename(os.path.dirname(p)).startswith('-tmp-'))


def codex_transcripts(session_id, home=None):
    """Exact current thread only; never infer identity from the newest transcript."""
    import glob
    if not re.fullmatch(r'[A-Za-z0-9_-]+', session_id): return []
    root = os.path.join(home, '.codex') if home else os.environ.get('CODEX_HOME', os.path.expanduser('~/.codex'))
    return sorted(glob.glob(os.path.join(root, 'sessions', '**', 'rollout-*-' + session_id + '.jsonl'), recursive=True))


def codex_events(obj):
    """Normalize paired rollout response items without accepting echoed input as output.

    Supports ordinary function tools and custom/code-mode calls. Unknown formats
    contribute no evidence. Only response_item records count, not event mirrors.
    """
    if obj.get('type') != 'response_item': return []
    item = obj.get('payload', {})
    kind, uid = item.get('type'), item.get('call_id')
    if not uid: return []
    if kind in ('function_call', 'custom_tool_call'):
        raw = item.get('arguments', item.get('input', ''))
        try: inp = json.loads(raw)
        except (ValueError, TypeError): inp = {'code': raw}
        return [{'type': 'tool_use', 'id': uid, 'name': item.get('name'), 'input': inp}]
    if kind in ('function_call_output', 'custom_tool_call_output'):
        output = item.get('output', '')
        # Code-mode envelopes contain input_text blocks with JSON-encoded shell
        # results. Decode their bodies, retaining exit/truncation metadata.
        def decode(value):
            if isinstance(value, list): return [decode(v) for v in value]
            if isinstance(value, dict):
                return {k: decode(v) for k, v in value.items()}
            if isinstance(value, str):
                try: return decode(json.loads(value))
                except ValueError:
                    lines = value.splitlines()
                    return [decode(line) for line in lines] if len(lines) > 1 else value
            return value
        content = decode(output)
        return [{'type': 'tool_result', 'tool_use_id': uid, 'content': content}]
    return []


def stamp(msgfile, session_id=None, home=None, now=None):
    """commit-msg hook: append Skills-Read/Skills-Window trailers graded from the local transcript; exit 1 for a named skill not read in full."""
    import tempfile
    session_id = session_id or os.environ.get('CLAUDE_CODE_SESSION_ID')
    codex = not session_id and bool(os.environ.get('CODEX_THREAD_ID'))
    if codex: session_id = os.environ['CODEX_THREAD_ID']
    body = open(msgfile, encoding='utf-8').read()
    names = skill_names(body)
    if not names or not session_id: return 0
    paths = codex_transcripts(session_id, home) if codex else transcripts(session_id, home)
    if not paths:
        print('skills stamp skipped: current session has no local transcript', file=sys.stderr)
        return 0
    now = now or dt.datetime.now(dt.timezone(dt.timedelta(hours=4)))
    since = window_start(now.strftime('%Y-%m-%d'))
    with tempfile.TemporaryDirectory() as d:
        kept = os.path.join(d, 'events.json')
        with open(kept, 'w', encoding='utf-8') as out:
            for p in paths:
                for line in open(p, encoding='utf-8'):
                    try: ts = json.loads(line).get('timestamp')
                    except (ValueError, AttributeError): continue
                    try: ok = ts and dt.datetime.fromisoformat(ts.replace('Z', '+00:00')) >= since
                    except (ValueError, TypeError): ok = False
                    if ok:
                        if codex:
                            for event in codex_events(json.loads(line)):
                                out.write(json.dumps(event) + '\n')
                        else: out.write(line)
        calls = tool_inputs(kept)
    catalog = sources(ROOT, 'HEAD')
    if any(n not in catalog and n not in ACCOUNT_SKILLS for n in names):
        # A fresh hosted checkout often lacks the pinned toolkit objects (10-29: 3 stamps UNVERIFIED); fetch them once.
        subprocess.run(['git', '-C', ROOT, 'submodule', 'update', '--init', '-q', '--', '.agent-toolkit'], capture_output=True, timeout=90)
        sources.cache_clear(); catalog = sources(ROOT, 'HEAD')
    graded = {n: verdict(n, calls, catalog) for n in names}
    keep = [l for l in body.rstrip('\n').split('\n') if not re.match(r'(Skills-Read|Skills-Window):', l)]
    trailer = ['Skills-Read: ' + ', '.join(f'{n} {v}' for n, v in graded.items()), 'Skills-Window: ' + since.isoformat()]
    open(msgfile, 'w', encoding='utf-8').write('\n'.join(keep + trailer) + '\n')
    bad = [f'{n} {v}' for n, v in graded.items() if v in ('UNREAD', 'PARTIAL', 'GUIDE')]
    if bad:
        # 10-29: 5 of 12 stamped names were never read and the commits went in anyway, so a false Skills line now stops the commit.
        print('skills: commit refused. The Skills line names skills this session did not read in full today: ' + ', '.join(bad) +
              '. Read each whole SKILL.md (Read or cat, no head/sed/grep cut), recheck the work against it, and commit again;'
              ' or, if you did not use it, take it off the Skills line (name only skills you read).', file=sys.stderr)
        return 1
    return 0


def objects(path):
    """Decode saved JSON objects, including older wrapped list_events extracts."""
    text = open(path, encoding='utf-8').read()
    dec, i = json.JSONDecoder(), 0
    while i < len(text):
        j = text.find('{', i)
        if j < 0: break
        try: obj, i = dec.raw_decode(text, j)
        except ValueError:
            i = j + 1; continue
        yield obj


def payload_blocks(obj):
    if isinstance(obj, str):
        try: obj = json.loads(obj)
        except ValueError: return
    if isinstance(obj, dict):
        yield obj
        for value in obj.values(): yield from payload_blocks(value)
    elif isinstance(obj, list):
        for value in obj: yield from payload_blocks(value)


def blocks(obj):
    if isinstance(obj, dict):
        yield obj
        # Inputs/result bodies are evidence, never additional transcript events.
        if obj.get('type') not in ('tool_use', 'tool_result'):
            for value in obj.values(): yield from blocks(value)
    elif isinstance(obj, list):
        for value in obj: yield from blocks(value)


def result_text(value):
    """Text payloads only: do not count an echoed input/command as source output."""
    if isinstance(value, str):
        try: decoded = json.loads(value)
        except ValueError: return value
        return result_text(decoded) if isinstance(decoded, (dict, list)) else value
    if isinstance(value, list): return '\n'.join(result_text(v) for v in value)
    if isinstance(value, dict):
        return '\n'.join(result_text(value[k]) for k in ('text', 'content', 'stdout', 'output', 'aggregated_output') if k in value)
    return ''


def usable_result(result):
    if result.get('is_error') or result.get('isError'): return False
    if len(json.dumps(result, ensure_ascii=False).encode('utf-8')) > MAX_RESULT_BYTES: return False
    # Explicit transport/process failures or truncation invalidate the entire result.
    for obj in payload_blocks(result.get('content')):
        if obj.get('is_error') or obj.get('isError') or obj.get('truncated') or obj.get('is_truncated') or obj.get('has_more'):
            return False
        if any(obj.get(k) not in (None, 0) for k in ('exit_code', 'exitCode', 'returncode')):
            return False
    if any(result.get(k) for k in ('truncated', 'is_truncated', 'has_more')): return False
    if any(result.get(k) not in (None, 0) for k in ('exit_code', 'exitCode', 'returncode')): return False
    body = result_text(result.get('content'))
    if re.search(r'(?im)^.*(?:output (?:was |has been )?truncated|truncated output|content (?:was )?truncated|truncated \d+|output exceeded|process exited with (?:code )?[1-9]|command failed with (?:status|code) [1-9]|exit (?:code|status)[: ]+[1-9]).*$', body):
        return False
    return (bool(body.strip()) or result.get('is_error') is False) and not (len(body) < 400 and re.search(r'No such file|does not exist|not found', body))


def tool_inputs(path):
    """Keep the existing list-of-JSON API, now with paired successful outputs.
    Missing IDs/results and conflicting duplicate IDs cannot establish a read.
    """
    uses, results = {}, {}
    for obj in objects(path):
        for b in blocks(obj):
            if b.get('type') == 'tool_use' and b.get('id'):
                uses.setdefault(b['id'], set()).add(json.dumps({'name': b.get('name'), 'input': b.get('input', {})}, sort_keys=True))
            if b.get('type') == 'tool_result' and b.get('tool_use_id'):
                results.setdefault(b['tool_use_id'], set()).add(json.dumps(b, sort_keys=True))
    out = []
    for uid, calls in uses.items():
        if len(calls) != 1 or len(results.get(uid, [])) != 1: continue
        result = json.loads(next(iter(results[uid])))
        if not usable_result(result): continue
        call = json.loads(next(iter(calls)))
        call['output'] = result_text(result.get('content'))
        call['paired_success'] = True
        out.append(json.dumps(call))
    return out


def complete(path, since=None):
    """Only an explicit final paging marker certifies a complete collection.
    A session ID alone, or has_more text echoed inside a tool result, proves nothing.
    A windowed marker counts only when its window_start is no later than `since` (the day's window_start).
    """
    try:
        lines = [line for line in open(path, encoding='utf-8') if line.strip()]
        last = json.loads(lines[-1]) if lines else None
        if last == {'has_more': False}: return True
        if not (isinstance(last, dict) and set(last) == {'has_more', 'window_start'} and last['has_more'] is False): return False
        start = dt.datetime.fromisoformat(str(last['window_start']).replace('Z', '+00:00'))
        return since is not None and start.tzinfo is not None and start <= since
    except (OSError, ValueError, TypeError, IndexError): return False


def git_blob(repo, ref, path):
    return subprocess.run(['git', '-C', repo, 'show', f'{ref}:{path}'], check=True, capture_output=True).stdout


@functools.lru_cache(maxsize=32)
def sources(repo=ROOT, ref='HEAD'):
    """Use committed consumer gitlink/manifest/blobs, never mutable installed files.
    Unavailable pinned objects stay unverified; the auditor never downloads sources.
    """
    found = {}
    try:
        tree = subprocess.run(['git', '-C', repo, 'ls-tree', ref, '.agent-toolkit'], check=True, capture_output=True, text=True).stdout
        mode, kind, pin = tree.split()[:3]
        if (mode, kind) != ('160000', 'commit'): raise ValueError('not a pinned toolkit')
        toolkit = os.path.join(repo, '.agent-toolkit')
        manifest = json.loads(git_blob(toolkit, pin, 'toolkit.lock.json'))
        for skill in manifest['skills']:
            path, name = skill['path'] + '/SKILL.md', skill['name']
            body = git_blob(toolkit, pin, path)
            if hashlib.sha256(body).hexdigest() != manifest['files'].get(path): continue
            found[name] = {'body': body.decode('utf-8'), 'aliases': [path, '.agent-skill-cache/' + path, f'.agents/skills/{name}/SKILL.md', f'.claude/skills/{name}/SKILL.md', f'{name}/SKILL.md']}
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        pass
    # Hosted sessions often cannot fetch the toolkit repo (10-29: 11 stamps UNVERIFIED). The consumer commits a pinned skill
    # cache with per-file sha256 (.agent-skill-cache/manifest.json); its blobs at the same ref are equally committed evidence.
    try:
        cache = json.loads(git_blob(repo, ref, '.agent-skill-cache/manifest.json'))
        for name, meta in cache['skills'].items():
            if name in found: continue
            path = meta['source']
            body = git_blob(repo, ref, '.agent-skill-cache/' + path)
            if hashlib.sha256(body).hexdigest() != meta['sha256'] or cache['files'].get(path) != meta['sha256']: continue
            found[name] = {'body': body.decode('utf-8'), 'aliases': [path, '.agent-skill-cache/' + path, f'.agents/skills/{name}/SKILL.md', f'.claude/skills/{name}/SKILL.md', f'{name}/SKILL.md']}
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        pass
    # Project-local procedures do not require the shared toolkit to be available.
    try:
        tree = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', ref, '--', '.agents/skills', '.claude/skills'], check=True, capture_output=True, text=True).stdout
        for row in tree.splitlines():
            meta, path = row.split('\t', 1)
            if meta.startswith('100') and path.endswith('/SKILL.md'):
                name = path.split('/')[-2]
                found.setdefault(name, {'body': git_blob(repo, ref, path).decode('utf-8'), 'aliases': [f'.agents/skills/{name}/SKILL.md', f'.claude/skills/{name}/SKILL.md', f'{name}/SKILL.md']})
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        pass
    return found


def unique_lines(body):
    return {line.strip() for line in body.splitlines() if line.strip()}


def pattern_lines(body):
    headings = list(re.finditer(r'^### (\d+)\..+$', body, re.M))
    if [int(h.group(1)) for h in headings] != list(range(1, 27)): return set()
    following = re.search(r'^## ', body[headings[-1].end():], re.M)
    end = headings[-1].end() + following.start() if following else len(body)
    return unique_lines(body[headings[0].start():end])


def verdict(name, inputs, catalog=None):
    calls = []
    for text in inputs:
        try: call = json.loads(text)
        except (ValueError, TypeError): continue
        if isinstance(call, dict) and call.get('paired_success') is True: calls.append(call)
    if name in ACCOUNT_SKILLS:
        # Account invocation evidence, not proof of a repo source read or application.
        return 'ok' if any(c.get('name') == 'Skill' and re.search(r'(?:^|:)' + re.escape(name) + r'$', str(c.get('input', {}).get('skill', ''))) for c in calls) else 'UNREAD'
    source = (sources() if catalog is None else catalog).get(name)
    if not source: return 'UNVERIFIED'
    hits = [c for c in calls if any(re.search(r'(?<![\w.-])' + re.escape(alias) + r'(?![\w./-])', json.dumps(c.get('input', {}))) for alias in source['aliases'])]
    if not hits:
        return 'GUIDE' if any(f'catalog/{name}.md' in json.dumps(c.get('input', {})) for c in calls) else 'UNREAD'
    # Read and nl/sed/grep outputs may carry line-number prefixes. Match complete
    # stripped source lines, not substrings, commands, or counts of headings.
    observed = set()
    for c in hits:
        observed.update(unique_lines(c.get('output', '')))
        observed.update(re.sub(r'^\s*L?\d+(?:[ ]*\t|[ ]*(?:→|:|\|)[ ]?)', '', line).strip() for line in c.get('output', '').splitlines() if line.strip())
    full = unique_lines(source['body'])
    patterns = pattern_lines(source['body']) if name == 'humanizer' else set()
    return 'ok' if (full and full <= observed) or (patterns and patterns <= observed) else 'PARTIAL'

DONE_RE = re.compile(r'\b(done|fixed|passing|passes|passed|ready|works|merged|complete)\b', re.I)


def report_record(message):
    """Collector helper: classify the FULL message before retaining its preview."""
    return {'report': message[:300], 'chars': len(message), 'completion_claim': bool(DONE_RE.search(message))}


def report_evidence(path):
    reps, assessments, issues = [], [], []
    for line in open(path):
        try: obj = json.loads(line)
        except ValueError: continue
        if not isinstance(obj, dict): continue
        if 'report' in obj: reps.append(obj)
        if 'edited' in obj: assessments.append(obj['edited'])
    if reps and (not assessments or any(type(v) is not bool for v in assessments)):
        issues.append('edited assessment missing/unknown')
    if True in assessments and False in assessments:
        issues.append('edited assessments conflict')
    completions, lengths = [], []
    for rep in reps:
        preview, chars, claim = rep['report'], rep.get('chars'), rep.get('completion_claim')
        if not isinstance(preview, str) or len(preview) > 300 or type(chars) is not int or chars < len(preview):
            issues.append('report preview/length incomplete'); continue
        lengths.append(chars)
        if type(claim) is not bool: issues.append('full-message completion flag missing/unknown')
        if claim is False and DONE_RE.search(preview): issues.append('completion flag contradicts preview')
        completions.append(claim is True or bool(DONE_RE.search(preview)))
    need = []
    if any(length > 280 for length in lengths): need.append('humanizer')
    if any(v is True for v in assessments) and any(completions): need.append('verification-before-completion')
    return need, len(reps), sorted(set(issues))


def report_needs(path):
    """Preserve the (needed names, report count) API; reports() also checks metadata."""
    return report_evidence(path)[:2]


def reports(events, day=None):
    since = window_start(day or default_day())
    n = {'sessions': 0, 'needed': 0, 'read': 0, 'missed': 0, 'nolog': 0, 'unverified': 0}
    if not os.path.isdir(events):
        print(f'nolog    {events}'); return 1
    for f in sorted(os.listdir(events)):
        if not f.endswith('.json'): continue
        p = os.path.join(events, f)
        need, nrep, issues = report_evidence(p)
        if not nrep: continue
        n['sessions'] += 1
        if not complete(p, since):
            n['nolog'] += 1; print(f'partlog  {f[:-5]}'); continue
        t = tool_inputs(p)
        res = {k: verdict(k, t) for k in need}
        n['needed'] += len(res); n['read'] += sum(v == 'ok' for v in res.values()); n['missed'] += sum(v != 'ok' for v in res.values())
        n['unverified'] += bool(issues)
        bad = [f'{k} {v}' for k, v in res.items() if v != 'ok']
        if issues: bad.append('report-evidence UNVERIFIED: ' + '; '.join(issues))
        print(f"report   {f[:-5]}  {'MISSED ' + ', '.join(bad) if bad else 'ok'}  ({nrep} reports; needs {', '.join(need) or 'nothing'})")
    print(f"skills_reports sessions={n['sessions']} needed={n['needed']} read={n['read']} missed={n['missed']} nolog={n['nolog']} unverified={n['unverified']}")
    return 1 if n['missed'] or n['nolog'] or n['unverified'] or not n['sessions'] else 0


def check(day, repos, events):
    rows = [(repo, r) for repo in repos for r in commits(repo, day)]
    n = {'named': 0, 'read': 0, 'partial': 0, 'unread': 0, 'nolog': 0, 'unverified': 0}
    cache, since = {}, window_start(day)
    for repo, (sha, subj, ses, names) in rows:
        for name in names or []:
            n['named'] += 1
            p = os.path.join(events, ses + '.json')
            if (STAMPS.get(sha) or {}).get(name):
                v = STAMPS[sha][name]
            elif not os.path.exists(p):
                v = 'nolog'
            elif not complete(p, since):
                v = 'partlog'
            else:
                if p not in cache: cache[p] = tool_inputs(p)
                v = verdict(name, cache[p], sources(repo, sha))
            n['unverified'] += v == 'UNVERIFIED'
            n['read'] += v == 'ok'; n['partial'] += v == 'PARTIAL'; n['unread'] += v in ('UNREAD', 'GUIDE'); n['nolog'] += v in ('nolog', 'partlog')
            print(f'{v:8} {sha} {name:32} {ses}  {subj}')
    print(f"skills_audit day={day} commits={len(rows)} named={n['named']} read={n['read']} partial={n['partial']} unread={n['unread']} nolog={n['nolog']} unverified={n['unverified']}")
    return 1 if n['partial'] or n['unread'] or n['nolog'] or n['unverified'] else 0


def selftest(pinned_sources=False):
    import contextlib, io, tempfile
    from unittest.mock import patch
    # Ordinary CI always uses fixed offline fixtures. Real integration checks below
    # measure the available pinned sources without freezing future vendor lengths.
    pinned_catalog = sources() if pinned_sources else None
    if pinned_sources:
        assert {'humanizer', 'verification-before-completion', 'impeccable'} <= pinned_catalog.keys(), 'initialize the pinned toolkit for --pinned-sources'
    patterns = []
    for i in range(1, 27):
        patterns += [f'### {i}. Fixture pattern'] + [f'Pattern {i} body line {j}: preserve this source evidence.' for j in range(6)]
    patterns += [f'Last pattern body {j}' for j in range(5)]
    human = '\n'.join([f'Introduction line {j}' for j in range(46)] + patterns + ['## When not to act'])
    catalog = {}
    for name, body in [('humanizer', human)] + [(name, '\n'.join(f'{name} source line {i}: require the complete result.' for i in range(size))) for name, size in [('verification-before-completion', 80), ('impeccable', 65), ('design-taste-frontend', 90)]]:
        path = 'vendor/taste/skills/SKILL.md' if name == 'design-taste-frontend' else f'vendor/{name}/skills/SKILL.md'
        catalog[name] = {'body': body, 'aliases': [path, '.agent-skill-cache/' + path, f'.agents/skills/{name}/SKILL.md', f'.claude/skills/{name}/SKILL.md', f'{name}/SKILL.md']}
    human = catalog['humanizer']['body']
    verification = catalog['verification-before-completion']['body']
    assert len(unique_lines(human)) == 234 and len(pattern_lines(human)) == 187
    assert len(unique_lines(verification)) == 80
    count = 0
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'session_x.json')
        def pair(name, output, uid='u1', tool='Read', **flags):
            inp = {'file_path': f'/r/.agents/skills/{name}/SKILL.md'} if tool == 'Read' else {'skill': name}
            return [{'type': 'tool_use', 'id': uid, 'name': tool, 'input': inp},
                    dict(type='tool_result', tool_use_id=uid, content=output, **flags)]
        def write(events, marker=True):
            with open(p, 'w') as f:
                for event in events + ([{'has_more': False}] if marker else []): f.write(json.dumps(event) + '\n')
            return tool_inputs(p)
        def grade(events, name='humanizer'):
            return verdict(name, write(events), catalog)

        # Fixed fixtures falsify headings/input/preview evidence independently of
        # legitimate future changes to the pinned public sources.
        assert grade(pair('humanizer', human)) == 'ok'; count += 1
        numbered_source = '1: actual source text\nSecond source line'
        numbered_catalog = {'verification-before-completion': dict(catalog['verification-before-completion'], body=numbered_source)}
        assert verdict('verification-before-completion', write(pair('verification-before-completion', numbered_source)), numbered_catalog) == 'ok'; count += 1
        numbered_formats = {'tab': '{i}\t{line}', 'padded-tab': '  {i:5d} \t{line}', 'arrow': '{i}→{line}', 'colon': 'L{i}: {line}', 'pipe': '{i}| {line}'}
        table_source = '| column | value |\n| --- | --- |\n| item | data |\n1: literal numeric source'
        table_catalog = {'verification-before-completion': dict(catalog['verification-before-completion'], body=table_source)}
        for label, fmt in numbered_formats.items():
            output = '\n'.join(fmt.format(i=i, line=line) for i, line in enumerate(table_source.splitlines(), 1))
            assert verdict('verification-before-completion', write(pair('verification-before-completion', output)), table_catalog) == 'ok', label
            count += 1
        events = pair('humanizer', human); events[0]['input']['file_path'] = '.agent-skill-cache/vendor/humanizer/skills/SKILL.md'
        assert grade(events) == 'ok'; count += 1
        assert verdict('humanizer', write(events), {}) == 'UNVERIFIED'; count += 1
        events[1]['content'] = human[:300]
        assert grade(events) == 'PARTIAL'; count += 1
        assert grade([{'ccr': {'data': pair('humanizer', human)}}]) == 'ok'; count += 1
        events = pair('humanizer', human); events[1]['is_error'] = True
        assert grade(events + [events[0]]) == 'UNREAD'; count += 1
        assert grade(pair('humanizer', '\n'.join(sorted(pattern_lines(human))))) == 'ok'; count += 1
        headings = '\n'.join(line for line in human.splitlines() if re.match(r'^### \d+\.', line))
        assert len(headings.splitlines()) == 26
        assert grade(pair('humanizer', headings)) == 'PARTIAL'; count += 1
        assert grade(pair('humanizer', human[:300])) == 'PARTIAL'; count += 1
        missing_last = pattern_lines(human) - {human[human.index('### 26.'):].split('## When not to act')[0].strip().splitlines()[-1].strip()}
        assert grade(pair('humanizer', '\n'.join(missing_last))) == 'PARTIAL'; count += 1
        assert grade(pair('humanizer', human)[:1]) == 'UNREAD'; count += 1
        assert grade(pair('humanizer', 'cat: file: No such file or directory', is_error=False)) == 'UNREAD'; count += 1
        for flag in ({'is_error': True}, {'truncated': True}, {'exit_code': 1}):
            assert grade(pair('humanizer', human, **flag)) == 'UNREAD'; count += 1
        events = pair('humanizer', human); events[1]['tool_use_id'] = 'other'
        assert grade(events) == 'UNREAD'; count += 1
        events = pair('humanizer', 'Read attempted'); events[0]['input']['echoed_source'] = human
        assert grade(events) == 'PARTIAL'; count += 1
        fake = pair('humanizer', human)
        assert grade([{'type': 'tool_use', 'id': 'outer', 'name': 'Other', 'input': {'events': fake}}]) == 'UNREAD'; count += 1
        assert verdict('humanizer', [json.dumps({'name': 'Read', 'input': {'file_path': '/r/.agents/skills/humanizer/SKILL.md'}})], catalog) == 'UNREAD'; count += 1
        for name in ('verification-before-completion', 'impeccable', 'design-taste-frontend'):
            for alias in catalog[name]['aliases']:
                events = pair(name, catalog[name]['body']); events[0]['input']['file_path'] = '/r/' + alias
                assert grade(events, name) == 'ok'; count += 1
            assert grade(pair(name, catalog[name]['body'][:300]), name) == 'PARTIAL'; count += 1
        # Complementary successful ranges can establish coverage; failed ranges cannot.
        mid = len(human.splitlines()) // 2
        chunks = human.splitlines()
        first, last = '\n'.join(chunks[:mid]), '\n'.join(chunks[mid:])
        assert grade(pair('humanizer', first) + pair('humanizer', last, uid='u2')) == 'ok'; count += 1
        assert grade(pair('humanizer', first) + pair('humanizer', last, uid='u2', is_error=True)) == 'PARTIAL'; count += 1
        numbered = '\n'.join(f'{i}\t{line}' for i, line in enumerate(human.splitlines(), 1))
        assert grade(pair('humanizer', [{'type': 'text', 'text': numbered}])) == 'ok'; count += 1
        assert grade(pair('humanizer', json.dumps({'content': human}))) == 'ok'; count += 1
        assert grade(pair('humanizer', human + '\nOutput was truncated')) == 'UNREAD'; count += 1
        assert grade(pair('humanizer', human + '\nWarning: truncated output (original token count: 9000)')) == 'UNREAD'; count += 1
        assert grade(pair('humanizer', json.dumps({'content': human, 'exit_code': 1}))) == 'UNREAD'; count += 1
        assert grade(pair('humanizer', 'x' * (MAX_RESULT_BYTES + 1))) == 'UNREAD'; count += 1
        events = pair('humanizer', human); events[0]['input']['file_path'] += '.bak'
        assert grade(events) == 'UNREAD'; count += 1
        events = pair('humanizer', 'Catalogue instructions'); events[0]['input']['file_path'] = '.agent-toolkit/catalog/humanizer.md'
        assert grade(events) == 'GUIDE'; count += 1
        assert verdict('unknown', [], catalog) == 'UNVERIFIED'; count += 1
        assert verdict('humanizer', write(pair('humanizer', human)), {}) == 'UNVERIFIED'; count += 1
        assert verdict('docx', [json.dumps({'name': 'Skill', 'input': {'skill': 'anthropic-skills:docx'}})]) == 'UNREAD'; count += 1
        assert grade(pair('anthropic-skills:docx', 'Skill loaded', tool='Skill'), 'docx') == 'ok'; count += 1
        assert grade(pair('anthropic-skills:docx', '', tool='Skill', is_error=False), 'docx') == 'ok'; count += 1
        assert grade(pair('anthropic-skills:docx', 'Skill failed', tool='Skill', is_error=True), 'docx') == 'UNREAD'; count += 1
        write(pair('humanizer', human)); assert complete(p); count += 1
        write([{'sessionId': 'x'}], marker=False); assert not complete(p); count += 1
        write([{'has_more': True}], marker=False); assert not complete(p); count += 1
        write(pair('humanizer', '{"has_more":false}'), marker=False); assert not complete(p); count += 1
        # Windowed collection (10-28): a marker that reached the day's window certifies it; a later one, or no day, does not.
        day_w = window_start('2026-10-28')
        def windowed(ts): write(pair('humanizer', human) + [{'has_more': False, 'window_start': ts}], marker=False)
        windowed('2026-10-27T17:55:00Z'); assert complete(p, day_w) and not complete(p); count += 1
        windowed('2026-10-27T18:00:00Z'); assert complete(p, day_w); count += 1
        windowed('2026-10-27T18:05:00Z'); assert not complete(p, day_w); count += 1
        windowed('2026-10-27T18:00:00'); assert not complete(p, day_w); count += 1
        write(pair('humanizer', human) + [{'has_more': False, 'window_start': '2026-10-27T17:00:00Z', 'x': 1}], marker=False); assert not complete(p, day_w); count += 1
        # Missing pinned blobs/checksum mismatches cannot be replaced by installed files.
        source_path = 'vendor/humanizer/skills/SKILL.md'
        body = human.encode('utf-8')
        manifest = {'skills': [{'name': 'humanizer', 'path': 'vendor/humanizer/skills'}], 'files': {source_path: hashlib.sha256(body).hexdigest()}}
        def fixture_blob(repo, ref, path):
            if path == 'toolkit.lock.json': return json.dumps(manifest).encode('utf-8')
            if path == source_path: return body
            raise OSError('no fixture for this path')
        with patch(__name__ + '.git_blob', side_effect=fixture_blob):
            sources.cache_clear(); assert sources()['humanizer']['body'] == human; count += 1
        def altered(repo, ref, path):
            value = fixture_blob(repo, ref, path)
            return value + b'changed' if path == source_path else value
        with patch(__name__ + '.git_blob', side_effect=altered):
            sources.cache_clear(); assert 'humanizer' not in sources(); count += 1
        sources.cache_clear()
        with patch(__name__ + '.git_blob', side_effect=OSError('unavailable')):
            assert not sources(); count += 1
        sources.cache_clear()
        # Both audit entrypoints fail on uncollected/incomplete evidence, not just misses.
        report = [report_record('Fixed retry test; all checks pass. ' + 'x' * 300), {'edited': True}]
        assert report_needs(p)[0] == []
        with contextlib.redirect_stdout(io.StringIO()), patch(__name__ + '.sources', return_value=catalog):
            assert reports(os.path.join(d, 'absent')) == 1; count += 1
            write(report + pair('humanizer', human) + pair('verification-before-completion', verification, uid='v'))
            assert report_needs(p)[0] == ['humanizer', 'verification-before-completion']
            assert reports(d) == 0; count += 1
            tail = report_record('x' * 301 + ' Fixed the retry.')
            assert tail['completion_claim'] is True and not DONE_RE.search(tail['report']); count += 1
            write([tail, {'edited': True}] + pair('humanizer', human))
            assert report_needs(p)[0] == ['humanizer', 'verification-before-completion']; count += 1
            assert reports(d) == 1; count += 1
            for metadata in ([{'report': 'Fixed.', 'chars': 6}, {'edited': True}], [report_record('On it.')], [report_record('On it.'), {'edited': None}], [dict(report_record('Fixed.'), completion_claim=False), {'edited': False}]):
                write(metadata + pair('humanizer', human) + pair('verification-before-completion', verification, uid='v'))
                assert reports(d) == 1; count += 1
            write([report_record('On it.'), {'edited': False}]); assert reports(d) == 0; count += 1
            write(report + pair('humanizer', headings))
            assert reports(d) == 1; count += 1
            write(report, marker=False); assert reports(d) == 1; count += 1
            sha = subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
            with patch(__name__ + '.commits', return_value=[(sha, 'fixture', 'session_x', ['humanizer'])]):
                assert check('fixture', [ROOT], os.path.join(d, 'absent')) == 1; count += 1
                assert check('fixture', [ROOT], d) == 1; count += 1
                write(pair('humanizer', human)); assert check('fixture', [ROOT], d) == 0; count += 1
                write(pair('humanizer', headings)); assert check('fixture', [ROOT], d) == 1; count += 1
            with patch(__name__ + '.commits', return_value=[(sha, 'fixture', 'session_x', ['unknown'])]):
                assert check('fixture', [ROOT], d) == 1; count += 1
            # Commit-time stamp (10-28): grades from this session's local transcript, today's window only, never -tmp- subagents.
            home = os.path.join(d, 'home'); sid = 'sid-fixture'
            def transcript(folder, rows):
                os.makedirs(os.path.join(home, '.claude', 'projects', folder), exist_ok=True)
                with open(os.path.join(home, '.claude', 'projects', folder, sid + '.jsonl'), 'w') as f:
                    for ts, event in rows: f.write(json.dumps({'timestamp': ts, 'message': {'content': [event]}}) + '\n')
            h, v_old, v_tmp = pair('humanizer', human), pair('verification-before-completion', verification, uid='v'), pair('verification-before-completion', verification, uid='t')
            transcript('-home-user', [('2026-10-28T09:00:00Z', h[0]), ('2026-10-28T09:00:01Z', h[1]), ('2026-10-27T10:00:00Z', v_old[0]), ('2026-10-27T10:00:01Z', v_old[1])])
            transcript('-tmp-scratch-project', [('2026-10-28T09:00:00Z', v_tmp[0]), ('2026-10-28T09:00:01Z', v_tmp[1])])
            msg = os.path.join(d, 'MSG')
            open(msg, 'w').write('Fix retry\n\nSkills: humanizer, verification-before-completion\n')
            noon = dt.datetime.fromisoformat('2026-10-28T12:00:00+04:00')
            with contextlib.redirect_stderr(io.StringIO()) as err:
                assert stamp(msg, sid, home, noon) == 1 and stamp(msg, sid, home, noon) == 1
            body = open(msg).read()
            assert stamped(body) == {'humanizer': 'ok', 'verification-before-completion': 'UNREAD'} and body.count('Skills-Read:') == 1; count += 1
            assert 'verification-before-completion UNREAD' in err.getvalue() and 'Skills-Window: 2026-10-27T22:00:00+04:00' in body; count += 1
            open(msg, 'w').write('Fix retry\n\nSkills: .agents/skills/humanizer/SKILL.md\n')
            assert stamp(msg, sid, home, noon) == 0 and stamped(open(msg).read()) == {'humanizer': 'ok'}; count += 1
            assert skill_names('x\n\nSkills: .claude/skills/verification-before-completion/SKILL.md, impeccable') == ['verification-before-completion', 'impeccable']; count += 1
            assert skill_names('x\n\nSkills: humanizer, verification-before-completion not loaded (measured)') == ['humanizer']; count += 1
            open(msg, 'w').write('Data\n\nSkills: none (data)\n'); stamp(msg, sid, home, noon); assert 'Skills-Read' not in open(msg).read(); count += 1
            STAMPS[sha] = {'humanizer': 'ok'}
            with patch(__name__ + '.commits', return_value=[(sha, 'fixture', 'session_x', ['humanizer'])]):
                assert check('fixture', [ROOT], os.path.join(d, 'absent')) == 0; count += 1
            STAMPS[sha] = {'humanizer': 'PARTIAL'}
            with patch(__name__ + '.commits', return_value=[(sha, 'fixture', 'session_x', ['humanizer'])]):
                assert check('fixture', [ROOT], os.path.join(d, 'absent')) == 1; count += 1
            STAMPS.pop(sha)
        if pinned_sources:
            integration_count = 0
            for name in ('humanizer', 'verification-before-completion', 'impeccable'):
                body = pinned_catalog[name]['body']
                assert unique_lines(body), 'pinned source must be nonempty'
                assert verdict(name, write(pair(name, body)), pinned_catalog) == 'ok'; integration_count += 1
                assert verdict(name, write(pair(name, body)[:1]), pinned_catalog) == 'UNREAD'; integration_count += 1
                assert verdict(name, write(pair(name, body, is_error=True)), pinned_catalog) == 'UNREAD'; integration_count += 1
                assert verdict(name, write(pair(name, body, truncated=True)), pinned_catalog) == 'UNREAD'; integration_count += 1
                assert verdict(name, write(pair(name, '', is_error=False)), pinned_catalog) == 'PARTIAL'; integration_count += 1
            for name, source in sorted(pinned_catalog.items()):
                body = source['body']
                assert verdict(name, write(pair(name, body)), pinned_catalog) == 'ok', name + ' raw'
                integration_count += 1
                for label, fmt in numbered_formats.items():
                    output = '\n'.join(fmt.format(i=i, line=line) for i, line in enumerate(body.splitlines(), 1))
                    assert verdict(name, write(pair(name, output)), pinned_catalog) == 'ok', name + ' ' + label
                    integration_count += 1
            actual_patterns = pattern_lines(pinned_catalog['humanizer']['body'])
            if actual_patterns:
                assert verdict('humanizer', write(pair('humanizer', '\n'.join(sorted(actual_patterns)))), pinned_catalog) == 'ok'; integration_count += 1
            print(f"skills_audit pinned integration ok ({integration_count} cases; {len(pinned_catalog)} pinned skills × raw/5 numbered formats; Humanizer {len(unique_lines(pinned_catalog['humanizer']['body']))} full / {len(actual_patterns)} recognized pattern lines, verification {len(unique_lines(pinned_catalog['verification-before-completion']['body']))})")
    print(f"skills_audit selftest ok ({count} cases; offline synthetic fixtures; Humanizer 234 full / 187 pattern lines, verification 80)")

def main(a):
    if a[:1] == ['selftest']: return selftest('--pinned-sources' in a)
    day = a[a.index('--day') + 1] if '--day' in a else default_day()
    repos = [a[i + 1] for i, x in enumerate(a) if x == '--repo'] or default_repos()
    if a[:1] == ['sessions']:
        seen = {}
        for repo in repos:
            for sha, _, ses, names in commits(repo, day):
                if names and not all((STAMPS.get(sha) or {}).get(n) for n in names): seen[ses] = seen.get(ses, 0) + 1
        for s, c in sorted(seen.items()): print(s, c, f'window_start={window_start(day).isoformat()}')
        return 0
    if a[:1] == ['stamp'] and len(a) > 1:
        try: return stamp(a[1])
        except Exception as e:   # a hook must never stop a commit
            print(f'skills stamp skipped: {e}', file=sys.stderr); return 0
    if a[:1] == ['reports'] and '--events' in a:
        save = a[a.index('--save') + 1] if '--save' in a else None
        if not save: return reports(a[a.index('--events') + 1], day)
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): code = reports(a[a.index('--events') + 1], day)
        os.makedirs(os.path.dirname(save) or '.', exist_ok=True)
        open(save, 'w').write(buf.getvalue()); print(buf.getvalue(), end='')
        return code
    if a[:1] == ['check'] and '--events' in a:
        return check(day, repos, a[a.index('--events') + 1])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
