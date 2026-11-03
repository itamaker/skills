"""Exercise explicit preset rendering using the real packaged native assets."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest


SKILL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('preset_installer', SKILL / 'scripts/install_clients.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PresetInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        for directory in ['.agents/skills', '.claude/skills']:
            location = self.home / directory
            location.mkdir(parents=True)
            (location / 'shipyard').symlink_to(SKILL, target_is_directory=True)

    def test_every_preset_renders_roles_and_primary_launch_settings(self):
        policy = json.loads((SKILL / 'assets/model-policy.json').read_text())
        for tier in ['economy', 'balanced', 'deep']:
            with self.subTest(tier=tier):
                installer.install(SKILL, self.home, tier=tier, apply=True)
                expected = policy['clients']['codex']['tiers'][tier]
                for path in (self.home / '.codex/agents').glob('*.toml'):
                    data = tomllib.loads(path.read_text())
                    self.assertEqual(data['model'], expected['model'])
                    self.assertEqual(data['model_reasoning_effort'], expected['effort'])
                output = subprocess.check_output([
                    sys.executable, str(self.home / '.codex/chief-of-staff'),
                    '--print-command', 'prompt with spaces',
                ], text=True)
                argv = json.loads(output)
                self.assertEqual(argv[-1], 'prompt with spaces')
                self.assertIn(f'model={json.dumps(expected["model"])}', argv)
                self.assertIn(f'model_reasoning_effort={json.dumps(expected["effort"])}', argv)
                expected = policy['clients']['claude']['tiers'][tier]
                for path in (self.home / '.claude/agents').glob('*.md'):
                    frontmatter = path.read_text().split('---', 2)[1]
                    self.assertIn(f'model: {json.dumps(expected["model"])}\n', frontmatter)
                    self.assertIn(f'effort: {json.dumps(expected["effort"])}\n', frontmatter)
                settings = json.loads((self.home / '.claude/chief-of-staff.settings.json').read_text())
                self.assertEqual(settings['model'], expected['model'])
                self.assertEqual(settings['effortLevel'], expected['effort'])

    def test_inherit_restores_unpinned_roles_and_preserves_preset_backups(self):
        installer.install(SKILL, self.home, tier='deep', apply=True)
        installer.install(SKILL, self.home, tier='inherit', apply=True)
        for path in (self.home / '.codex/agents').glob('*.toml'):
            data = tomllib.loads(path.read_text())
            self.assertNotIn('model', data)
            self.assertNotIn('model_reasoning_effort', data)
        primary = tomllib.loads((self.home / '.codex/chief-of-staff.config.toml').read_text())
        self.assertNotIn('model', primary)
        self.assertNotIn('model_reasoning_effort', primary)
        for path in (self.home / '.claude/agents').glob('*.md'):
            frontmatter = path.read_text().split('---', 2)[1]
            self.assertNotIn('\nmodel:', frontmatter)
            self.assertNotIn('\neffort:', frontmatter)
        self.assertEqual(json.loads((self.home / '.claude/chief-of-staff.settings.json').read_text()), {})
        self.assertTrue(list(self.home.rglob('*.shipyard-backup-*')))

    def test_custom_policy_is_used_without_editing_packaged_defaults(self):
        original = (SKILL / 'assets/model-policy.json').read_text()
        custom = json.loads(original)
        custom['clients']['codex']['tiers']['balanced']['effort'] = 'high'
        path = self.home / 'custom-policy.json'
        path.write_text(json.dumps(custom))
        installer.install(SKILL, self.home, client='codex', tier='balanced', policy=path, apply=True)
        data = tomllib.loads((self.home / '.codex/agents/implementation_worker.toml').read_text())
        self.assertEqual(data['model_reasoning_effort'], 'high')
        self.assertEqual((SKILL / 'assets/model-policy.json').read_text(), original)

    def test_invalid_policy_cannot_partially_install_either_client(self):
        path = self.home / 'invalid.json'
        path.write_text('{}')
        with self.assertRaises(ValueError):
            installer.install(SKILL, self.home, tier='balanced', policy=path, apply=True)
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.claude/agents').exists())

    def test_policy_requires_explicit_preset(self):
        with self.assertRaisesRegex(installer.InstallError, 'explicit'):
            installer.install(SKILL, self.home, policy=self.home / 'anything.json', apply=True)
        self.assertFalse((self.home / '.codex').exists())

    def test_unpersistable_claude_effort_fails_both_before_writes(self):
        policy = json.loads((SKILL / 'assets/model-policy.json').read_text())
        opus = policy['clients']['claude']['model_capabilities']['opus']
        opus['efforts'].append('max')
        policy['clients']['claude']['tiers']['deep']['effort'] = 'max'
        path = self.home / 'runtime-only-effort.json'
        path.write_text(json.dumps(policy))
        with self.assertRaisesRegex(installer.InstallError, 'cannot persist'):
            installer.install(SKILL, self.home, tier='deep', policy=path, apply=True)
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.claude/agents').exists())

    def test_preset_validates_visual_capability_for_each_client_before_writes(self):
        for client in ['codex', 'claude']:
            with self.subTest(client=client):
                policy = json.loads((SKILL / 'assets/model-policy.json').read_text())
                model = policy['clients'][client]['tiers']['balanced']['model']
                policy['clients'][client]['model_capabilities'][model]['vision'] = False
                path = self.home / 'nonvisual-policy.json'
                path.write_text(json.dumps(policy))
                with self.assertRaisesRegex(ValueError, 'vision capability'):
                    installer.install(SKILL, self.home, tier='balanced', policy=path, apply=True)
                self.assertFalse((self.home / '.codex').exists())
                self.assertFalse((self.home / '.claude/agents').exists())


if __name__ == '__main__':
    unittest.main()
