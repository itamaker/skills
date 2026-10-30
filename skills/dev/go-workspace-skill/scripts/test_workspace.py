"""Tests for workspace.py. Stdlib only; fixtures are local bare repos over file:// (no network).

Run from this directory: python3 -I -m unittest
"""

import json
import os
import shutil
import signal
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


def git(cwd, *args, env=None):
    subprocess.run(["git", *args], cwd=str(cwd), env=dict(ENV, **(env or {})), check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def snapshot(path):
    """Every file under path with its bytes: equal snapshots mean nothing on disk changed."""
    return {str(f.relative_to(path)): f.read_bytes() for f in sorted(path.rglob("*")) if f.is_file()}


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

    def run_ws(self, *args, env=None):
        if not (self.ws / ".go-workspace.json").exists():
            self.write_config()
        proc = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--root", str(self.ws), *args],
            env=dict(ENV, **(env or {})),
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

    def test_discard_changes_removes_only_named_repos(self):
        code, out = self.run_ws("clean", "--force", "--discard-changes", "dirty", "ahead")
        self.assertEqual(self.present(), ["untracked"])
        self.assertEqual(code, 1)  # untracked is still skipped
        self.assertIn("Discarding dirty", out)
        self.assertIn("SKIPPED untracked", out)

    def test_discard_changes_all_named_exits_zero(self):
        code, _ = self.run_ws("clean", "--force", "--discard-changes", "dirty", "ahead", "untracked")
        self.assertEqual((code, self.present()), (0, []))

    def test_discard_changes_unknown_name_deletes_nothing(self):
        code, out = self.run_ws("clean", "--force", "--discard-changes", "dirty", "nope")
        self.assertNotEqual(code, 0)
        self.assertIn("nope", out)
        self.assertEqual(len(self.present()), 4)

    def test_discard_changes_needs_names(self):
        self.assertNotEqual(self.run_ws("clean", "--force", "--discard-changes")[0], 0)
        self.assertEqual(len(self.present()), 4)

    def test_requires_force(self):
        self.assertNotEqual(self.run_ws("clean")[0], 0)
        self.assertEqual(len(self.present()), 4)

    def test_dry_run_changes_nothing(self):
        code, out = self.run_ws("--dry-run", "clean", "--force", "--discard-changes", "dirty", "ahead", "untracked")
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
        for bad in ("", ".", "..", ".git", ".GIT", ".Git", "../x", "a/b", "a\\b", "/abs", "x..y", "c:x", "x.", "x "):
            with self.subTest(name=bad):
                self.write_config([{"name": bad, "url": "file:///none", "go_project": False}])
                for action in (["list-repos"], ["clean", "--force"]):
                    code, out = self.run_ws(*action)
                    self.assertNotEqual(code, 0)
                    self.assertIn("Invalid config", out)
                    self.assertEqual(len(out.strip().splitlines()), 1)


class ProbeTests(Fixture):
    """Each state below is clean-and-pushed as far as a naive check can tell, yet holds unsaved work."""

    def skipped(self, name, reason, env=None):
        code, out = self.run_ws("clean", "--force", env=env)
        line = [l for l in out.splitlines() if l.startswith("SKIPPED %s:" % name)]
        self.assertTrue(line, out)
        self.assertIn(reason, line[0])
        self.assertTrue((self.ws / name).is_dir())
        self.assertEqual(code, 1)

    def test_ignored_file_from_info_exclude(self):
        self.add_repo("r")
        (self.ws / "r" / ".git" / "info" / "exclude").write_text(".env\ngo.work\n")
        (self.ws / "r" / ".env").write_text("SECRET=1\n")
        (self.ws / "r" / "go.work").write_text("go 1.21\n")
        self.skipped("r", "ignored files present: .env, go.work (2)")

    def test_ignored_file_from_users_global_excludes_file(self):
        self.add_repo("r")
        (self.tmp / "ignore").write_text("*.local.*\n")
        (self.tmp / "gitconfig").write_text("[core]\n\texcludesFile = %s\n" % (self.tmp / "ignore"))
        (self.ws / "r" / "app.local.json").write_text("{}")
        self.skipped("r", "ignored files present: app.local.json", env={"GIT_CONFIG_GLOBAL": str(self.tmp / "gitconfig")})

    def test_linked_worktrees(self):
        self.add_repo("main")
        git(self.ws / "main", "worktree", "add", str(self.ws / "linked"), "-b", "feature")
        self.repos.append({"name": "linked", "url": "file:///none", "go_project": False})
        self.write_config()
        code, out = self.run_ws("clean", "--force")
        self.assertIn("SKIPPED main: has linked worktrees: %s" % (self.ws / "linked").resolve(), out)
        self.assertIn("SKIPPED linked: is a linked worktree or submodule checkout", out)
        self.assertEqual(self.present(), ["linked", "main"])

    def test_commits_only_reachable_from_a_tag(self):
        self.add_repo("r")
        git(self.ws / "r", "checkout", "-b", "tmp")
        (self.ws / "r" / "f").write_text("x")
        git(self.ws / "r", "add", "-A")
        git(self.ws / "r", "commit", "-m", "tagged")
        git(self.ws / "r", "tag", "keep")
        git(self.ws / "r", "checkout", "main")
        git(self.ws / "r", "branch", "-D", "tmp")
        self.skipped("r", "1 commit(s) not on any remote branch")

    def test_stash(self):
        self.add_repo("r")
        (self.ws / "r" / "README").write_text("wip\n")
        git(self.ws / "r", "stash")
        self.skipped("r", "stashed changes")

    def test_detached_head_commit(self):
        self.add_repo("r")
        git(self.ws / "r", "checkout", "--detach")
        (self.ws / "r" / "f").write_text("x")
        git(self.ws / "r", "add", "-A")
        git(self.ws / "r", "commit", "-m", "detached")
        self.skipped("r", "1 commit(s) not on any remote branch")

    def test_repo_without_remote(self):
        (self.ws / "r").mkdir()
        git(self.ws / "r", "init", "-b", "main")
        git(self.ws / "r", "commit", "--allow-empty", "-m", "only here")
        self.repos.append({"name": "r", "url": "file:///none", "go_project": False})
        self.write_config()
        self.skipped("r", "1 commit(s) not on any remote branch")

    def test_changes_hidden_by_assume_unchanged_and_skip_worktree(self):
        self.add_repo("a")
        self.add_repo("b")
        for name, flag in (("a", "--assume-unchanged"), ("b", "--skip-worktree")):
            git(self.ws / name, "update-index", flag, "README")
            (self.ws / name / "README").write_text("hidden edit\n")
        self.skipped("a", "hidden from status")
        self.skipped("b", "hidden from status")

    def test_initialized_submodule_even_when_user_config_hides_it(self):
        self.add_repo("sup")
        self.add_repo("lib", clone=False)
        sup = self.ws / "sup"
        git(sup, "-c", "protocol.file.allow=always", "submodule", "add", self.repos[-1]["url"], "libdir")
        git(sup, "config", "-f", ".gitmodules", "submodule.libdir.ignore", "all")
        git(sup, "commit", "-am", "add submodule")
        git(sup, "push", "origin", "main")
        (sup / "libdir" / "wip.txt").write_text("unsaved")
        (self.tmp / "gitconfig").write_text("[diff]\n\tignoreSubmodules = all\n")
        self.skipped("sup", "has initialized submodules", env={"GIT_CONFIG_GLOBAL": str(self.tmp / "gitconfig")})

    def test_probing_does_not_modify_the_repo(self):
        self.add_repo("r")
        os.utime(str(self.ws / "r" / "README"), (946684800, 946684800))  # stale stat data: plain `git status` rewrites the index
        before = snapshot(self.ws / "r")
        self.assertEqual(self.run_ws("--dry-run", "clean", "--force")[0], 0)
        self.assertEqual(snapshot(self.ws / "r"), before)


class GoEdgeTests(Fixture):
    def test_zero_go_projects_is_an_error(self):
        self.add_repo("docs")
        self.write_config([dict(self.repos[0], go_project=False)])
        code, out = self.run_ws("build")
        self.assertEqual(code, 1)
        self.assertIn("no Go projects", out)

    def test_ctrl_c_prints_summary_and_exits_130(self):
        self.add_repo("slow")
        self.write_config()
        fake = self.tmp / "bin"
        fake.mkdir()
        (fake / "go").write_text("#!/bin/sh\nexec sleep 30\n")
        (fake / "go").chmod(0o755)
        proc = subprocess.Popen(
            [sys.executable, "-I", str(SCRIPT), "--root", str(self.ws), "build"],
            env=dict(ENV, PATH="%s%s%s" % (fake, os.pathsep, ENV["PATH"])),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
            preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL),  # a backgrounded runner may ignore SIGINT
        )
        self.addCleanup(proc.kill)
        for line in proc.stdout:
            if line.startswith("go build"):
                break
        proc.send_signal(signal.SIGINT)
        out = proc.communicate(timeout=20)[0]
        self.assertEqual(proc.returncode, 130)
        self.assertIn("FAIL slow (interrupted)", out)
        self.assertNotIn("Traceback", out)


if __name__ == "__main__":
    unittest.main()
