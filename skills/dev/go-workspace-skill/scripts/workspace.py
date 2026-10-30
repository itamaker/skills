#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

CONFIG_ENV_VAR = "GO_WORKSPACE_SKILLS_CONFIG"
DEFAULT_CONFIG_NAMES = (".go-workspace.json", "go-workspace.json")


@dataclass(frozen=True)
class Repo:
    name: str
    url: str
    go_project: bool


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def example_manifest_path() -> Path:
    return skill_dir() / "assets" / "workspace.example.json"


def resolve_path(raw_path: str, root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def resolve_config_path(root: Path, explicit_config: str | None) -> Path:
    if explicit_config:
        path = resolve_path(explicit_config, root)
        if not path.exists():
            raise SystemExit(f"Workspace config not found: {path}")
        return path

    env_config = os.environ.get(CONFIG_ENV_VAR)
    if env_config:
        path = resolve_path(env_config, root)
        if not path.exists():
            raise SystemExit(f"Workspace config from {CONFIG_ENV_VAR} not found: {path}")
        return path

    candidates = [root / name for name in DEFAULT_CONFIG_NAMES]
    for path in candidates:
        if path.exists():
            return path

    candidate_list = ", ".join(str(path) for path in candidates)
    raise SystemExit(
        "No workspace config found. "
        f"Looked for {candidate_list}. "
        "Run 'init-config' to create one, or pass --config. "
        f"Example config: {example_manifest_path()}"
    )


def invalid_name_reason(name: str) -> str | None:
    """Why `name` cannot be a direct child directory of the workspace root, or None if it can."""
    if not name.strip():
        return "is empty"
    if name in (".", ".git"):
        return "must not be '.' or '.git'"
    if "/" in name or "\\" in name:
        return "must not contain '/' or '\\'"
    if ".." in name:
        return "must not contain '..'"
    if Path(name).is_absolute() or PureWindowsPath(name).is_absolute():
        return "must not be an absolute path"
    return None


def load_repos(config_path: Path) -> list[Repo]:
    try:
        data = json.loads(config_path.read_text())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Invalid config: cannot read {config_path}: {exc}")
    raw_repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(raw_repos, list) or not raw_repos:
        raise SystemExit(f"Invalid config: {config_path} must define a non-empty repos list")

    repos: list[Repo] = []
    seen: set[str] = set()

    for item in raw_repos:
        if not isinstance(item, dict):
            raise SystemExit(f"Invalid config: each repo entry in {config_path} must be an object")

        name = item.get("name")
        url = item.get("url")
        go_project = bool(item.get("go_project", False))

        if not isinstance(name, str) or not name:
            raise SystemExit(f"Invalid config: repo entry in {config_path} is missing a valid name")
        if not isinstance(url, str) or not url:
            raise SystemExit(f"Invalid config: repo '{name}' in {config_path} is missing a valid url")
        reason = invalid_name_reason(name)
        if reason:
            raise SystemExit(f"Invalid config: repo name {name!r} in {config_path} {reason}")
        if name in seen:
            raise SystemExit(f"Invalid config: duplicate repo name '{name}' in {config_path}")

        seen.add(name)
        repos.append(Repo(name=name, url=url, go_project=go_project))

    return repos


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage a configurable multi-repo Go workspace.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Workspace root to operate on. Defaults to the current directory.",
    )
    parser.add_argument(
        "--config",
        help="Optional path to the workspace config JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands and file operations without executing them.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Clone or fast-forward pull repositories.")
    sync_parser.add_argument("repos", nargs="*", help="Optional subset of repositories to sync.")

    subparsers.add_parser("build", help="Run go build ./... in each configured Go project.")
    subparsers.add_parser("test", help="Run go test ./... in each configured Go project.")

    clean_parser = subparsers.add_parser("clean", help="Delete configured repository paths.")
    clean_parser.add_argument(
        "--force",
        action="store_true",
        help="Required for destructive clean operations.",
    )
    clean_parser.add_argument(
        "--discard-changes",
        action="store_true",
        help="Also delete repos holding uncommitted work, unpushed commits or non-git directories.",
    )

    init_parser = subparsers.add_parser("init-config", help="Write an example workspace config.")
    init_parser.add_argument(
        "--output",
        help="Output path for the generated config. Defaults to <root>/.go-workspace.json.",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )

    repos_parser = subparsers.add_parser("list-repos", help="List managed repositories.")
    repos_parser.add_argument(
        "--format",
        choices=("lines", "shell", "json"),
        default="lines",
        help="Output format.",
    )

    projects_parser = subparsers.add_parser("list-projects", help="List Go project repositories.")
    projects_parser.add_argument(
        "--format",
        choices=("lines", "shell", "json"),
        default="lines",
        help="Output format.",
    )

    return parser.parse_args()


