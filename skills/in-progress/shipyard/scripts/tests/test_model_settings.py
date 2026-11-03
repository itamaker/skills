"""Scoped persistence/resolution checks using temporary settings and policy files."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'model_settings.py'
spec = importlib.util.spec_from_file_location('model_settings', SCRIPT)
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class ModelSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.user = self.root / 'personal/model-settings.json'
        self.project_file = self.project / '.shipyard/model-settings.json'

    def write(self, path, defaults=None, roles=None, client='codex'):
        document = {'version': 1, 'clients': {client: {}}}
        if defaults is not None:
            document['clients'][client]['defaults'] = defaults
        if roles is not None:
            document['clients'][client]['roles'] = roles
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document))
        return document

    def resolve(self, **kwargs):
        kwargs.setdefault('project', self.project)
        kwargs.setdefault('user_config', self.user)
        kwargs.setdefault('cwd', self.project)
        return settings.resolve('codex', **kwargs)

    def change(self, action='set', scope='user', **kwargs):
        kwargs.setdefault('project', self.project)
        kwargs.setdefault('user_config', self.user)
        kwargs.setdefault('cwd', self.project)
        return settings.configure('codex', action, scope, **kwargs)

    def snapshot(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))

    def test_absent_settings_use_builtin_without_creating_files(self):
        before = self.snapshot()
        result = self.resolve()
        self.assertEqual(result['values'], {'tier': 'auto', 'max_tier': 'deep'})
        self.assertIsNone(result['policy_path'])
        self.assertEqual(self.snapshot(), before)

    def test_defaults_roles_projects_and_task_precedence_with_provenance(self):
        self.write(self.user, {'tier': 'economy'}, {'implementation-worker': {'tier': 'balanced'}})
        self.write(self.project_file, {'tier': 'deep'}, {'implementation_worker': {'tier': 'balanced'}})
        self.assertEqual(self.resolve()['sources']['tier']['layer'], 'project.roles.implementation_worker')
        result = self.resolve(overrides={'tier': 'economy'})
        self.assertEqual(result['values']['tier'], 'economy')
        self.assertEqual(result['sources']['tier']['layer'], 'task')
        self.assertEqual(len(result['layers']), 6)
        self.assertEqual(result['layers'][-1]['values'], {'tier': 'economy', 'model': None, 'effort': None})

    def test_missing_field_inherits_and_null_clears(self):
        self.write(self.user, {'model': 'gpt-6-astra', 'effort': 'high'})
        self.write(self.project_file, {'max_tier': 'deep'})
        self.assertEqual(self.resolve()['values']['model'], 'gpt-6-astra')
        self.write(self.project_file, {'model': None, 'effort': None})
        result = self.resolve()
        self.assertNotIn('model', result['values'])
        self.assertNotIn('effort', result['values'])
        self.assertTrue(result['sources']['model']['cleared'])
        self.assertEqual(result['values']['tier'], 'auto')

    def test_set_auto_persists_tombstones_and_reset_reveals_lower_pins(self):
        self.write(self.user, {'model': 'gpt-6-astra', 'effort': 'high'})
        result = self.change(scope='project', values={'tier': 'auto'}, apply=True)
        stored = json.loads(self.project_file.read_text())['clients']['codex']['defaults']
        self.assertEqual(stored, {'tier': 'auto', 'model': None, 'effort': None})
        self.assertNotIn('model', result['values'])
        result = self.change('reset', scope='project', apply=True)
        self.assertEqual(result['values']['model'], 'gpt-6-astra')

    def test_model_only_clears_inherited_tier_and_effort(self):
        self.write(self.user, {'tier': 'deep', 'effort': 'high'})
        result = self.resolve(overrides={'model': 'gpt-6-luna'})
        self.assertEqual(result['values']['model'], 'gpt-6-luna')
        self.assertEqual(result['values']['tier'], 'auto')
        self.assertNotIn('effort', result['values'])
        self.change(scope='project', values={'model': 'gpt-6-luna'}, apply=True)
        stored = json.loads(self.project_file.read_text())['clients']['codex']['defaults']
        self.assertEqual(stored, {'model': 'gpt-6-luna', 'tier': 'auto', 'effort': None})

    def test_effort_only_preserves_selected_model(self):
        self.write(self.user, {'model': 'gpt-6-astra'})
        result = self.resolve(overrides={'effort': 'low'})
        self.assertEqual(result['values']['model'], 'gpt-6-astra')
        self.assertEqual(result['values']['effort'], 'low')

    def test_cap_is_strictest_even_when_later_layers_clear_or_relax(self):
        self.write(self.user, {'max_tier': 'balanced'})
        self.write(self.project_file, {'max_tier': 'deep'})
        for explicit in ({'max_tier': 'deep'}, {'max_tier': None}):
            result = self.resolve(overrides=explicit)
            self.assertEqual(result['values']['max_tier'], 'balanced')
            self.assertEqual(result['sources']['max_tier']['layer'], 'user.defaults')
        self.assertEqual(len(result['ceiling_sources']), 3)
        result = self.change('reset', fields=['max_tier'], apply=True)
        self.assertEqual(result['values']['max_tier'], 'deep')

    def test_budget_only_cap_saves_without_auto_role_floor_failure(self):
        self.change(values={'max_tier': 'economy'}, apply=True)
        result = self.resolve(role='architecture_advisor')
        self.assertEqual(result['values'], {'tier': 'auto', 'max_tier': 'economy'})
        policy = settings.policy_module()
        with self.assertRaisesRegex(ValueError, 'hard cap'):
            policy.select(policy.load_policy(), 'codex', role='architecture_advisor', **result['values'], env={})

    def test_explicit_pin_cannot_bypass_saved_cap(self):
        self.write(self.user, {'max_tier': 'economy'})
        with self.assertRaisesRegex(ValueError, 'max_tier'):
            self.resolve(overrides={'model': 'gpt-6-astra', 'max_tier': 'deep'})
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.change(scope='project', values={'tier': 'deep'}, apply=True)
        self.assertEqual(self.snapshot(), before)

    def test_only_selected_client_and_role_are_changed(self):
        original = self.write(self.user, {'tier': 'balanced'}, {'code_advisor': {'effort': 'high'}})
        original['clients']['claude'] = {'defaults': {'model': 'opus'}, 'roles': {'visual_advisor': {'effort': 'low'}}}
        self.user.write_text(json.dumps(original))
        self.change(role='implementation-worker', values={'tier': 'economy'}, apply=True)
        stored = json.loads(self.user.read_text())
        self.assertEqual(stored['clients']['claude'], original['clients']['claude'])
        self.assertEqual(stored['clients']['codex']['defaults'], original['clients']['codex']['defaults'])
        self.assertEqual(stored['clients']['codex']['roles']['code_advisor'], {'effort': 'high'})
        self.change('reset', role='implementation_worker', fields=['tier'], apply=True)
        remaining = json.loads(self.user.read_text())['clients']['codex']['roles']['implementation_worker']
        self.assertEqual(remaining, {'model': None, 'effort': None})

    def test_reset_whole_role_or_defaults_preserves_other_entries(self):
        original = self.write(self.user, {'tier': 'balanced'}, {
            'code_advisor': {'effort': 'high'}, 'project_manager': {'tier': 'balanced'},
        })
        self.change('reset', role='code_advisor', apply=True)
        stored = json.loads(self.user.read_text())['clients']['codex']
        self.assertNotIn('code_advisor', stored['roles'])
        self.assertEqual(stored['defaults'], original['clients']['codex']['defaults'])
        self.change('reset', apply=True)
        stored = json.loads(self.user.read_text())['clients']['codex']
        self.assertNotIn('defaults', stored)
        self.assertEqual(stored['roles'], {'project_manager': {'tier': 'balanced'}})

    def test_target_directory_conflict_fails_without_writes(self):
        self.user.mkdir(parents=True)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.change(values={'tier': 'economy'}, apply=True)
        self.assertEqual(self.snapshot(), before)

    def test_policy_tombstone_reveals_builtin_policy_without_changing_sources(self):
        custom = self.project / 'custom.json'
        custom.write_text(json.dumps(settings.policy_module().load_policy()))
        self.write(self.user, {'policy': str(custom)})
        result = self.resolve(overrides={'policy': None})
        self.assertIsNone(result['policy_path'])
        self.assertTrue(result['sources']['policy']['cleared'])
        self.assertEqual(result['sources']['policy']['layer'], 'task')

    def test_preview_and_invalid_set_never_create_settings_lock_or_backups(self):
        before = self.snapshot()
        result = self.change(values={'tier': 'balanced'})
        self.assertFalse(result['applied'])
        self.assertEqual(self.snapshot(), before)
        for values in ({'unknown': 'x'}, {'model': 'unknown'}, {'effort': 'unknown'}, {'tier': 'unknown'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.change(values=values, apply=True)
        self.assertEqual(self.snapshot(), before)

    def test_backups_preserve_raw_original_and_unchanged_rerun_is_noop(self):
        self.change(values={'tier': 'balanced'}, apply=True)
        raw = self.user.read_bytes()
        result = self.change(values={'tier': 'economy'}, apply=True)
        self.assertEqual(Path(result['backup']).read_bytes(), raw)
        snapshot = self.snapshot()
        self.assertFalse(self.change(values={'tier': 'economy'}, apply=True)['applied'])
        self.assertEqual(self.snapshot(), snapshot)

    def test_target_and_parent_symlinks_are_rejected_without_writes(self):
        external = self.root / 'outside.json'
        external.write_text('{"version":1}')
        self.user.parent.mkdir()
        self.user.symlink_to(external)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.change(values={'tier': 'economy'}, apply=True)
        self.assertEqual(external.read_text(), '{"version":1}')
        self.assertEqual(self.snapshot(), before)
        self.user.unlink()
        self.user.parent.rmdir()
        directory = self.root / 'elsewhere'
        directory.mkdir()
        self.user.parent.symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink parent'):
            self.change(values={'tier': 'economy'}, apply=True)
        self.assertEqual(list(directory.iterdir()), [])

    def test_damaged_json_unknown_fields_and_duplicate_keys_fail_closed(self):
        self.user.parent.mkdir()
        for raw in ('{invalid', '{"version":1,"command":"run"}', '{"version":1,"version":1}', '{"version":1,"clients":{"codex":{"roles":{"code_advisor":{"policy":"x"}}}}}'):
            with self.subTest(raw=raw):
                self.user.write_text(raw)
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.change(values={'tier': 'economy'}, apply=True)
                self.assertEqual(self.user.read_text(), raw)
                self.assertEqual(self.snapshot(), before)

    def test_project_policy_is_portable_relative_to_settings_file(self):
        custom = self.project / 'policies/custom.json'
        custom.parent.mkdir()
        policy = settings.policy_module().load_policy()
        policy['clients']['codex']['model_capabilities']['custom'] = {'tier': 'balanced', 'default_effort': 'low', 'efforts': ['low'], 'vision': True}
        custom.write_text(json.dumps(policy))
        result = self.change(scope='project', values={'policy': 'policies/custom.json', 'model': 'custom'}, apply=True)
        stored = json.loads(self.project_file.read_text())['clients']['codex']['defaults']
        self.assertEqual(stored['policy'], '../policies/custom.json')
        self.assertEqual(result['policy_path'], str(custom))
        fresh = self.resolve()
        self.assertEqual(fresh['policy_path'], str(custom))
        self.assertEqual(fresh['values']['model'], 'custom')
        self.assertNotIn('policy', fresh['values'])

    def test_custom_policy_from_task_is_relative_to_caller_cwd(self):
        path = self.project / 'custom.json'
        path.write_text(json.dumps(settings.policy_module().load_policy()))
        self.assertEqual(self.resolve(overrides={'policy': 'custom.json'})['policy_path'], str(path))

    def test_project_override_cannot_mask_invalid_user_model(self):
        self.write(self.project_file, {'tier': 'balanced', 'model': None, 'effort': None})
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Unknown model'):
            self.change(values={'model': 'not-a-real-model'}, apply=True)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.user.exists())

    def test_higher_project_policy_cannot_validate_user_only_model(self):
        custom = self.project / 'custom.json'
        policy = settings.policy_module().load_policy()
        policy['clients']['codex']['model_capabilities']['project-only'] = {
            'tier': 'balanced', 'default_effort': 'low', 'efforts': ['low'], 'vision': True,
        }
        custom.write_text(json.dumps(policy))
        self.write(self.project_file, {'policy': '../custom.json'})
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Unknown model'):
            self.change(values={'model': 'project-only'}, apply=True)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.user.exists())

    def test_target_scope_role_cannot_mask_invalid_defaults(self):
        for scope, path in [('user', self.user), ('project', self.project_file)]:
            with self.subTest(scope=scope):
                original = self.write(path, roles={'implementation_worker': {
                    'tier': 'balanced', 'model': None, 'effort': None,
                }})
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, 'Unknown model'):
                    self.change(scope=scope, values={'model': 'not-a-real-model'}, apply=True)
                self.assertEqual(json.loads(path.read_text()), original)
                self.assertEqual(self.snapshot(), before)

    def test_scope_validation_does_not_remove_real_roles_or_other_clients(self):
        original = self.write(self.user, {'tier': 'balanced'}, {'implementation_worker': {'effort': 'high'}})
        original['clients']['claude'] = {'defaults': {'tier': 'deep'}}
        self.user.write_text(json.dumps(original))
        self.write(self.project_file, {'tier': 'balanced', 'model': None, 'effort': None})
        self.change(values={'tier': 'economy'}, apply=True)
        stored = json.loads(self.user.read_text())
        self.assertEqual(stored['clients']['codex']['roles'], original['clients']['codex']['roles'])
        self.assertEqual(stored['clients']['claude'], original['clients']['claude'])

    def test_user_role_validation_ignores_higher_project_role_mask(self):
        self.write(self.project_file, roles={'code_advisor': {'tier': 'balanced', 'model': None, 'effort': None}})
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Unknown model'):
            self.change(role='code_advisor', values={'model': 'not-a-real-model'}, apply=True)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.user.exists())

    def test_missing_or_invalid_chosen_policy_never_falls_back(self):
        for content in (None, '{bad', '{"version":42}'):
            path = self.project / 'custom.json'
            if content is not None:
                path.write_text(content)
            with self.subTest(content=content), self.assertRaises((ValueError, OSError)):
                self.change(scope='project', values={'policy': 'custom.json'}, apply=True)
            self.assertFalse(self.project_file.exists())

    def test_discovered_project_is_ignored_until_trusted_and_opt_out_keeps_user(self):
        subprocess.run(['git', 'init', str(self.project)], check=True, capture_output=True)
        self.write(self.user, {'tier': 'economy'})
        self.project_file.parent.mkdir()
        self.project_file.write_text('{malformed and untrusted')
        ignored = self.resolve(project=None)
        self.assertEqual(ignored['values']['tier'], 'economy')
        self.assertTrue(ignored['warnings'])
        with self.assertRaises(ValueError):
            self.resolve(project=None, trust_project=True)
        self.write(self.project_file, {'tier': 'balanced'})
        self.assertEqual(self.resolve(project=None, trust_project=True)['values']['tier'], 'balanced')
        self.assertEqual(self.resolve(project=None, trust_project=True, no_project=True)['values']['tier'], 'economy')

    def test_project_writes_outside_git_require_explicit_project(self):
        with self.assertRaisesRegex(ValueError, 'explicit --project'):
            self.change(scope='project', project=None, trust_project=True, values={'tier': 'economy'}, apply=True)
        self.assertFalse(self.project_file.exists())
        self.assertTrue(self.change(scope='project', values={'tier': 'economy'}, apply=True)['applied'])

    def test_discovered_git_project_can_be_written_only_when_trusted(self):
        subprocess.run(['git', 'init', str(self.project)], check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, 'explicit --project'):
            self.change(scope='project', project=None, values={'tier': 'economy'}, apply=True)
        self.assertTrue(self.change(scope='project', project=None, trust_project=True, values={'tier': 'economy'}, apply=True)['applied'])

    def test_lock_symlink_is_rejected(self):
        self.user.parent.mkdir()
        target = self.root / 'lock-target'
        target.write_text('preserve')
        self.user.with_name(self.user.name + '.lock').symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.change(values={'tier': 'economy'}, apply=True)
        self.assertFalse(self.user.exists())
        self.assertEqual(target.read_text(), 'preserve')

    def test_concurrent_read_modify_write_preserves_independent_roles(self):
        commands = []
        for role in ('project_manager', 'implementation_worker', 'code_advisor', 'visual_advisor'):
            command = [sys.executable, str(SCRIPT), 'set', '--client', 'codex', '--scope', 'user', '--role', role,
                       '--tier', 'balanced', '--user-config', str(self.user), '--project', str(self.project), '--apply']
            commands.append(subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for process in commands:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr + stdout)
        roles = json.loads(self.user.read_text())['clients']['codex']['roles']
        self.assertEqual(set(roles), {'project_manager', 'implementation_worker', 'code_advisor', 'visual_advisor'})
        self.assertFalse(list(self.user.parent.glob('*.tmp')))

    def test_invalid_cli_prints_clean_error_and_preview_is_json(self):
        common = ['--client', 'codex', '--user-config', str(self.user), '--project', str(self.project)]
        result = subprocess.run([sys.executable, str(SCRIPT), 'set', *common, '--scope', 'user', '--model', 'unknown', '--apply'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Model settings rejected', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), 'set', *common, '--scope', 'user', '--tier', 'balanced'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['applied'])
        self.assertFalse(self.user.exists())


if __name__ == '__main__':
    unittest.main()
