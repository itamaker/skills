"""Run scoped settings and planner commands in fresh, isolated processes."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[2]


class ModelCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.personal = self.root / 'personal/settings.json'
        self.project = self.root / 'project'
        self.project.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True, capture_output=True)
        self.other = self.root / 'other-project'
        self.other.mkdir()

    def run_script(self, name, *arguments, cwd=None, ok=True):
        result = subprocess.run([
            sys.executable, str(SKILL / 'scripts' / name), *map(str, arguments),
        ], cwd=cwd or self.project, capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def settings(self, action, *arguments, **kwargs):
        return self.run_script('model_settings.py', action, '--client', 'codex',
                               '--user-config', self.personal, '--project', self.project,
                               *arguments, **kwargs)

    def plan(self, *arguments, project=True, **kwargs):
        location = ['--project', project if isinstance(project, Path) else self.project] if project else []
        return self.run_script('model_policy.py', '--client', 'codex', '--complexity', 'low',
                               '--user-config', self.personal, *location, *arguments, **kwargs)

    def test_request_override_expires_without_writing_settings(self):
        self.assertEqual(self.plan()['tier'], 'economy')
        self.assertEqual(self.plan('--tier', 'deep')['tier'], 'deep')
        self.assertEqual(self.plan()['tier'], 'economy')
        self.assertFalse(self.personal.exists())
        self.assertFalse((self.project / '.shipyard').exists())

    def test_saved_scopes_reload_and_reset_reveals_personal_default(self):
        self.settings('set', '--scope', 'user', '--tier', 'balanced', '--apply')
        self.assertEqual(self.plan()['tier'], 'balanced')
        self.settings('set', '--scope', 'project', '--tier', 'economy', '--apply')
        self.assertEqual(self.plan()['tier'], 'economy')
        self.assertEqual(self.plan(project=self.other)['tier'], 'balanced')
        self.settings('reset', '--scope', 'project', '--apply')
        self.assertEqual(self.plan()['tier'], 'balanced')

    def test_explicit_auto_masks_saved_model_and_effort_for_this_request(self):
        self.settings('set', '--scope', 'user', '--tier', 'deep', '--effort', 'max', '--apply')
        result = self.plan('--tier', 'auto')
        self.assertEqual((result['tier'], result['requested_effort']), ('economy', 'low'))
        saved = self.plan()
        self.assertEqual((saved['tier'], saved['requested_effort']), ('deep', 'max'))

    def test_model_only_request_clears_inherited_effort(self):
        self.settings('set', '--scope', 'user', '--model', 'gpt-6.1-sol', '--effort', 'high', '--apply')
        result = self.plan('--model', 'gpt-6-luna')
        self.assertEqual((result['requested_model'], result['requested_effort']), ('gpt-6-luna', 'low'))

    def test_request_cannot_relax_saved_planning_ceiling(self):
        self.settings('set', '--scope', 'user', '--max-tier', 'economy', '--apply')
        self.assertEqual(self.plan()['tier'], 'economy')
        self.plan('--tier', 'deep', '--max-tier', 'deep', ok=False)
        self.plan('--risk', 'high', ok=False)

    def test_saved_custom_policy_reloads_from_another_working_directory(self):
        policy = json.loads((SKILL / 'assets/model-policy.json').read_text())
        policy['clients']['codex']['tiers']['balanced']['effort'] = 'high'
        path = self.project / 'custom-policy.json'
        path.write_text(json.dumps(policy))
        self.settings('set', '--scope', 'project', '--tier', 'balanced', '--policy', path, '--apply')
        result = self.plan(cwd=self.other)
        self.assertEqual(result['requested_effort'], 'high')
        self.assertEqual(Path(result['settings']['policy_path']), path)
        path.unlink()
        self.plan(ok=False)

    def test_project_role_default_does_not_change_other_roles(self):
        self.settings('set', '--scope', 'user', '--tier', 'balanced', '--apply')
        self.settings('set', '--scope', 'project', '--role', 'implementation_worker', '--tier', 'economy', '--apply')
        self.assertEqual(self.plan()['tier'], 'economy')
        self.assertEqual(self.plan('--role', 'code_advisor')['tier'], 'balanced')
        self.settings('reset', '--scope', 'project', '--role', 'implementation_worker', '--apply')
        self.assertEqual(self.plan()['tier'], 'balanced')

    def test_untrusted_or_ignored_project_keeps_personal_default(self):
        self.settings('set', '--scope', 'user', '--tier', 'balanced', '--apply')
        self.settings('set', '--scope', 'project', '--tier', 'deep', '--apply')
        self.assertEqual(self.plan(project=False)['tier'], 'balanced')
        self.assertEqual(self.plan('--trust-project', project=False)['tier'], 'deep')
        self.assertEqual(self.plan('--no-project-settings')['tier'], 'balanced')

    def test_project_mask_cannot_hide_an_invalid_personal_save(self):
        self.settings('set', '--scope', 'project', '--tier', 'balanced', '--apply')
        self.settings('set', '--scope', 'user', '--model', 'not-a-real-model', '--apply', ok=False)
        self.assertFalse(self.personal.exists())
        self.assertEqual(self.plan()['tier'], 'balanced')
        self.assertEqual(self.plan(project=self.other)['tier'], 'economy')


if __name__ == '__main__':
    unittest.main()