def workspace_root(raw_root: str) -> Path:
    root = Path(raw_root).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Workspace root does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Workspace root is not a directory: {root}")
    return root


def default_config_output(root: Path) -> Path:
    return root / DEFAULT_CONFIG_NAMES[0]


def write_example_config(root: Path, output: str | None, force: bool) -> None:
    destination = resolve_path(output, root) if output else default_config_output(root)
    if destination.exists() and not force:
        raise SystemExit(f"Config already exists: {destination}. Re-run with --force to overwrite.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(example_manifest_path().read_text())
    print(f"Wrote config template to {destination}")


def format_names(names: list[str], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(names)
    if output_format == "shell":
        return " ".join(names)
    return "\n".join(names)


def say(message: str = "") -> None:
    """Print and flush, so status lines stay ordered with child-process output on a pipe."""
    print(message, flush=True)


def run_command(cmd: list[str], *, cwd: Path | None = None, dry_run: bool) -> int:
    """Run cmd with output streaming; return its exit code (127 if it cannot start)."""
    prefix = "[dry-run] " if dry_run else ""
    rendered = " ".join(shlex.quote(part) for part in cmd)
    say(f"{prefix}{rendered}" + (f"  (cwd: {cwd})" if cwd is not None else ""))

    if dry_run:
        return 0

    try:
        return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode
    except OSError as exc:
        say(f"Cannot run {cmd[0]}: {exc}")
        return 127


def git_output(repo_dir: Path, *args: str) -> str:
    """Stdout of a read-only git command in repo_dir; raises RuntimeError if git fails."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except OSError as exc:
        raise RuntimeError(f"cannot run git: {exc}")
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.returncode}")
    return proc.stdout


def git_succeeds(repo_dir: Path, *args: str) -> bool:
    """True if a read-only git command exits 0 in repo_dir."""
    quiet = subprocess.DEVNULL
    return subprocess.run(["git", "-C", str(repo_dir), *args], stdout=quiet, stderr=quiet).returncode == 0


def local_work_reasons(repo_dir: Path) -> list[str]:
    """Reasons deleting repo_dir would lose work; empty means clean and fully pushed.

    "Pushed" means reachable from a remote-tracking ref as of the last fetch; no fetch is done.
    Fails closed: anything that cannot be verified is reported as a reason.
    """
    if repo_dir.is_symlink():
        return ["is a symlink"]
    if not (repo_dir / ".git").exists():
        return ["is not a git repository"]
    reasons: list[str] = []
    try:
        if git_output(repo_dir, "status", "--porcelain", "--untracked-files=all").strip():
            reasons.append("uncommitted or untracked changes")
        tips = ["--branches"]
        if not git_succeeds(repo_dir, "symbolic-ref", "-q", "HEAD") and git_succeeds(
            repo_dir, "rev-parse", "-q", "--verify", "HEAD"
        ):
            tips.append("HEAD")  # detached HEAD: its commits belong to no branch
        unpushed = int(git_output(repo_dir, "rev-list", "--count", *tips, "--not", "--remotes").strip())
        if unpushed:
            reasons.append(f"{unpushed} commit(s) not on any remote branch")
        if git_succeeds(repo_dir, "rev-parse", "-q", "--verify", "refs/stash"):
            reasons.append("stashed changes")
    except (RuntimeError, ValueError, OSError) as exc:
        reasons.append(f"could not verify: {exc}")
    return reasons


def selected_repos(all_repos: list[Repo], requested: list[str]) -> list[Repo]:
    if not requested:
        return all_repos

    by_name = {repo.name: repo for repo in all_repos}
    unknown = [name for name in requested if name not in by_name]
    if unknown:
        raise SystemExit(f"Unknown repo(s): {', '.join(unknown)}")

    return [by_name[name] for name in requested]


def remove_path(path: Path, *, dry_run: bool) -> bool:
    """Delete path (a symlink is unlinked, never followed). Return False if deletion failed."""
    say(f"{'[dry-run] ' if dry_run else ''}Removing {path.name}")
    if dry_run:
        return True
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
    except OSError as exc:
        say(f"FAILED to remove {path.name}: {exc}")
        return False
    return True


def print_summary(title: str, results: list[tuple[str, bool, str]]) -> int:
    """Print one status line per item; return 1 if any item failed, else 0."""
    say()
    say(f"{title}:")
    for name, ok, detail in results:
        say(f"  {'PASS' if ok else 'FAIL'} {name}" + (f" ({detail})" if detail else ""))
    failed = sum(1 for _, ok, _ in results if not ok)
    say(f"{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


def command_sync(root: Path, repos: list[Repo], dry_run: bool) -> int:
    results: list[tuple[str, bool, str]] = []
    for repo in repos:
        repo_dir = root / repo.name
        if (repo_dir / ".git").exists():
            say(f"Pulling {repo.name}")
            code = run_command(["git", "-C", str(repo_dir), "pull", "--ff-only"], dry_run=dry_run)
        elif repo_dir.exists():
            say(f"{repo.name} exists but is not a git repository")
            results.append((repo.name, False, "exists but is not a git repository; left untouched"))
            continue
        else:
            say(f"Cloning {repo.name}")
            code = run_command(["git", "clone", repo.url, str(repo_dir)], dry_run=dry_run)
        results.append((repo.name, code == 0, f"git exited {code}" if code else ""))
    return print_summary("Sync summary", results)


def command_go(root: Path, projects: list[Repo], subcommand: str, dry_run: bool) -> int:
    results: list[tuple[str, bool, str]] = []
    for project in projects:
        project_dir = root / project.name
        say(f"{subcommand.capitalize()}ing {project.name}")
        if not project_dir.is_dir():
            say(f"Missing directory {project_dir}; run sync first")
            results.append((project.name, False, "directory missing; run sync"))
            continue
        code = run_command(["go", subcommand, "./..."], cwd=project_dir, dry_run=dry_run)
        results.append((project.name, code == 0, f"go exited {code}" if code else ""))
    return print_summary(f"{subcommand.capitalize()} summary", results)


def command_clean(root: Path, repos: list[Repo], dry_run: bool, force: bool, discard: bool) -> int:
    if not force:
        raise SystemExit("clean requires --force")

    skipped: list[tuple[str, list[str]]] = []
    failed = 0
    for repo in repos:
        path = root / repo.name
        if not path.exists() and not path.is_symlink():
            say(f"Skipping {repo.name}: not found.")
            continue
        reasons = local_work_reasons(path)
        if reasons and not discard:
            say(f"SKIPPED {repo.name}: {'; '.join(reasons)}")
            skipped.append((repo.name, reasons))
            continue
        if reasons:
            say(f"Discarding {repo.name}: {'; '.join(reasons)}")
        if not remove_path(path, dry_run=dry_run):
            failed += 1

    if skipped:
        say()
        say(f"Skipped {len(skipped)} repo(s) holding local work; nothing was deleted for them:")
        for name, reasons in skipped:
            say(f"  {name}: {'; '.join(reasons)}")
        say("Re-run with --discard-changes to delete them too.")
    return 1 if skipped or failed else 0


def main() -> int:
    args = parse_args()
    root = workspace_root(args.root)

    if args.command == "init-config":
        write_example_config(root, args.output, args.force)
        return 0

    config_path = resolve_config_path(root, args.config)
    repos = load_repos(config_path)
    projects = [repo for repo in repos if repo.go_project]

    if args.command == "list-repos":
        print(format_names([repo.name for repo in repos], args.format))
        return 0

    if args.command == "list-projects":
        print(format_names([repo.name for repo in projects], args.format))
        return 0

    say(f"Workspace root: {root}")
    say(f"Config: {config_path}")

    if args.command == "sync":
        return command_sync(root, selected_repos(repos, args.repos), args.dry_run)

    if args.command in ("build", "test"):
        return command_go(root, projects, args.command, args.dry_run)

    if args.command == "clean":
        return command_clean(root, repos, args.dry_run, args.force, args.discard_changes)

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
