"""Persona behavior through the skill's literal-argument entry point."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('persona_command_test', SKILL / 'scripts/shipyard.py')
command = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command)


class PersonaSettingsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root / 'config')})
        environment.start()
        self.addCleanup(environment.stop)
        self.settings = self.root / 'config/shipyard/persona-settings.json'

    def call(self, *arguments):
        return command.handle(list(arguments))

    def create(self, identity='custom-chief'):
        return self.call('--persona-create', identity, '--name', 'Morgan',
                         '--traits', 'Stay calm. Explain the tradeoff.\nKeep the evidence.')

    def test_list_and_show_are_read_only(self):
        listing = self.call('--personas')
        self.assertEqual(len(listing['roles']), 9)
        show = self.call('--persona-show', 'chief_of_staff')
        self.assertEqual(show['profile']['id'], 'elon-musk')
        self.assertEqual(show['profile']['name'], 'Elon Musk')
        self.assertTrue(Path(show['profile']['path']).is_absolute())
        self.assertFalse(self.settings.parent.exists())

    def test_create_switch_and_manual_edit(self):
        created = self.create()
        path = Path(created['profile']['path'])
        self.assertEqual(path.name, 'custom-chief.md')
        self.assertIn('Keep the evidence.', path.read_text())
        self.call('--persona', 'chief-of-staff:custom-chief')
        path.write_text(path.read_text().replace('Morgan', 'Avery').replace('calm', 'decisive'))
        shown = self.call('--persona-show', 'chief-of-staff')
        self.assertEqual(shown['profile']['name'], 'Avery')
        self.assertIn('decisive', shown['profile']['content'])
        self.assertEqual(shown['selection'], 'saved')

    def test_cross_client_switch_and_reset_preserve_other_roles(self):
        self.call('--client', 'codex', '--persona', 'chief-of-staff:andy-grove')
        self.call('--client', 'claude', '--persona', 'project-manager:elon-musk')
        self.assertEqual(self.call('--client', 'claude', '--persona-show', 'chief-of-staff')['profile']['id'], 'andy-grove')
        result = self.call('--persona-reset', 'chief-of-staff')
        self.assertEqual(result['selection'], 'default')
        self.assertEqual(result['profile']['id'], 'elon-musk')
        self.assertEqual(json.loads(self.settings.read_text())['roles'], {'project-manager': 'elon-musk'})

    def test_creation_never_overwrites_existing_or_builtin(self):
        created = self.create()
        path = Path(created['profile']['path'])
        original = path.read_bytes()
        for identity in ['custom-chief', 'elon-musk']:
            with self.assertRaises(ValueError):
                self.create(identity)
        self.assertEqual(path.read_bytes(), original)

    def test_preview_mutations_create_no_files(self):
        self.call('--persona', 'chief-of-staff:andy-grove', '--preview')
        self.call('--persona-reset', 'chief-of-staff', '--preview')
        result = self.call('--persona-create', 'custom-chief', '--name', 'Morgan', '--traits', 'Calm', '--preview')
        self.assertFalse(result['applied'])
        self.assertFalse(self.settings.parent.exists())

    def test_invalid_commands_create_no_files(self):
        cases = [
            ['--persona', 'chief-of-staff:missing'],
            ['--persona', 'unknown:elon-musk'],
            ['--persona', 'chief-of-staff:../escape'],
            ['--persona', 'chief-of-staff'],
            ['--persona', 'chief-of-staff=elon-musk'],
            ['--persona-create', '../escape', '--name', 'Name', '--traits', 'Traits'],
            ['--persona-create', 'valid', '--name', 'Name'],
            ['--persona-create', 'valid', '--name', 'Name\nID: other', '--traits', 'Traits'],
            ['--personas', '--preview'],
            ['--personas', '--implement', 'sonnet:medium'],
            ['--personas', '--task'],
            ['--personas', '--name', 'unused'],
            ['--personas', '--personas'],
            ['--persona-show', 'chief-of-staff', '--persona-reset', 'chief-of-staff'],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.call(*arguments)
        self.assertFalse(self.settings.parent.exists())

    def test_missing_selected_profile_can_be_repaired_by_reset(self):
        created = self.create()
        self.call('--persona', 'chief-of-staff:custom-chief')
        Path(created['profile']['path']).unlink()
        with self.assertRaisesRegex(ValueError, 'Selected profile is missing'):
            self.call('--persona-show', 'chief-of-staff')
        result = self.call('--persona-reset', 'chief-of-staff')
        self.assertEqual(result['profile']['id'], 'elon-musk')

    def test_invalid_saved_json_fails_without_replacement(self):
        self.settings.parent.mkdir(parents=True)
        raw = '{"version":1,"roles":{},"roles":{}}'
        self.settings.write_text(raw)
        with self.assertRaises(ValueError):
            self.call('--persona', 'chief-of-staff:andy-grove')
        self.assertEqual(self.settings.read_text(), raw)

    def test_unfinished_profile_does_not_block_other_roles_or_reset(self):
        created = self.create()
        self.call('--persona', 'chief-of-staff:custom-chief')
        Path(created['profile']['path']).write_text('# Work in progress\n')
        self.assertIn('custom-chief', self.call('--personas')['errors'])
        self.assertEqual(self.call('--persona-show', 'ci-worker')['profile']['id'], 'brendan-gregg')
        with self.assertRaisesRegex(ValueError, 'title, ID and behavioral content'):
            self.call('--persona-show', 'chief-of-staff')
        self.assertEqual(self.call('--persona-reset', 'chief-of-staff')['profile']['id'], 'elon-musk')

    def test_symlink_custom_profile_is_rejected(self):
        profiles_dir = self.settings.parent / 'personas'
        profiles_dir.mkdir(parents=True)
        target = self.root / 'elsewhere.md'
        target.write_text('# Other\n\nID: custom\n\nTraits\n')
        (profiles_dir / 'custom.md').symlink_to(target)
        with self.assertRaises(ValueError):
            self.call('--persona', 'chief-of-staff:custom')

    def test_structured_bridge_preserves_literal_traits(self):
        traits = 'calm $(touch /tmp/unwanted-persona-command) `echo ignored`'
        result = command.handle(['--input-json'], input_text=json.dumps({
            'arguments': '--persona-create literal --name "Morgan" --traits "' + traits + '"',
            'client': 'codex', 'project': str(self.root),
        }))
        self.assertIn(traits, Path(result['profile']['path']).read_text())

    def test_concurrent_selections_preserve_all_roles(self):
        roles = ['chief-of-staff', 'project-manager', 'code-advisor', 'ci-worker']
        processes = [subprocess.Popen([sys.executable, str(SKILL / 'scripts/shipyard.py'),
                                      '--persona', f'{role}:elon-musk'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for role in roles]
        for process in processes:
            output, error = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, error)
            self.assertEqual(json.loads(output)['mode'], 'persona_settings')
        self.assertEqual(json.loads(self.settings.read_text())['roles'], {role: 'elon-musk' for role in roles})


if __name__ == '__main__':
    unittest.main()
