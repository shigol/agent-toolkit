"""Compile project routing instructions from reviewed catalogue metadata."""
from collections import defaultdict
from skills import catalogue

START = '<!-- skill-routes:start -->'
END = '<!-- skill-routes:end -->'


def block(root, selected):
    entries = {entry['name']: entry for entry in catalogue(root)}
    automatic, restricted = defaultdict(list), defaultdict(list)
    for skill in selected:
        name = skill['name']
        entry = entries[name]
        target = automatic if entry['fields']['Invocation'] == 'automatic' else restricted
        restriction = entry['fields']['Invocation']
        route = entry['fields']['Route']
        if restriction == 'explicit-only':
            route = 'Only on explicit skill name, ' + route
        elif restriction == 'explicit-direction':
            route = 'Explicit alternative direction only, ' + route
        target[route].append(name)
    lines = [START,
             'Before edits/drafts, fully read matching SKILL.md; one primary UI workflow. '
             'Missing coverage: .agent-toolkit/catalog/README.md, then search. Project rules/templates win. '
             'Humanizer: read ### sections with bodies for work reports; full source for docs/outside messages. Keep facts/quotes/evidence.']
    for route, names in automatic.items():
        lines.append('- ' + route + ': ' + ', '.join(names))
    for route, names in restricted.items():
        lines.append('- ' + route + ': ' + ', '.join(names))
    lines += ['Sources: .agents/skills/<name>/SKILL.md or .claude/skills/<name>/SKILL.md; '
              'else guide Source. Missing: bash tools/setup-agent-toolkit.sh --skills-only. Honor exclusions.',
              'Commit/PR: Skills: <sources read this task> or Skills: none (<why>).', END]
    return '\n'.join(lines) + '\n'


def replace_block(text, generated):
    """Move the owned block to the top, preserving every byte outside it."""
    starts, ends = text.count(START), text.count(END)
    if starts != ends or starts > 1:
        raise ValueError('Repeated or incomplete skill-routes markers')
    if starts:
        start, end = text.index(START), text.index(END)
        if end < start:
            raise ValueError('Reversed skill-routes markers')
        end += len(END)
        if text[end:end + 1] == '\n':
            end += 1
        if start == 0:
            return generated + text[end:]
        return generated + text[:start] + text[end:]
    return generated + text


def plan_updates(root, project, selected, agents, existing_only=False):
    """Preflight both headers before any write; installer only adopts existing markers."""
    paths = [project / ('AGENTS.md' if agent == 'codex' else 'CLAUDE.md') for agent in agents]
    updates = []
    generated = None
    for path in dict.fromkeys(paths):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Route header must be a regular file: ' + str(path))
        text = path.read_text() if path.exists() else ''
        if existing_only and START not in text and END not in text:
            continue
        if generated is None:
            generated = block(root, selected)
        result = replace_block(text, generated)
        if result != text:
            updates.append((path, result))
    return updates


def write_updates(updates):
    # Do not follow symlinks or replace unrelated files. Content preflight is done above.
    for path, text in updates:
        if path.is_symlink():
            raise ValueError('Route header became a symlink: ' + str(path))
        path.write_text(text)


