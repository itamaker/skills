"""Flat-command routing and real isolated phase-settings transactions."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock


SKILL = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('shipyard_command', SKILL / 'scripts/shipyard.py')
command = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command)


class ShipyardCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.personal = self.root / 'personal/settings.json'
        self.settings = self.project / '.shipyard/model-settings.json'

    def call(self, *arguments, client='claude', **kwargs):
        return command.handle(['--client', client, '--project', str(self.project),
                               '--user-config', str(self.personal), *arguments], cwd=self.project, **kwargs)

    def document(self, path=None):
        return json.loads((path or self.settings).read_text())

    def test_all_nine_flags_route_to_the_canonical_stage_and_role(self):
        arguments = [value for target in command.TARGETS for value in (f'--{target}', 'sonnet:medium')]
        result = self.call(*arguments)
        self.assertTrue(result['applied'])
        self.assertEqual(len(result['targets']), 9)
        stages = self.document()['clients']['claude']['stages']
        for target, (stage, role) in command.TARGETS.items():
            with self.subTest(target=target):
                self.assertEqual(stages[stage][role]['model'], 'sonnet')
                self.assertEqual(stages[stage][role]['effort'], 'medium')
        self.assertEqual(command.TARGETS['verify'][1], 'verify-worker')
        self.assertEqual(command.TARGETS['ci'][1], 'ci-worker')
        self.assertEqual(command.TARGETS['deliver'][1], 'deliver-worker')

    def test_multi_target_is_one_batch_and_invalid_second_target_writes_nothing(self):
        self.call('--implement', 'sonnet:medium', '--code-review', 'opus:high')
        before = self.settings.read_bytes()
        with self.assertRaises(ValueError):
            self.call('--implement', 'haiku:low', '--code-review', 'not-a-model:high')
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertFalse(list(self.settings.parent.glob('*.backup-*')))
        self.call('--implement', 'haiku:low', '--code-review', 'sonnet:medium')
        self.assertEqual(len(list(self.settings.parent.glob('*.backup-*'))), 1)

    def test_preview_and_config_are_read_only_and_auto_is_not_guessed(self):
        preview = self.call('--implement', 'sonnet:medium', '--preview')
        self.assertFalse(preview['applied'])
        self.assertFalse(self.settings.parent.exists())
        result = self.call('--config')
        self.assertEqual(len(result['targets']), 9)
        self.assertTrue(all(target['preferences']['tier'] == 'auto' for target in result['targets']))
        self.assertIsNone(result['effective_model'])
        self.assertFalse(self.settings.parent.exists())

    def test_auto_masks_a_generic_role_pin_but_reset_reveals_it(self):
        backend = command.backend_module()
        backend.configure('claude', 'set', 'project', role='implementation-worker',
                          values={'model': 'opus', 'effort': 'high'}, apply=True,
                          project=self.project, user_config=self.personal)
        self.call('--implement', 'auto')
        result = self.call('--config')
        implement = next(t for t in result['targets'] if t['target'] == 'implement')
        self.assertNotIn('model', implement['preferences'])
        self.call('--reset', 'implement')
        restored = self.call('--config')
        implement = next(t for t in restored['targets'] if t['target'] == 'implement')
        self.assertEqual(implement['preferences']['model'], 'opus')

    def test_reset_all_preserves_generic_defaults_and_other_client(self):
        backend = command.backend_module()
        backend.configure('claude', 'set', 'project', values={'effort': 'medium'}, apply=True,
                          project=self.project, user_config=self.personal)
        backend.configure('codex', 'set', 'project', role='implementation-worker',
                          values={'tier': 'balanced'}, apply=True,
                          project=self.project, user_config=self.personal)
        self.call('--implement', 'haiku:low', '--code-review', 'opus:high')
        self.call('--reset', 'all')
        saved = self.document()['clients']
        self.assertEqual(saved['claude']['defaults'], {'effort': 'medium'})
        self.assertNotIn('stages', saved['claude'])
        self.assertEqual(saved['codex']['roles']['implementation-worker']['tier'], 'balanced')

    def test_user_scope_does_not_read_or_change_project_settings(self):
        self.settings.parent.mkdir()
        self.settings.write_text('invalid project data')
        self.call('--user', '--implement', 'sonnet:medium')
        self.assertEqual(self.settings.read_text(), 'invalid project data')
        self.assertEqual(self.document(self.personal)['clients']['claude']['stages']['implement']['implementation-worker']['model'], 'sonnet')

    def test_duplicate_conflicting_and_unknown_flags_fail_before_backend_calls(self):
        backend = Mock()
        for arguments in [
            ['--implement', 'sonnet:medium', '--implement', 'opus:high'],
            ['--implement', 'sonnet:medium', '--reset', 'implement'],
            ['--config', '--implement', 'sonnet:medium'],
            ['--reset', 'implement,implement'], ['--reset', 'unknown'],
            ['--implement', 'sonnet'], ['--implement', ':high'],
            ['--implement', 'sonnet:'], ['--scope', 'project'],
            ['--user', '--task', '--implement', 'sonnet:medium'],
            ['--next', '--implement', 'sonnet:medium', '--verify', 'opus:high'],
        ]:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.call(*arguments, backend=backend)
        self.assertEqual(backend.mock_calls, [])

    def test_task_next_preview_and_reset_return_intents_without_persistence(self):
        result = self.call('--next', '--verify', 'opus:high')
        self.assertEqual(result['mode'], 'next_override_intent')
        self.assertEqual(result['operations'][0]['role'], 'verify-worker')
        self.assertTrue(result['record'])
        preview = self.call('--task', '--implement', 'sonnet:medium', '--preview')
        self.assertFalse(preview['record'])
        reset = self.call('--next', '--reset', 'all')
        self.assertTrue(all(op['action'] == 'reset' for op in reset['operations']))
        status = self.call('--next', '--config')
        self.assertEqual(status['mode'], 'next_status_intent')
        self.assertFalse(self.settings.parent.exists())
        self.assertFalse(self.personal.exists())

    def test_colons_in_a_registered_model_id_remain_literal(self):
        self.assertEqual(command.assignment('provider:deployment:model:high'),
                         {'model': 'provider:deployment:model', 'effort': 'high'})

    def test_bridge_uses_json_data_and_never_executes_shell_fragments(self):
        marker = self.root / 'must-not-exist'
        payload = {'client': 'claude', 'project': str(self.project),
                   'user_config': str(self.personal),
                   'arguments': f'--implement "$(touch {marker}):medium"'}
        with self.assertRaises(ValueError):
            command.handle(['--input-json'], input_text=json.dumps(payload), cwd=self.project)
        self.assertFalse(marker.exists())
        payload['arguments'] = '--implement sonnet:medium --preview'
        result = command.handle(['--input-json'], input_text=json.dumps(payload), cwd=self.project)
        self.assertTrue(result['preview'])
        self.assertFalse(self.settings.parent.exists())

    def test_bad_bridge_json_and_host_context_are_rejected(self):
        for payload in ['{invalid', '{"arguments":"--config","arguments":"--reset all"}',
                        json.dumps({'arguments': '--config', 'unknown': True}),
                        json.dumps({'arguments': '--config', 'client': 'wrong'}),
                        json.dumps({'arguments': '--client codex --config', 'client': 'claude'}),
                        json.dumps({'arguments': '--implement "', 'client': 'claude'})]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                command.handle(['--input-json'], input_text=payload)

    def test_empty_natural_and_help_do_not_touch_backend(self):
        backend = Mock()
        self.assertEqual(command.handle([], backend=backend)['mode'], 'delivery')
        self.assertEqual(command.handle(['build', 'this'], backend=backend)['mode'], 'natural')
        result = command.handle(['--help'], backend=backend)
        for target in command.TARGETS:
            self.assertIn(f'--{target}', result['text'])
        self.assertEqual(backend.mock_calls, [])

    def test_direct_cli_fails_cleanly_outside_git_without_explicit_project(self):
        result = subprocess.run([sys.executable, str(SKILL / 'scripts/shipyard.py'),
                                 '--client', 'claude', '--user-config', str(self.personal),
                                 '--implement', 'sonnet:medium'], cwd=self.root, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.personal.exists())

    def test_saved_phase_is_used_by_the_actual_planner_cli(self):
        self.call('--implement', 'sonnet:medium', '--verify', 'opus:high')
        def plan(role, stage):
            output = subprocess.check_output([
                sys.executable, str(SKILL / 'scripts/model_policy.py'), '--client', 'claude',
                '--project', str(self.project), '--user-config', str(self.personal),
                '--role', role, '--stage', stage,
            ], text=True)
            return json.loads(output)
        self.assertEqual(plan('implementation-worker', 'implement')['requested_model'], 'sonnet')
        self.assertEqual(plan('verify-worker', 'verify')['requested_model'], 'opus')
        self.assertEqual(plan('implementation-worker', 'verify')['requested_model'], 'sonnet')


if __name__ == '__main__':
    unittest.main()
