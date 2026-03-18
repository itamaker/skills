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
from pathlib import Path

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


def load_repos(config_path: Path) -> list[Repo]:
    data = json.loads(config_path.read_text())
    raw_repos = data.get("repos")
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


def run_command(cmd: list[str], *, cwd: Path | None = None, dry_run: bool) -> None:
    prefix = "[dry-run] " if dry_run else ""
    rendered = " ".join(shlex.quote(part) for part in cmd)
    if cwd is not None:
        print(f"{prefix}{rendered}  (cwd: {cwd})")
    else:
        print(f"{prefix}{rendered}")

    if dry_run:
        return

    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def selected_repos(all_repos: list[Repo], requested: list[str]) -> list[Repo]:
    if not requested:
        return all_repos

    by_name = {repo.name: repo for repo in all_repos}
    unknown = [name for name in requested if name not in by_name]
    if unknown:
        raise SystemExit(f"Unknown repo(s): {', '.join(unknown)}")

    return [by_name[name] for name in requested]


def remove_path(path: Path, *, dry_run: bool) -> None:
    if not path.exists() and not path.is_symlink():
        print(f"Skipping {path.name}: not found.")
        return

    print(f"Removing {path.name}")
    if dry_run:
        return

    if path.is_symlink() or path.is_file():
        path.unlink()
        return

    shutil.rmtree(path)


def ensure_projects_exist(root: Path, projects: list[Repo]) -> None:
    missing = [project.name for project in projects if not (root / project.name).is_dir()]
    if missing:
        raise SystemExit(
            "Missing project directories: "
            + ", ".join(missing)
            + ". Run sync first or choose the correct --root."
        )


def command_sync(root: Path, repos: list[Repo], dry_run: bool) -> None:
    for repo in repos:
        repo_dir = root / repo.name
        git_marker = repo_dir / ".git"

        if git_marker.exists():
            print(f"Pulling {repo.name}")
            run_command(["git", "-C", str(repo_dir), "pull", "--ff-only"], dry_run=dry_run)
        elif repo_dir.exists():
            print(f"Skipping {repo.name}: {repo.name} exists but is not a git repository.")
        else:
            print(f"Cloning {repo.name}")
            run_command(["git", "clone", repo.url, str(repo_dir)], dry_run=dry_run)


def command_go(root: Path, projects: list[Repo], subcommand: str, dry_run: bool) -> None:
    ensure_projects_exist(root, projects)

    for project in projects:
        project_dir = root / project.name
        print(f"{subcommand.capitalize()}ing {project.name}")
        run_command(["go", subcommand, "./..."], cwd=project_dir, dry_run=dry_run)


def command_clean(root: Path, repos: list[Repo], dry_run: bool, force: bool) -> None:
    if not force:
        raise SystemExit("clean requires --force")

    for repo in repos:
        remove_path(root / repo.name, dry_run=dry_run)


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

    print(f"Workspace root: {root}")
    print(f"Config: {config_path}")

    if args.command == "sync":
        command_sync(root, selected_repos(repos, args.repos), args.dry_run)
        return 0

    if args.command == "build":
        command_go(root, projects, "build", args.dry_run)
        return 0

    if args.command == "test":
        command_go(root, projects, "test", args.dry_run)
        return 0

    if args.command == "clean":
        command_clean(root, repos, args.dry_run, args.force)
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
