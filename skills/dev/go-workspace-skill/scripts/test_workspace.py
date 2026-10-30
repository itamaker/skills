"""Tests for workspace.py. Stdlib only; fixtures are local bare repos over file:// (no network).

Run from this directory: python3 -I -m unittest
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "workspace.py"
ENV = dict(
    os.environ,
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_AUTHOR_NAME="t",
    GIT_AUTHOR_EMAIL="t@t",
    GIT_COMMITTER_NAME="t",
    GIT_COMMITTER_EMAIL="t@t",
    GOTOOLCHAIN="local",
    GOWORK="off",
)
GOOD = "package main\n\nfunc main() {}\n"
BROKEN = "package main\n\nfunc main() { undefined_symbol() }\n"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=str(cwd), env=ENV, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class Fixture(unittest.TestCase):
    """A workspace of repos cloned from local bare remotes."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gows-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.ws = self.tmp / "ws"
        self.ws.mkdir()
        self.repos = []

    def add_repo(self, name, source=GOOD, clone=True):
        """Create a bare remote with one commit and (by default) clone it into the workspace."""
        bare, seed = self.tmp / "remotes" / (name + ".git"), self.tmp / "seed" / name
        bare.mkdir(parents=True)
        seed.mkdir(parents=True)
        git(bare, "init", "--bare", "-b", "main")
        git(seed, "init", "-b", "main")
        (seed / "go.mod").write_text("module m/%s\n\ngo 1.21\n" % name)
        (seed / "main.go").write_text(source)
        (seed / "README").write_text("v1\n")
        git(seed, "add", "-A")
        git(seed, "commit", "-m", "init")
        git(seed, "push", str(bare), "main")
        if clone:
            git(self.ws, "clone", str(bare), name)
        self.repos.append({"name": name, "url": bare.as_uri(), "go_project": True})

    def push_upstream(self, name, text="v2\n"):
        seed = self.tmp / "seed" / name
        (seed / "README").write_text(text)
        git(seed, "commit", "-am", "v2")
        git(seed, "push", str(self.tmp / "remotes" / (name + ".git")), "main")

    def write_config(self, repos=None):
        (self.ws / ".go-workspace.json").write_text(json.dumps({"repos": repos or self.repos}))

    def run_ws(self, *args):
        if not (self.ws / ".go-workspace.json").exists():
            self.write_config()
        proc = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--root", str(self.ws), *args],
            env=ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        return proc.returncode, proc.stdout

    def present(self):
        return sorted(p.name for p in self.ws.iterdir() if not p.name.startswith("."))


class CleanTests(Fixture):
    def setUp(self):
        super().setUp()
        for name in ("pristine", "dirty", "ahead", "untracked"):
            self.add_repo(name)
        (self.ws / "dirty" / "README").write_text("local edit\n")
        (self.ws / "untracked" / "scratch.txt").write_text("new\n")
        (self.ws / "ahead" / "extra").write_text("x\n")
        git(self.ws / "ahead", "add", "-A")
        git(self.ws / "ahead", "commit", "-m", "not pushed")

    def test_clean_skips_local_work_and_removes_the_rest(self):
        code, out = self.run_ws("clean", "--force")
        self.assertEqual(self.present(), ["ahead", "dirty", "untracked"])
        self.assertNotEqual(code, 0)
        self.assertIn("SKIPPED dirty: uncommitted or untracked changes", out)
        self.assertIn("SKIPPED untracked: uncommitted or untracked changes", out)
        self.assertIn("SKIPPED ahead: 1 commit(s) not on any remote branch", out)
        self.assertEqual((self.ws / "dirty" / "README").read_text(), "local edit\n")

    def test_non_git_directory_is_skipped(self):
        (self.ws / "plain").mkdir()
        (self.ws / "plain" / "f").write_text("data")
        self.repos.append({"name": "plain", "url": "file:///none", "go_project": False})
        self.write_config()
        out = self.run_ws("clean", "--force")[1]
        self.assertIn("SKIPPED plain: is not a git repository", out)
        self.assertTrue((self.ws / "plain" / "f").exists())

    def test_discard_changes_removes_everything(self):
        code, out = self.run_ws("clean", "--force", "--discard-changes")
        self.assertEqual((code, self.present()), (0, []))
        self.assertIn("Discarding dirty", out)

    def test_requires_force(self):
        self.assertNotEqual(self.run_ws("clean")[0], 0)
        self.assertEqual(len(self.present()), 4)

    def test_dry_run_changes_nothing(self):
        code, out = self.run_ws("--dry-run", "clean", "--force", "--discard-changes")
        self.assertEqual(len(self.present()), 4)
        self.assertEqual((self.ws / "dirty" / "README").read_text(), "local edit\n")
        self.assertIn("Removing pristine", out)


@unittest.skipUnless(shutil.which("go"), "go is not installed")
class GoTests(Fixture):
    def setUp(self):
        super().setUp()
        self.add_repo("first")
        self.add_repo("broken", source=BROKEN)
        self.add_repo("last")

    def check(self, action):
        code, out = self.run_ws(action)
        summary = out.split("%s summary:" % action.capitalize())[-1].splitlines()
        self.assertNotEqual(code, 0)
        self.assertIn("  PASS first", summary)
        self.assertIn("  FAIL broken (go exited 1)", summary)
        self.assertIn("  PASS last", summary)  # ran after the failure
        self.assertIn("2 passed, 1 failed", summary)

    def test_build_continues_past_failure(self):
        self.check("build")

    def test_test_continues_past_failure(self):
        self.check("test")

    def test_all_passing_exits_zero(self):
        shutil.rmtree(str(self.ws / "broken"))
        self.write_config([r for r in self.repos if r["name"] != "broken"])
        self.assertEqual(self.run_ws("build")[0], 0)

    def test_missing_project_dir_is_reported_not_fatal(self):
        shutil.rmtree(str(self.ws / "first"))
        code, out = self.run_ws("build")
        self.assertNotEqual(code, 0)
        self.assertIn("  FAIL first (directory missing; run sync)", out)
        self.assertIn("  PASS last", out)


class SyncTests(Fixture):
    def test_dirty_repo_is_reported_and_others_still_sync(self):
        for name in ("one", "conflicted", "two"):
            self.add_repo(name)
        self.add_repo("fresh", clone=False)
        (self.ws / "conflicted" / "README").write_text("local edit\n")
        for name in ("one", "conflicted", "two"):
            self.push_upstream(name)
        code, out = self.run_ws("sync")
        summary = out.split("Sync summary:")[-1].splitlines()
        self.assertNotEqual(code, 0)
        self.assertIn("  FAIL conflicted (git exited 1)", summary)
        self.assertIn("  PASS two", summary)
        self.assertEqual((self.ws / "one" / "README").read_text(), "v2\n")
        self.assertEqual((self.ws / "two" / "README").read_text(), "v2\n")
        self.assertEqual((self.ws / "conflicted" / "README").read_text(), "local edit\n")
        self.assertTrue((self.ws / "fresh" / "README").exists())  # cloned after the failure


class NameValidationTests(Fixture):
    def test_unsafe_names_are_rejected(self):
        for bad in ("", ".", "..", ".git", "../x", "a/b", "a\\b", "/abs", "x..y"):
            with self.subTest(name=bad):
                self.write_config([{"name": bad, "url": "file:///none", "go_project": False}])
                for action in (["list-repos"], ["clean", "--force"]):
                    code, out = self.run_ws(*action)
                    self.assertNotEqual(code, 0)
                    self.assertIn("Invalid config", out)
                    self.assertEqual(len(out.strip().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
