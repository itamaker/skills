"""Deterministic planner tests; no client/API/model calls are made."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'model_policy.py'
spec = importlib.util.spec_from_file_location('model_policy', SCRIPT)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = selector.load_policy()

    def select(self, client='codex', **kwargs):
        kwargs.setdefault('env', {})
        return selector.select(self.policy, client, **kwargs)

    def test_role_complexity_and_risk_choose_relative_tiers(self):
        self.assertEqual(self.select(complexity='low')['tier'], 'economy')
        self.assertEqual(self.select()['tier'], 'balanced')
        self.assertEqual(self.select(role='project-manager', complexity='low')['tier'], 'balanced')
        self.assertEqual(self.select(role='architecture-advisor', complexity='low')['tier'], 'deep')
        self.assertEqual(self.select(complexity='high')['tier'], 'deep')
        self.assertEqual(self.select(risk='high')['tier'], 'deep')
        self.assertEqual(self.select(risk='medium', complexity='low')['tier'], 'balanced')

    def test_defaults_for_both_clients(self):
        for client, model in [('codex', 'gpt-6.1-sol'), ('claude', 'sonnet')]:
            with self.subTest(client=client):
                result = self.select(client)
                self.assertEqual((result['requested_model'], result['requested_effort']), (model, 'medium'))
                self.assertIsNone(result['effective_model'])
                self.assertIsNone(result['effective_effort'])

    def test_explicit_tier_can_override_auto_minimum_with_warning(self):
        result = self.select(role='architecture_advisor', tier='economy')
        self.assertEqual((result['requested_model'], result['requested_effort']), ('gpt-6-luna', 'low'))
        self.assertTrue(any('below recommended deep' in w for w in result['warnings']))

    def test_explicit_model_gets_its_own_default_effort(self):
        result = self.select(model='gpt-6-astra')
        self.assertEqual((result['tier'], result['requested_effort']), ('deep', 'high'))
        result = self.select(risk='high', model='gpt-6-luna')
        self.assertEqual(result['requested_effort'], 'low')
        self.assertTrue(any('below recommended' in w for w in result['warnings']))

    def test_explicit_effort_is_preserved(self):
        result = self.select(model='gpt-6-luna', effort='max')
        self.assertEqual((result['requested_model'], result['requested_effort']), ('gpt-6-luna', 'max'))
        self.assertEqual(self.select(effort='low')['requested_effort'], 'low')

    def test_unknown_model_or_incompatible_effort_is_rejected(self):
        for kwargs in [{'model': 'unknown'}, {'effort': 'unknown'}, {'tier': 'economy', 'model': 'gpt-6-astra'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(selector.PolicyError):
                self.select(**kwargs)
        with self.assertRaisesRegex(selector.PolicyError, 'unsupported'):
            self.select('claude', effort='max')

    def test_custom_model_requires_declared_capabilities(self):
        self.policy['clients']['codex']['model_capabilities']['custom-model'] = {
            'tier': 'balanced', 'efforts': ['low'], 'default_effort': 'low', 'vision': True,
        }
        result = self.select(model='custom-model')
        self.assertEqual((result['requested_model'], result['requested_effort']), ('custom-model', 'low'))
        with self.assertRaisesRegex(selector.PolicyError, 'hard cap'):
            self.select(model='custom-model', max_tier='economy')

    def test_hard_cap_never_silently_downgrades(self):
        for kwargs in [{'risk': 'high', 'max_tier': 'balanced'}, {'tier': 'deep', 'max_tier': 'economy'}, {'model': 'gpt-6-astra', 'max_tier': 'balanced'}]:
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(selector.PolicyError, 'hard cap'):
                self.select(**kwargs)

    def test_one_evidence_backed_escalation(self):
        result = self.select(complexity='low', escalate=True, evidence='Focused check still fails')
        self.assertEqual((result['tier'], result['escalation_count'], result['max_escalations']), ('balanced', 1, 1))
        self.assertEqual(self.select(escalation_count=1)['escalation_count'], 1)
        for kwargs in [{'escalation_count': 1, 'evidence': 'failure'}, {'evidence': ''}, {'evidence': ' '}, {'risk': 'high', 'evidence': 'failure'}, {'max_tier': 'balanced', 'evidence': 'failure'}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(selector.PolicyError):
                self.select(escalate=True, **kwargs)

    def test_escalation_never_changes_manual_pins(self):
        for pin in [{'tier': 'balanced'}, {'model': 'gpt-6.1-sol'}, {'effort': 'medium'}]:
            with self.subTest(pin=pin), self.assertRaisesRegex(selector.PolicyError, 'explicit'):
                self.select(escalate=True, evidence='failure', **pin)

    def test_unknown_fixed_spawn_and_session_hosts_are_distinct(self):
        expected = {'unknown': 'plan_only', 'fixed': 'session_preset_required', 'spawn': 'spawn_overrides', 'session': 'session_preset'}
        for runtime, method in expected.items():
            with self.subTest(runtime=runtime):
                result = self.select(runtime=runtime)
                self.assertEqual(result['application_method'], method)
                self.assertIsNone(result['effective_model'])
                self.assertIsNone(result['effective_effort'])

    def test_claude_spawn_requires_verified_effort_version(self):
        for version in [None, '2.1.291', 'unknown', '2.1.292-beta']:
            with self.subTest(version=version):
                result = self.select('claude', runtime='spawn', claude_version=version)
                self.assertEqual(result['application_method'], 'session_preset_required')
                self.assertTrue(any('version' in c for c in result['constraints']))
        for version in ['2.1.292', '2.2.0', 'v2.1.292', '2.1.292 (Claude Code)']:
            with self.subTest(version=version):
                self.assertEqual(self.select('claude', runtime='spawn', claude_version=version)['application_method'], 'spawn_overrides')

    def test_claude_full_model_ids_need_a_session_preset(self):
        self.policy['clients']['claude']['model_capabilities']['claude-custom-full-id'] = {
            'tier': 'deep', 'efforts': ['high'], 'default_effort': 'high', 'vision': True,
        }
        result = self.select('claude', model='claude-custom-full-id', runtime='spawn', claude_version='2.1.292')
        self.assertEqual(result['requested_model'], 'claude-custom-full-id')
        self.assertEqual(result['application_method'], 'session_preset_required')
        self.assertTrue(any('aliases only' in c for c in result['constraints']))

    def test_claude_fable_alias_can_be_declared_by_custom_policy(self):
        self.policy['clients']['claude']['model_capabilities']['fable'] = {
            'tier': 'balanced', 'efforts': ['medium'], 'default_effort': 'medium', 'vision': True,
        }
        result = self.select('claude', model='fable', runtime='spawn', claude_version='2.1.292')
        self.assertEqual(result['application_method'], 'spawn_overrides')

    def test_environment_defaults_warn_without_blocking_invocation(self):
        result = self.select('claude', runtime='spawn', claude_version='2.1.292', env={
            'ANTHROPIC_MODEL': 'other', 'CLAUDE_CODE_SUBAGENT_MODEL': 'haiku',
            'ANTHROPIC_DEFAULT_SONNET_MODEL': 'some-version',
        })
        self.assertEqual(result['requested_model'], 'sonnet')
        self.assertEqual(result['application_method'], 'spawn_overrides')
        self.assertEqual(result['constraints'], [])
        self.assertIsNone(result['effective_model'])
        self.assertTrue(any('alias resolution' in w for w in result['warnings']))

    def test_force_model_and_effort_environment_emit_constraints(self):
        for env in [{'CLAUDE_CODE_SUBAGENT_MODEL_FORCE': '1'}, {'CLAUDE_CODE_SUBAGENT_MODEL_FORCE': 'true', 'CLAUDE_CODE_SUBAGENT_MODEL': 'haiku'}, {'CLAUDE_CODE_EFFORT_LEVEL': 'high'}]:
            with self.subTest(env=env):
                result = self.select('claude', runtime='spawn', claude_version='2.1.292', env=env)
                self.assertEqual(result['application_method'], 'session_preset_required')
                self.assertTrue(result['constraints'])
                self.assertEqual((result['requested_model'], result['requested_effort']), ('sonnet', 'medium'))
                self.assertIsNone(result['effective_model'])
                self.assertIsNone(result['effective_effort'])

    def test_empty_effort_and_false_force_do_not_block(self):
        result = self.select('claude', runtime='spawn', claude_version='2.1.292', env={
            'CLAUDE_CODE_SUBAGENT_MODEL_FORCE': 'false', 'CLAUDE_CODE_EFFORT_LEVEL': '',
        })
        self.assertEqual(result['application_method'], 'spawn_overrides')

    def test_auto_and_unset_effort_environment_suppress_requested_effort(self):
        for effort in ('auto', 'unset'):
            with self.subTest(effort=effort):
                result = self.select('claude', runtime='spawn', claude_version='2.1.292', env={
                    'CLAUDE_CODE_EFFORT_LEVEL': effort,
                })
                self.assertEqual(result['application_method'], 'session_preset_required')
                self.assertTrue(any('suppresses the effort parameter' in c for c in result['constraints']))
                self.assertEqual(result['requested_effort'], 'medium')
                self.assertIsNone(result['effective_effort'])

    def test_none_environment_reads_process_without_changing_it(self):
        with patch.dict(selector.os.environ, {'CLAUDE_CODE_EFFORT_LEVEL': 'high'}, clear=True):
            before = dict(selector.os.environ)
            result = selector.select(self.policy, 'claude', runtime='session')
            self.assertTrue(result['constraints'])
            self.assertEqual(dict(selector.os.environ), before)

    def test_visual_auto_finds_capable_tier_without_lowering_minimum(self):
        self.policy['clients']['codex']['model_capabilities']['gpt-6.1-sol']['vision'] = False
        result = self.select(role='visual_advisor')
        self.assertEqual(result['tier'], 'deep')
        with self.assertRaisesRegex(selector.PolicyError, 'vision-capable'):
            self.select(role='visual_advisor', max_tier='balanced')
        with self.assertRaisesRegex(selector.PolicyError, 'vision capability'):
            self.select(role='visual_advisor', model='gpt-6.1-sol')

    def test_invalid_entire_policy_is_rejected_even_for_other_client(self):
        corruptions = [lambda p: p.update(version=True),
                       lambda p: p['auto']['role_minimums'].pop('project_manager'),
                       lambda p: p['clients']['claude']['model_capabilities']['sonnet'].update(vision='yes'),
                       lambda p: p['clients']['claude']['model_capabilities']['sonnet'].update(default_effort='max'),
                       lambda p: p['clients']['claude']['model_capabilities']['sonnet'].update(tier='unknown'),
                       lambda p: p['clients']['claude']['tiers']['balanced'].update(model='unknown'),
                       lambda p: p['clients']['claude']['model_capabilities']['sonnet'].update(efforts=['medium', 'medium'])]
        for corrupt in corruptions:
            with self.subTest(corrupt=corrupt):
                policy = copy.deepcopy(self.policy)
                corrupt(policy)
                with self.assertRaises(ValueError):
                    selector.select(policy, 'codex', env={})

    def test_invalid_inputs_are_rejected(self):
        for kwargs in [{'role': 'unknown'}, {'complexity': 'extreme'}, {'risk': 'none'}, {'tier': 'unknown'}, {'max_tier': 'auto'}, {'runtime': 'magic'}, {'escalation_count': True}, {'escalation_count': 2}, {'escalate': 1}, {'model': ''}, {'effort': ''}, {'env': []}, {'claude_version': 42}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.select(**kwargs)
        with self.assertRaises(ValueError):
            self.select('unknown')

    def test_selection_has_no_policy_mutation_or_subprocess_calls(self):
        before = copy.deepcopy(self.policy)
        with patch.object(subprocess, 'run', side_effect=AssertionError('No process should run')):
            first = self.select()
            second = self.select()
        self.assertEqual(first, second)
        self.assertEqual(self.policy, before)

    def test_custom_policy_file_and_cli_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / 'policy.json'
            policy_path.write_text(json.dumps(self.policy))
            self.assertEqual(selector.load_policy(policy_path), self.policy)
            result = subprocess.run([sys.executable, str(SCRIPT), '--policy', str(policy_path), '--client', 'codex', '--complexity', 'low'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['requested_model'], 'gpt-6-luna')
            policy_path.write_text('{invalid')
            result = subprocess.run([sys.executable, str(SCRIPT), '--policy', str(policy_path), '--client', 'codex'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Model plan rejected', result.stderr)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
