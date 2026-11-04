"""Network-free cleanup checks using real local refs and a fake GitHub API."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'cleanup_merged.py'
spec = importlib.util.spec_from_file_location('cleanup_merged', SCRIPT)
cleanup_merged = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup_merged)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.work = self.root / 'work'
        self.bare = self.root / 'remote.git'
        self.git('init', '--bare', str(self.bare), cwd=self.root)
        self.git('init', '-b', 'main', str(self.work), cwd=self.root)
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.work / 'file').write_text('base\n')
        self.git('add', 'file')
        self.git('commit', '-m', 'base')
        self.git('remote', 'add', 'origin', str(self.bare))
        self.git('push', 'origin', 'main')
        self.git('switch', '-c', 'ticket')
        (self.work / 'file').write_text('base\nchange\n')
        self.git('commit', '-am', 'change')
        self.sha = self.git('rev-parse', 'HEAD')
        self.git('push', 'origin', 'ticket')
        self.git('switch', 'main')
        self.repo = {'default_branch': 'main'}
        self.pull = {
            'merged': True,
            'merged_at': '2026-01-01T00:00:00Z',
            'head': {'ref': 'ticket', 'sha': self.sha, 'repo': {'full_name': 'owner/repo'}},
            'base': {'ref': 'main', 'repo': {'full_name': 'owner/repo'}},
        }
        self.calls = []
        self.url = 'https://github.com/owner/repo.git'
        self.push_url = self.url
        self.before_push = None
        self.before_local_delete = None
        self.after_push = None
        self.after_branch_read = None
        self.protection = {'protected': False}

    def git(self, *args, cwd=None):
        result = subprocess.run(['git', *args], cwd=cwd or self.work, text=True, capture_output=True)
        if result.returncode:
            raise cleanup_merged.CleanupError(result.stderr.strip())
        return result.stdout.strip()

    def execute(self, argv):
        self.calls.append(argv)
        if argv[0] == 'gh':
            self.assertEqual(argv[:4], ['gh', 'api', '--hostname', 'github.com'])
            endpoint = argv[4]
            if '/branches/' in endpoint:
                if self.after_branch_read:
                    self.after_branch_read()
                return json.dumps(self.protection)
            return json.dumps(self.pull if '/pulls/' in endpoint else self.repo)
        if argv[:3] == ['git', 'remote', 'get-url']:
            return self.push_url if '--push' in argv else self.url
        if argv[:2] == ['git', 'push'] and self.before_push:
            self.before_push()
        if argv[:2] == ['git', 'update-ref'] and '-d' in argv and self.before_local_delete:
            self.before_local_delete()
        result = self.git(*argv[1:])
        if argv[:2] == ['git', 'push'] and self.after_push:
            self.after_push()
        return result

    def clean(self, **kwargs):
        return cleanup_merged.cleanup('owner/repo', 12, released=True, execute=self.execute, **kwargs)

    def local_exists(self):
        return bool(self.git('for-each-ref', '--format=%(refname)', 'refs/heads/ticket'))

    def remote_exists(self):
        return bool(self.git('ls-remote', '--heads', 'origin', 'refs/heads/ticket'))

    def assert_preserved(self):
        self.assertTrue(self.local_exists())
        self.assertTrue(self.remote_exists())
        self.assertFalse(any(c[:2] == ['git', 'push'] for c in self.calls))
        self.assertFalse(any(c[:2] == ['git', 'update-ref'] and '-d' in c for c in self.calls))

    def test_dry_run_preserves_both_refs(self):
        self.assertIn('Dry run', self.clean())
        self.assert_preserved()

    def test_requires_coordinator_release(self):
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'released'):
            cleanup_merged.cleanup('owner/repo', 12, apply=True, execute=self.execute)
        self.assert_preserved()

    def test_unmerged_pr_preserves_refs(self):
        self.pull['merged'] = False
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'merged'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_missing_merge_timestamp_preserves_refs(self):
        self.pull['merged_at'] = None
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'merged'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_wrong_remote_or_fork_preserves_refs(self):
        for attr in ('url', 'push_url'):
            old = getattr(self, attr)
            setattr(self, attr, 'git@github.com:other/repo.git')
            with self.assertRaisesRegex(cleanup_merged.CleanupError, 'match'):
                self.clean(apply=True)
            setattr(self, attr, old)
        self.pull['head']['repo']['full_name'] = 'fork/repo'
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'same-repository'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_protected_branch_preserves_refs(self):
        self.repo['default_branch'] = 'ticket'
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'Protected'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_long_lived_and_base_branches_are_preserved(self):
        for branch in ('main', 'master', 'develop', 'release', 'release/1.0', 'staging', 'integration'):
            with self.subTest(branch=branch):
                self.pull['head']['ref'] = branch
                if branch == 'integration':
                    self.pull['base']['ref'] = branch
                with self.assertRaisesRegex(cleanup_merged.CleanupError, 'Protected'):
                    self.clean(apply=True)
        self.assert_preserved()

    def test_custom_protected_branch_preserves_refs(self):
        self.protection['protected'] = True
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'protected'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_unknown_or_invalid_protection_preserves_refs(self):
        for protection in (None, [], {}, {'protected': None}, {'protected': 0}, {'protected': 'false'}):
            with self.subTest(protection=protection):
                self.protection = protection
                with self.assertRaisesRegex(cleanup_merged.CleanupError, 'protection is unknown'):
                    self.clean(apply=True)
        self.assert_preserved()

    def test_branch_protection_api_failure_preserves_refs(self):
        def fail():
            raise cleanup_merged.CleanupError('HTTP 403')
        self.after_branch_read = fail
        with self.assertRaisesRegex(cleanup_merged.CleanupError, '403'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_symbolic_branch_cannot_delete_main_or_remote(self):
        self.git('merge', '--ff-only', 'ticket')
        self.git('update-ref', '-d', 'refs/heads/ticket')
        self.git('symbolic-ref', 'refs/heads/ticket', 'refs/heads/main')
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'symbolic ref'):
            self.clean(apply=True)
        self.assertEqual(self.git('rev-parse', 'main'), self.sha)
        self.assert_preserved()

    def test_symbolic_alias_introduced_at_delete_cannot_dereference_main(self):
        self.git('merge', '--ff-only', 'ticket')
        def introduce_alias():
            self.git('update-ref', '-d', 'refs/heads/ticket')
            self.git('symbolic-ref', 'refs/heads/ticket', 'refs/heads/main')
        self.before_local_delete = introduce_alias
        try:
            self.clean(apply=True)
        except cleanup_merged.CleanupError:
            pass  # A safe compare failure is also acceptable.
        self.assertEqual(self.git('rev-parse', 'main'), self.sha)
        deletes = [c for c in self.calls if c[:2] == ['git', 'update-ref'] and '-d' in c]
        self.assertEqual(len(deletes), 1)
        self.assertIn('--no-deref', deletes[0])

    def test_branch_api_path_encodes_slashes(self):
        self.git('branch', '-m', 'ticket', 'ticket/child')
        self.git('--git-dir', str(self.bare), 'update-ref', '-d', 'refs/heads/ticket')
        self.git('push', 'origin', 'ticket/child')
        self.pull['head']['ref'] = 'ticket/child'
        self.assertIn('Dry run', self.clean())
        self.assertTrue(any(c[-1] == 'repos/owner/repo/branches/ticket%2Fchild' for c in self.calls))

    def test_github_host_is_explicit_for_every_api_request(self):
        self.clean()
        calls = [c for c in self.calls if c[0] == 'gh']
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(c[:4] == ['gh', 'api', '--hostname', 'github.com'] for c in calls))

    def test_late_checkout_before_remote_deletion_preserves_refs(self):
        self.after_branch_read = lambda: self.git('switch', 'ticket')
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'worktree'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_late_checkout_after_remote_deletion_preserves_local(self):
        self.after_push = lambda: self.git('switch', 'ticket')
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'Remote branch deleted; local cleanup skipped'):
            self.clean(apply=True)
        self.assertTrue(self.local_exists())
        self.assertFalse(self.remote_exists())
        self.assertFalse(any(c[:2] == ['git', 'update-ref'] and '-d' in c for c in self.calls))

    def test_current_branch_preserves_refs(self):
        self.git('switch', 'ticket')
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'worktree'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_linked_worktree_preserves_refs_and_files(self):
        linked = self.root / 'linked'
        self.git('worktree', 'add', str(linked), 'ticket')
        (linked / 'untracked').write_text('preserve me')
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'worktree'):
            self.clean(apply=True)
        self.assertEqual((linked / 'untracked').read_text(), 'preserve me')
        self.assert_preserved()

    def test_local_advanced_preserves_refs(self):
        self.git('update-ref', 'refs/heads/ticket', self.git('rev-parse', 'main'))
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'Local branch'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_remote_advanced_preserves_refs(self):
        self.git('--git-dir', str(self.bare), 'update-ref', 'refs/heads/ticket', self.git('rev-parse', 'main'))
        with self.assertRaisesRegex(cleanup_merged.CleanupError, 'Remote branch'):
            self.clean(apply=True)
        self.assert_preserved()

    def test_normal_merge_deletes_exact_refs(self):
        self.git('merge', '--no-ff', 'ticket', '-m', 'merge')
        self.assertIn('Deleted', self.clean(apply=True))
        self.assertFalse(self.local_exists())
        self.assertFalse(self.remote_exists())

    def test_squash_merge_and_repeat_are_safe(self):
        self.git('merge', '--squash', 'ticket')
        self.git('commit', '-m', 'squash')
        # PR head is not an ancestor of main: ordinary git branch -d would fail.
        self.assertNotEqual(self.git('rev-parse', 'main'), self.sha)
        self.assertIn('Deleted', self.clean(apply=True))
        self.assertFalse(self.local_exists())
        self.assertFalse(self.remote_exists())
        self.assertIn('Already absent', self.clean(apply=True))

    def test_already_deleted_remote_still_cleans_local(self):
        self.git('--git-dir', str(self.bare), 'update-ref', '-d', 'refs/heads/ticket')
        self.assertIn('Deleted', self.clean(apply=True))
        self.assertFalse(self.local_exists())

    def test_remote_lease_race_preserves_local_ref(self):
        newer = self.git('rev-parse', 'main')
        self.before_push = lambda: self.git('--git-dir', str(self.bare), 'update-ref', 'refs/heads/ticket', newer)
        with self.assertRaises(cleanup_merged.CleanupError):
            self.clean(apply=True)
        self.assertTrue(self.local_exists())
        self.assertEqual(self.git('--git-dir', str(self.bare), 'rev-parse', 'ticket'), newer)

    def test_local_compare_and_delete_race_preserves_new_ref(self):
        newer = self.git('rev-parse', 'main')
        self.before_local_delete = lambda: self.git('update-ref', 'refs/heads/ticket', newer)
        with self.assertRaises(cleanup_merged.CleanupError):
            self.clean(apply=True)
        self.assertEqual(self.git('rev-parse', 'ticket'), newer)
        self.assertFalse(self.remote_exists())

    def test_other_branch_with_same_prefix_is_preserved(self):
        self.git('update-ref', '-d', 'refs/heads/ticket')
        self.git('update-ref', 'refs/heads/ticket/next', self.sha)
        self.assertIn('Deleted', self.clean(apply=True))
        self.assertEqual(self.git('rev-parse', 'ticket/next'), self.sha)
        self.assertFalse(self.remote_exists())
        self.assertIn('Already absent', self.clean(apply=True))

    def test_ssh_remote_works(self):
        self.url = self.push_url = 'git@github.com:owner/repo.git'
        self.assertIn('Deleted', self.clean(apply=True))

    def test_invalid_ref_cannot_delete_anything(self):
        self.pull['head']['ref'] = '../main'
        with self.assertRaises(cleanup_merged.CleanupError):
            self.clean(apply=True)
        self.assert_preserved()


if __name__ == '__main__':
    unittest.main()
