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

    def test_pattern_exception_only_for_short_prose_and_all_26_patterns(self):
        import re
        body = (audit.ROOT / 'vendor/humanizer/skills/SKILL.md').read_text()
        patterns = '\n'.join(re.findall(r'^### \d+\..+$', body, re.M))
        events = [event('rg "^###" .agents/skills/humanizer/SKILL.md', patterns)]
        self.assertTrue(audit.audit(events, 'Skills: humanizer', short_prose=True)['passed'])
        self.assertFalse(audit.audit(events, 'Skills: humanizer', short_prose=False)['passed'])
        self.assertFalse(audit.audit([event('rg "^###" .agents/skills/humanizer/SKILL.md', patterns[:200])], 'Skills: humanizer', short_prose=True)['passed'])
