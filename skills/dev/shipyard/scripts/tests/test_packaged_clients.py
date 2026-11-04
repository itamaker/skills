"""Verify the actual skill assets install and launch without a dotfiles checkout."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest


SKILL = Path(__file__).resolve().parents[2]


class PackagedClientsTests(unittest.TestCase):
    def test_standalone_install_and_codex_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            for directory in ['.agents/skills', '.claude/skills']:
                entry = home / directory
                entry.mkdir(parents=True)
                (entry / 'shipyard').symlink_to(SKILL, target_is_directory=True)
            (home / '.codex').mkdir()
            global_config = home / '.codex/config.toml'
            global_config.write_text('model = "existing-model"\n')
            global_settings = home / '.claude/settings.json'
            global_settings.write_text('{"existing": true}\n')
            subprocess.run([
                sys.executable, str(SKILL / 'scripts/install_clients.py'),
                '--home', str(home), '--client', 'both', '--apply',
            ], check=True, capture_output=True, text=True)
            launcher = home / '.codex/chief-of-staff'
            self.assertTrue(launcher.stat().st_mode & 0o111)
            output = subprocess.check_output([
                sys.executable, str(launcher), '--print-command', 'prompt with spaces',
            ], text=True)
            argv = json.loads(output)
            self.assertEqual(argv[0], 'codex')
            self.assertEqual(argv[-1], 'prompt with spaces')
            paths = []
            for argument in argv[2:-1:2]:
                parsed = tomllib.loads(argument)
                for data in parsed.get('agents', {}).values():
                    if 'config_file' in data:
                        paths.append(Path(data['config_file']))
            self.assertEqual(len(paths), 9)
            self.assertTrue(all(p.is_file() and home in p.parents for p in paths))
            self.assertEqual(len(list((home / '.claude/agents').glob('*.md'))), 9)
            self.assertEqual(global_config.read_text(), 'model = "existing-model"\n')
            self.assertEqual(global_settings.read_text(), '{"existing": true}\n')


if __name__ == '__main__':
    unittest.main()
