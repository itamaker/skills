"""Isolated native-role installation checks; no writes to the real home."""

import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'install_clients.py'
spec = importlib.util.spec_from_file_location('install_clients', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root / 'package'
        self.home = self.root / 'home'
        for client in ('codex', 'claude'):
            for asset in installer.asset_paths(client):
                source = self.package / 'assets' / client / asset
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(f'{client}: {asset}\n')
            marker = self.home / ('.agents' if client == 'codex' else '.claude') / 'skills/shipyard/SKILL.md'
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text('installed skill\n')

    def install(self, client='both', apply=True):
        return installer.install(self.package, self.home, client, apply)

    def snapshot(self):
        return sorted(str(p.relative_to(self.home)) for p in self.home.rglob('*'))

    def backups(self):
        return list(self.home.rglob('*.shipyard-backup-*'))

    def test_preview_creates_no_files(self):
        before = self.snapshot()
        messages = self.install(apply=False)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(any('Would install global asset' in m for m in messages))
        self.assertFalse((self.home / '.codex').exists())

    def test_fresh_install_copies_only_allowlist_and_sets_launcher_mode(self):
        self.install()
        for client in ('codex', 'claude'):
            target = self.home / f'.{client}'
            expected = set(installer.asset_paths(client))
            actual = {str(p.relative_to(target)) for p in target.rglob('*') if p.is_file() and 'skills' not in p.relative_to(target).parts}
            self.assertEqual(actual, expected)
            for asset in expected:
                self.assertEqual((target / asset).read_bytes(), (self.package / 'assets' / client / asset).read_bytes())
        self.assertTrue((self.home / '.codex/chief-of-staff').stat().st_mode & stat.S_IXUSR)
        self.assertFalse(self.backups())

    def test_selected_client_only(self):
        marker = self.home / '.claude/skills/shipyard/SKILL.md'
        marker.unlink()
        self.install(client='codex')
        self.assertTrue((self.home / '.codex/agents/chief_of_staff.toml').exists())
        self.assertFalse((self.home / '.claude/agents').exists())

    def test_unchanged_install_is_idempotent(self):
        self.install()
        before = self.snapshot()
        launcher = self.home / '.codex/chief-of-staff'
        before_stat = launcher.stat()
        messages = self.install()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(launcher.stat().st_ino, before_stat.st_ino)
        self.assertFalse(self.backups())
        self.assertTrue(all('Unchanged' in m for m in messages[1:]))

    def test_changed_regular_file_is_backed_up_and_permissions_preserved(self):
        destination = self.home / '.codex/agents/chief_of_staff.toml'
        destination.parent.mkdir(parents=True)
        destination.write_text('existing custom role\n')
        destination.chmod(0o600)
        self.install(client='codex')
        backups = list(destination.parent.glob(destination.name + '.shipyard-backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'existing custom role\n')
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
        destination.write_text('changed again\n')
        self.install(client='codex')
        self.assertEqual(len(list(destination.parent.glob(destination.name + '.shipyard-backup-*'))), 2)

    def test_symlink_destination_is_backed_up_without_following(self):
        external = self.root / 'external'
        external.write_text('external original\n')
        destination = self.home / '.codex/chief-of-staff.config.toml'
        destination.parent.mkdir(parents=True)
        destination.symlink_to(external)
        self.install(client='codex')
        backups = list(destination.parent.glob(destination.name + '.shipyard-backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_symlink())
        self.assertEqual(backups[0].readlink(), external)
        self.assertEqual(external.read_text(), 'external original\n')
        self.assertFalse(destination.is_symlink())

    def test_dangling_symlink_destination_is_preserved_as_symlink_backup(self):
        destination = self.home / '.codex/chief-of-staff.config.toml'
        destination.parent.mkdir(parents=True)
        destination.symlink_to(self.root / 'absent')
        self.install(client='codex')
        backups = list(destination.parent.glob(destination.name + '.shipyard-backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].is_symlink())
        self.assertFalse(backups[0].exists())

    def test_symlink_parent_is_rejected_before_any_writes(self):
        external = self.root / 'external-directory'
        external.mkdir()
        (self.home / '.codex').symlink_to(external, target_is_directory=True)
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, 'Symlink parent'):
            self.install()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(external.iterdir()), [])

    def test_nested_symlink_parent_is_rejected(self):
        external = self.root / 'external-agents'
        external.mkdir()
        target = self.home / '.codex/agents'
        target.parent.mkdir()
        target.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallError, 'Symlink parent'):
            self.install()
        self.assertEqual(list(external.iterdir()), [])

    def test_directory_destination_conflict_is_rejected(self):
        (self.home / '.claude/chief-of-staff.settings.json').mkdir()
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, 'Destination'):
            self.install()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / '.codex').exists())

    def test_missing_source_fails_both_upfront_without_partial_install(self):
        (self.package / 'assets/claude/agents/visual-advisor.md').unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, 'Missing regular package asset'):
            self.install()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / '.codex').exists())

    def test_missing_installed_skill_explains_global_scope_without_writes(self):
        (self.home / '.claude/skills/shipyard/SKILL.md').unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, 'Install shipyard globally for claude first'):
            self.install()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / '.codex').exists())

    def test_symlinked_installed_skill_is_supported(self):
        skill = self.home / '.agents/skills/shipyard'
        (skill / 'SKILL.md').unlink()
        skill.rmdir()
        (self.package / 'SKILL.md').write_text('shared installed skill\n')
        skill.symlink_to(self.package, target_is_directory=True)
        self.install(client='codex')
        self.assertTrue((self.home / '.codex/agents/chief_of_staff.toml').is_file())

    def test_global_settings_and_instructions_are_untouched(self):
        paths = ['.codex/config.toml', '.codex/AGENTS.md', '.claude/settings.json', '.claude/CLAUDE.md']
        for path in paths:
            target = self.home / path
            target.parent.mkdir(exist_ok=True)
            target.write_text(f'original {path}\n')
        self.install()
        for path in paths:
            self.assertEqual((self.home / path).read_text(), f'original {path}\n')

    def test_equal_launcher_without_execute_is_backed_up_and_repaired(self):
        self.install(client='codex')
        launcher = self.home / '.codex/chief-of-staff'
        original = launcher.read_bytes()
        launcher.chmod(0o600)
        self.install(client='codex')
        self.assertTrue(launcher.stat().st_mode & stat.S_IXUSR)
        backup = list(launcher.parent.glob(launcher.name + '.shipyard-backup-*'))
        self.assertEqual(len(backup), 1)
        self.assertEqual(backup[0].read_bytes(), original)
        self.assertEqual(stat.S_IMODE(backup[0].stat().st_mode), 0o600)

    def test_symlinked_package_asset_cannot_read_outside_package(self):
        source = self.package / 'assets/codex/chief-of-staff'
        source.unlink()
        external = self.root / 'external-source'
        external.write_text('outside package')
        source.symlink_to(external)
        before = self.snapshot()
        with self.assertRaisesRegex(installer.InstallError, 'Missing regular package asset'):
            self.install()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
