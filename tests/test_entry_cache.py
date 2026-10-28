"""Fresh-checkout entry readability, authoritative regeneration and refusal of foreign edits."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_toolkit import toolkit
import entry_cache

AGENTS = ['codex', 'claude']


class EntryCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / 'project'
        self.project.mkdir()
        self.git('init', '--quiet')
        self.configure()
        self.data = toolkit.verify_sources()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.project), *args], text=True).strip()

    def configure(self, **kwargs):
        (self.project / '.agent-toolkit.json').write_text(json.dumps(
            {'schema': 1, 'groups': ['writing'], 'entry_cache': True, **kwargs}))

    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):
            toolkit.install(self.project, AGENTS)

    def plan(self):
        return entry_cache.prepare(toolkit.ROOT, self.project, self.data, toolkit.selection(self.project, self.data))

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'Reviewed generated fixture')

    def snapshot(self):
        return {str(p.relative_to(self.project)): ('link', os.readlink(p)) if p.is_symlink()
                else ('file', p.read_bytes()) for p in self.project.rglob('*')
                if '.git' not in p.relative_to(self.project).parts and (p.is_symlink() or p.is_file())}

    def test_fresh_git_clone_without_submodule_reads_both_full_entries_and_licenses(self):
        self.configure(groups=list(self.data['groups']))
        self.install()
        self.commit()
        clone = Path(self.tmp.name) / 'fresh clone'
        subprocess.run(['git', 'clone', '--quiet', '--no-recurse-submodules', str(self.project), str(clone)], check=True)
        self.assertFalse((clone / '.agent-toolkit').exists())
        manifest = json.loads((clone / '.agent-skill-cache/manifest.json').read_text())
        self.assertEqual(len(manifest['skills']), 30)
        for skill in self.data['skills']:
            canonical = (toolkit.ROOT / skill['path'] / 'SKILL.md').read_bytes()
            for agent in ('.agents', '.claude'):
                link = clone / agent / 'skills' / skill['name']
                self.assertEqual((link / 'SKILL.md').read_bytes(), canonical)
                self.assertTrue(link.resolve().is_relative_to(clone / '.agent-skill-cache'))
        for package in manifest['packages'].values():
            self.assertTrue(package['licenses'])
            for name in package['licenses']:
                self.assertEqual((clone / '.agent-skill-cache' / name).read_bytes(), (toolkit.ROOT / name).read_bytes())
        # Resource aliases become usable when the exact pinned runtime/source is available.
        (clone / '.agent-toolkit').symlink_to(toolkit.ROOT, target_is_directory=True)
        for name, target in manifest['links'].items():
            alias = clone / '.agent-skill-cache' / name
            self.assertEqual(alias.resolve(), (toolkit.ROOT / name).resolve())
            self.assertTrue(alias.exists())

    def test_legacy_migration_limit_and_local_skill_preservation(self):
        self.configure(entry_cache=False, groups=list(self.data['groups']), native_limit=3)
        self.install()
        local = self.project / '.claude/skills/project-only'
        local.mkdir(); (local / 'SKILL.md').write_text('Keep local instructions')
        self.configure(groups=list(self.data['groups']), native_limit=3)
        self.install()
        plan = self.plan()
        self.assertEqual(len(plan['manifest']['skills']), 3)
        self.assertEqual((local / 'SKILL.md').read_text(), 'Keep local instructions')
        self.assertEqual(len(list((self.project / '.agents/skills').iterdir())), 3)
        self.configure(entry_cache=False, groups=list(self.data['groups']), native_limit=3)
        self.install()
        self.assertFalse((self.project / '.agent-skill-cache').exists())
        self.assertEqual((local / 'SKILL.md').read_text(), 'Keep local instructions')

    def test_disabling_cache_for_one_agent_cannot_break_the_other_agent(self):
        self.install(); self.commit()
        self.configure(entry_cache=False)
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'both agents'):
            toolkit.install(self.project, ['codex'])
        self.assertEqual(before, self.snapshot())
        self.assertTrue((self.project / '.claude/skills/humanizer/SKILL.md').is_file())

    def test_one_agent_narrowing_or_path_move_cannot_break_untouched_agent(self):
        self.install(); self.commit()
        self.configure(groups=[])
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'both agents'):
            toolkit.install(self.project, ['codex'])
        self.assertEqual(before, self.snapshot())
        self.configure()
        data = copy.deepcopy(self.data)
        humanizer = next(s for s in data['skills'] if s['name'] == 'humanizer')
        humanizer['path'] = 'vendor/humanizer/moved'
        # Resolve desired source bytes without copying the whole library or changing vendor source.
        desired, files = entry_cache.expected(toolkit.ROOT, self.project, self.data, toolkit.selection(self.project, self.data))
        desired = copy.deepcopy(desired)
        desired['skills']['humanizer']['source'] = humanizer['path'] + '/SKILL.md'
        plan = self.plan(); plan['manifest'] = desired
        with patch.object(entry_cache, 'prepare', return_value=plan):
            with self.assertRaisesRegex(RuntimeError, 'both agents'):
                toolkit.preflight_install(self.project, ['codex'], data, toolkit.selection(self.project, data))
        self.assertTrue((self.project / '.claude/skills/humanizer/SKILL.md').is_file())

    def test_all_conflicts_preflight_before_cache_links_or_routes_change(self):
        conflict = self.project / '.claude/skills/humanizer'
        conflict.mkdir(parents=True); (conflict / 'SKILL.md').write_text('foreign')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'conflict'):
            self.install()
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.project / '.agent-skill-cache').exists())

    def test_modified_foreign_or_redirected_cache_refused_without_partial_changes(self):
        self.install(); self.commit()
        cached = self.project / '.agent-skill-cache/vendor/humanizer/skills/SKILL.md'
        original = cached.read_bytes()
        cached.write_bytes(original + b'foreign edit')
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Modified cached'):
            self.install()
        self.assertEqual(before, self.snapshot())
        cached.write_bytes(original)
        foreign = self.project / '.agent-skill-cache/unowned'
        foreign.write_text('Keep')
        with self.assertRaisesRegex(RuntimeError, 'Foreign cache'):
            self.install()
        foreign.unlink()
        link = next((self.project / '.agent-skill-cache' / name) for name in self.plan()['manifest']['links'])
        link.unlink(); link.symlink_to('/tmp')
        with self.assertRaisesRegex(RuntimeError, 'Modified cache reference'):
            self.install()

    def test_missing_owned_files_repaired_but_strict_ci_rejects_missing_or_untracked_cache(self):
        self.install()
        with self.assertRaisesRegex(RuntimeError, 'committed/tracked'):
            entry_cache.verify(self.plan(), tracked=True)
        self.commit(); entry_cache.verify(self.plan(), tracked=True)
        cached = self.project / '.agent-skill-cache/vendor/humanizer/skills/SKILL.md'
        cached.unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing or stale'):
            entry_cache.verify(self.plan(), tracked=True)
        self.install(); entry_cache.verify(self.plan(), tracked=True)
        (self.project / '.agent-skill-cache/manifest.json').unlink()
        self.install(); entry_cache.verify(self.plan(), tracked=True)

    def test_changed_and_new_skill_propagate_only_from_verified_source_selection(self):
        self.install(); self.commit()
        root = Path(self.tmp.name) / 'new source'
        data = copy.deepcopy(self.data)
        # Only fixture source bytes needed by the writing selection and its resource inventory.
        shutil.copytree(toolkit.ROOT / 'vendor/humanizer', root / 'vendor/humanizer')
        source = 'vendor/humanizer/skills/SKILL.md'
        (root / source).write_bytes((root / source).read_bytes() + b'\nFixture reviewed source update\n')
        data['files'][source] = entry_cache.sha((root / source).read_bytes())
        new = 'vendor/humanizer/new/SKILL.md'
        (root / new).parent.mkdir(); (root / new).write_text('New reviewed fixture skill\n')
        data['files'][new] = entry_cache.sha((root / new).read_bytes())
        data['skills'].append({'name': 'new-writing', 'package': 'humanizer', 'path': 'vendor/humanizer/new'})
        with patch.object(toolkit, 'ROOT', root), patch.object(toolkit, 'verify_sources', return_value=data):
            plan = entry_cache.prepare(root, self.project, data, toolkit.selection(self.project, data))
            with self.assertRaisesRegex(RuntimeError, 'stale'):
                entry_cache.verify(plan, tracked=True)
            self.install()
            for agent in ('.agents', '.claude'):
                self.assertEqual((self.project / agent / 'skills/new-writing/SKILL.md').read_bytes(), (root / new).read_bytes())
            self.commit()
            entry_cache.verify(plan, tracked=True)
            self.configure(exclude=['new-writing'])
            self.install()
            self.assertFalse(os.path.lexists(self.project / '.agents/skills/new-writing'))
            self.assertFalse((self.project / '.agent-skill-cache' / new).is_file())

    def test_identical_entry_bytes_do_not_churn_manifest_or_cache(self):
        self.install(); self.commit()
        before = self.snapshot()
        metadata = copy.deepcopy(self.data)
        for package in metadata['packages']:
            package['commit'] = 'f' * 40
        with patch.object(toolkit, 'verify_sources', return_value=metadata):
            self.install()
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_modified_ownership_manifest_cannot_authorize_overwriting_cached_text(self):
        self.install(); self.commit()
        base = self.project / '.agent-skill-cache'
        source = base / 'vendor/humanizer/skills/SKILL.md'
        source.write_text('foreign replacement')
        manifest = json.loads((base / 'manifest.json').read_text())
        manifest['files']['vendor/humanizer/skills/SKILL.md'] = entry_cache.sha(source.read_bytes())
        (base / 'manifest.json').write_bytes(entry_cache.encoded(manifest))
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, 'Modified/unowned'):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_foreign_symlink_cache_and_redirected_parents_are_never_followed(self):
        base = self.project / '.agent-skill-cache'
        base.symlink_to('missing-foreign')
        with self.assertRaisesRegex(RuntimeError, 'regular directory'):
            self.install()
        base.unlink()
        self.install(); self.commit()
        vendor = base / 'vendor'
        shutil.rmtree(vendor)
        vendor.symlink_to(toolkit.ROOT / 'vendor', target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'Redirected cache parent'):
            self.install()

    def test_atomic_generation_failure_restores_existing_cache(self):
        self.install(); self.commit()
        (self.project / '.agent-skill-cache/README.md').unlink()
        plan = self.plan()
        before = self.snapshot()
        original = Path.rename
        def fail_stage(path, destination):
            if '-stage-' in path.name:
                raise OSError('fixture rename failure')
            return original(path, destination)
        with patch.object(Path, 'rename', fail_stage), self.assertRaisesRegex(OSError, 'fixture rename'):
            entry_cache.apply(plan)
        self.assertEqual(before, self.snapshot())
