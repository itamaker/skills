"""Muse planner tests; no client/API/model calls are made.

Kept separate from the codex/claude cases in test_model_policy.py so a
Muse failure never requires touching codex/claude tests to fix.
"""

import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'model_policy.py'
spec = importlib.util.spec_from_file_location('model_policy_muse', SCRIPT)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

MUSE_MODELS = {'economy': 'muse-economy', 'balanced': 'muse-balanced', 'deep': 'muse-deep'}
ROLES = ('project-manager', 'implementation-worker', 'code-advisor')
LEVELS = ('low', 'medium', 'high')


class MusePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = selector.load_policy()

    def select(self, client='muse', **kwargs):
        kwargs.setdefault('env', {})
        return selector.select(self.policy, client, **kwargs)

    def test_muse_defaults_record_requested_without_applying(self):
        result = self.select()
        self.assertEqual((result['requested_model'], result['requested_effort']), ('muse-balanced', 'medium'))
        self.assertEqual(result['tier'], 'balanced')
        self.assertIsNone(result['effective_model'])
        self.assertIsNone(result['effective_effort'])
        self.assertEqual(result['application_method'], 'plan_only')

    def test_muse_uses_same_tier_table_as_codex(self):
        for role in ROLES:
            for complexity in LEVELS:
                for risk in LEVELS:
                    with self.subTest(role=role, complexity=complexity, risk=risk):
                        muse = self.select(role=role, complexity=complexity, risk=risk)
                        codex = self.select('codex', role=role, complexity=complexity, risk=risk)
                        self.assertEqual(muse['tier'], codex['tier'])
                        self.assertEqual(muse['recommended_tier'], codex['recommended_tier'])
                        self.assertEqual(muse['requested_model'], MUSE_MODELS[muse['tier']])

    def test_muse_constraints_present_for_every_runtime(self):
        for runtime in ('unknown', 'fixed', 'spawn', 'session'):
            with self.subTest(runtime=runtime):
                result = self.select(runtime=runtime)
                self.assertEqual(result['application_method'], 'plan_only')
                for expected in selector.muse_constraints():
                    self.assertIn(expected, result['constraints'])
                self.assertTrue(any('recorded only and never applied' in c for c in result['constraints']))
                self.assertTrue(any('remain unknown' in c for c in result['constraints']))
                self.assertTrue(any('does not change the model' in c for c in result['constraints']))
                self.assertIsNone(result['effective_model'])
                self.assertIsNone(result['effective_effort'])

    def test_muse_never_claims_a_model_changed(self):
        for runtime in ('unknown', 'fixed', 'spawn', 'session'):
            with self.subTest(runtime=runtime):
                result = self.select(runtime=runtime)
                self.assertEqual(result['application_method'], 'plan_only')
                self.assertIsNone(result['effective_model'])
                self.assertIsNone(result['effective_effort'])

    def test_muse_explicit_model_and_effort_are_recorded_only(self):
        result = self.select(model='muse-deep')
        self.assertEqual((result['tier'], result['requested_effort']), ('deep', 'high'))
        self.assertEqual(result['application_method'], 'plan_only')
        self.assertIsNone(result['effective_model'])
        result = self.select(model='muse-economy', effort='high')
        self.assertEqual((result['requested_model'], result['requested_effort']), ('muse-economy', 'high'))
        self.assertIsNone(result['effective_effort'])

    def test_muse_policy_validation_requires_codex_and_claude(self):
        self.assertEqual(selector.load_policy(), self.policy)
        for mutate in (lambda p: p['clients'].pop('claude'),
                       lambda p: p['clients'].pop('codex'),
                       lambda p: p['clients'].update({'other': p['clients']['muse']}),
                       lambda p: p.update(clients={'muse': p['clients']['muse']})):
            with self.subTest(mutate=mutate):
                policy = copy.deepcopy(self.policy)
                mutate(policy)
                with self.assertRaises(ValueError):
                    selector.select(policy, 'muse', env={})

    def test_muse_selection_has_no_policy_mutation(self):
        before = copy.deepcopy(self.policy)
        first = self.select(role='code-advisor', complexity='high', risk='high')
        second = self.select(role='code-advisor', complexity='high', risk='high')
        self.assertEqual(first, second)
        self.assertEqual(self.policy, before)

    def test_unknown_client_still_rejected(self):
        with self.assertRaises(selector.PolicyError):
            self.select('unknown')


if __name__ == '__main__':
    unittest.main()
