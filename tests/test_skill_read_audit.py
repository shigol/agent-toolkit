from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_skill_reads as audit


def event(command, output, code=0):
    return {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': command,
            'aggregated_output': output, 'exit_code': code}}


class SkillAuditTests(unittest.TestCase):
    def test_empty_guide_failed_partial_and_unknown_do_not_verify_claims(self):
        text = (audit.ROOT / 'vendor/humanizer/skills/SKILL.md').read_text()
        for events in ([], [event('cat catalog/humanizer.md', text)],
                       [event('cat .agents/skills/humanizer/SKILL.md', text, 1)],
                       [event('head .agents/skills/humanizer/SKILL.md', text[:300])]):
            self.assertFalse(audit.audit(events, 'Skills: humanizer')['passed'])
        self.assertFalse(audit.audit([], 'Skills: pdf')['passed'])
        self.assertFalse(audit.audit([], 'no declaration')['passed'])
        self.assertFalse(audit.audit([], 'Skills: none (transport)\nSkills: humanizer')['passed'])

    def test_whole_source_and_no_skill_explanation(self):
        body = (audit.ROOT / 'vendor/humanizer/skills/SKILL.md').read_text()
        self.assertTrue(audit.audit([event('cat .agents/skills/humanizer/SKILL.md', body)], 'Skills: humanizer')['passed'])
        self.assertTrue(audit.audit([], 'Skills: none (arithmetic only)')['passed'])

    def test_headings_only_do_not_verify_pattern_body_reads(self):
        import re
        body = (audit.ROOT / 'vendor/humanizer/skills/SKILL.md').read_text()
        headings = '\n'.join(re.findall(r'^### \d+\..+$', body, re.M))
        events = [event('rg "^###" .agents/skills/humanizer/SKILL.md', headings)]
        result = audit.audit(events, 'Skills: humanizer', short_prose=True)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reads']['humanizer']['state'], 'partial')
        self.assertEqual(result['reads']['humanizer']['pattern_covered_unique_lines'], 26)
        self.assertGreater(result['reads']['humanizer']['pattern_total_unique_lines'], 26)
        events.append(event('cat .agents/skills/humanizer/SKILL.md', body, 1))
        self.assertFalse(audit.audit(events, 'Skills: humanizer', short_prose=True)['passed'])

    def test_complete_pattern_bodies_can_be_chunked_for_short_prose_only(self):
        body = (audit.ROOT / 'vendor/humanizer/skills/SKILL.md').read_text()
        patterns = '### 1.' + body.split('### 1.', 1)[1].split('\n## When not to act', 1)[0]
        lines = patterns.splitlines(keepends=True)
        events = [event('sed -n "59,158p" .agents/skills/humanizer/SKILL.md', ''.join(lines[:100])),
                  event('sed -n "159,382p" .agents/skills/humanizer/SKILL.md', ''.join(lines[100:]))]
        result = audit.audit(events, 'Skills: humanizer', short_prose=True)
        self.assertTrue(result['passed'])
        self.assertEqual(result['reads']['humanizer']['state'], 'short_prose_patterns')
        self.assertEqual(result['reads']['humanizer']['pattern_covered_unique_lines'],
                         result['reads']['humanizer']['pattern_total_unique_lines'])
        self.assertFalse(audit.audit(events, 'Skills: humanizer', short_prose=False)['passed'])
        for incomplete in (patterns[:patterns.index('\n**Problem:**')],
                           patterns.replace(lines[-1], '', 1)):
            self.assertFalse(audit.audit([event('cat .agents/skills/humanizer/SKILL.md', incomplete)],
                             'Skills: humanizer', short_prose=True)['passed'])
        for command, code in [('cat .agents/skills/humanizer/SKILL.md', 1), ('cat catalog/humanizer.md', 0)]:
            self.assertFalse(audit.audit([event(command, patterns, code)], 'Skills: humanizer', short_prose=True)['passed'])
