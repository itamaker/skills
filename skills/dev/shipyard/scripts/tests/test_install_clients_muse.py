"""Muse client checks for install_clients.py; separate from codex/claude tests.

Muse needs no native role install: --client muse is a reporting no-op that
writes nothing. These tests need no codex/claude fixtures, so a Muse failure
never requires touching the codex/claude tests to fix.
"""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'install_clients.py'
spec = importlib.util.spec_from_file_location('install_clients', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class MuseInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root / 'package'
        self.home = self.root / 'home'
        self.home.mkdir()

    def install(self, client='muse', apply=True):
        return installer.install(self.package, self.home, client, apply)

    def snapshot(self):
        return sorted(str(p.relative_to(self.home)) for p in self.home.rglob('*'))

    def test_muse_preview_writes_nothing(self):
        before = self.snapshot()
        messages = self.install(apply=False)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.claude').exists())
        self.assertTrue(any('no native role install' in m for m in messages))
        self.assertTrue(any('No files were written' in m for m in messages))

    def test_muse_apply_is_noop_with_same_report(self):
        before = self.snapshot()
        preview = self.install(apply=False)
        applied = self.install(apply=True)
        self.assertEqual(applied, preview)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.claude').exists())
        self.assertFalse(list(self.home.rglob('*.shipyard-backup-*')))

    def test_muse_policy_is_rejected_not_ignored(self):
        # A policy file must never be silently ignored for muse, nor loaded
        # (it is not used): the {} content would fail validation if read.
        policy = self.root / 'custom-policy.json'
        policy.write_text('{}')
        with self.assertRaisesRegex(installer.InstallError, '--policy has no effect for muse'):
            installer.install(self.package, self.home, 'muse', True, policy=policy)
        self.assertEqual(self.snapshot(), [])

    def test_muse_needs_no_installed_skill_markers(self):
        # The muse branch returns before any marker or asset check runs.
        messages = self.install(apply=True)
        self.assertTrue(any('no native role install' in m for m in messages))



if __name__ == '__main__':
    unittest.main()
