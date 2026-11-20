"""Muse settings tests; no client/API/model calls are made.

Kept separate from the codex/claude cases in test_model_settings.py so a
Muse failure never requires touching codex/claude tests to fix.

Muse has its own ``muse`` settings key and reads/writes nothing under
``codex`` or ``claude`` (and vice versa). Until a Muse settings schema
exists, resolution is defaults-only: the builtin tier/max_tier plus
whatever pins live under the ``muse`` key, resolved through the same
policy aliases T1 added to model-policy.json.
"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'model_settings.py'
POLICY_SCRIPT = Path(__file__).resolve().parents[1] / 'model_policy.py'
spec = importlib.util.spec_from_file_location('model_settings_muse', SCRIPT)
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class MuseSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.user = self.root / 'personal/model-settings.json'

    def write_document(self, document):
        self.user.parent.mkdir(parents=True, exist_ok=True)
        self.user.write_text(json.dumps(document))
        return document

    def resolve(self, client='muse', **kwargs):
        kwargs.setdefault('project', self.project)
        kwargs.setdefault('user_config', self.user)
        kwargs.setdefault('cwd', self.project)
        return settings.resolve(client, **kwargs)

    def batch(self, client, operations, scope='user', **kwargs):
        kwargs.setdefault('project', self.project)
        kwargs.setdefault('user_config', self.user)
        kwargs.setdefault('cwd', self.project)
        return settings.configure_batch(client, scope, operations, **kwargs)

    def test_muse_resolve_defaults_without_settings_file(self):
        result = self.resolve()
        self.assertEqual(result['values'], {'tier': 'auto', 'max_tier': 'deep'})
        self.assertEqual([layer['name'] for layer in result['layers']], ['builtin'])
        self.assertFalse(self.user.exists())

    def test_validate_accepts_muse_key_and_still_rejects_unknown_client(self):
        document = {'version': 1, 'clients': {'muse': {'defaults': {'tier': 'balanced'}}}}
        self.assertEqual(settings.validate(document), document)
        with self.assertRaisesRegex(ValueError, 'Unknown settings client'):
            settings.validate({'version': 1, 'clients': {'other': {}}})

    def test_muse_resolve_reads_only_muse_key(self):
        original = self.write_document({'version': 1, 'clients': {
            'codex': {'defaults': {'tier': 'deep'}},
            'claude': {'defaults': {'tier': 'economy'}},
            'muse': {'defaults': {'tier': 'balanced'}},
        }})
        before = self.user.read_bytes()
        result = self.resolve()
        self.assertEqual(result['values']['tier'], 'balanced')
        self.assertEqual(result['sources']['tier']['layer'], 'user.defaults')
        self.assertEqual(self.user.read_bytes(), before)
        self.assertEqual(json.loads(self.user.read_text()), original)

    def test_codex_claude_pins_do_not_leak_into_muse_resolve(self):
        self.write_document({'version': 1, 'clients': {
            'codex': {'defaults': {'tier': 'deep'}},
            'claude': {'defaults': {'tier': 'economy'}},
        }})
        result = self.resolve()
        self.assertEqual(result['values'], {'tier': 'auto', 'max_tier': 'deep'})
        self.assertEqual([layer['name'] for layer in result['layers']], ['builtin'])

    def test_muse_configure_batch_writes_only_muse_key(self):
        original = self.write_document({'version': 1, 'clients': {
            'codex': {'defaults': {'tier': 'balanced'}},
            'claude': {'defaults': {'model': 'opus'}},
        }})
        result = self.batch('muse', [{'action': 'set', 'stage': None, 'role': 'implementation-worker',
                                       'values': {'effort': 'high'}, 'fields': None}], apply=True)
        self.assertTrue(result['applied'])
        stored = json.loads(self.user.read_text())
        self.assertEqual(stored['clients']['codex'], original['clients']['codex'])
        self.assertEqual(stored['clients']['claude'], original['clients']['claude'])
        self.assertEqual(stored['clients']['muse']['roles']['implementation-worker'], {'effort': 'high'})

    def test_codex_configure_batch_leaves_muse_entry_untouched(self):
        original = self.write_document({'version': 1, 'clients': {
            'muse': {'defaults': {'tier': 'economy'}},
        }})
        result = self.batch('codex', [{'action': 'set', 'stage': None, 'role': 'implementation-worker',
                                       'values': {'tier': 'balanced'}, 'fields': None}], apply=True)
        self.assertTrue(result['applied'])
        stored = json.loads(self.user.read_text())
        self.assertEqual(stored['clients']['muse'], original['clients']['muse'])

    def test_muse_settings_cli_status_accepts_muse(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), 'status', '--client', 'muse',
             '--user-config', str(self.user), '--project', str(self.project)],
            capture_output=True, text=True, cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Unknown client', result.stderr)
        self.assertEqual(json.loads(result.stdout)['values'], {'tier': 'auto', 'max_tier': 'deep'})

    def test_muse_policy_cli_end_to_end(self):
        cases = (('project-manager', 'plan'), ('implementation-worker', 'implement'),
                 ('code-advisor', 'review'))
        for role, stage in cases:
            with self.subTest(role=role, stage=stage):
                result = subprocess.run(
                    [sys.executable, str(POLICY_SCRIPT), '--client', 'muse', '--role', role,
                     '--stage', stage, '--complexity', 'medium', '--risk', 'medium',
                     '--user-config', str(self.user), '--project', str(self.project)],
                    capture_output=True, text=True, cwd=self.project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn('Unknown client', result.stderr)
                plan = json.loads(result.stdout)
                self.assertEqual((plan['requested_model'], plan['requested_effort']), ('muse-balanced', 'medium'))
                self.assertEqual(plan['application_method'], 'plan_only')
                self.assertIsNone(plan['effective_model'])

    def test_unknown_client_still_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown client'):
            self.resolve('unknown')
        with self.assertRaisesRegex(ValueError, 'Invalid client/scope'):
            self.batch('unknown', [{'action': 'set', 'stage': None, 'role': None,
                                    'values': {'tier': 'balanced'}, 'fields': None}])


if __name__ == '__main__':
    unittest.main()
