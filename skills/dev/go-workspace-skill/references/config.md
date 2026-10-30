# Workspace Config Reference

The workspace config file is the source of truth for any given workspace.

Lookup order:

- `--config /path/to/file.json`
- `GO_WORKSPACE_SKILLS_CONFIG=/path/to/file.json`
- `<workspace-root>/.go-workspace.json`
- `<workspace-root>/go-workspace.json`

If no config exists yet, run `scripts/run.sh --root /path/to/workspace init-config` and then edit the generated file.

## Config Schema

The config file is JSON with a top-level `repos` array:

```json
{
  "repos": [
    {
      "name": "example-cli",
      "url": "https://github.com/example/example-cli.git",
      "go_project": true
    }
  ]
}
```

Each repo object requires:

- `name`: local directory name and selection key for `sync <repo...>`. It must be a plain directory name: not empty, not `.` or `.git`, not absolute, and without `/`, `\` or `..`. A config with any other name is rejected on load with a one-line error, so no command can touch a path outside the workspace root.
- `url`: clone URL for `git clone`
- `go_project`: whether `build` and `test` should run in this repo

## Command Semantics

Exit status is 0 only when every repo succeeded.

- `sync [repo...]`: With no names, sync every configured repository; named repos must be in the config. Clone a missing repo, run `git pull --ff-only` in an existing one. A repo that fails (clone error, non-fast-forward, detached HEAD, local changes that conflict with the pull, a non-git directory in the way) is reported and the loop continues to the next. A summary lists PASS/FAIL per repo; exit 1 if any failed. `--ff-only` never merges or overwrites local work, so a repo with unrelated uncommitted changes still pulls.
- `build`: Run `go build ./...` in every Go project. Each command streams its output. Every project runs even after a failure; a missing project directory or missing `go` binary counts as that project's FAIL. A summary lists PASS/FAIL per project; exit 1 if any failed.
- `test`: Same as `build`, with `go test ./...`.
- `list-repos [--format lines|shell|json]`: Print every configured repo's `name`. `lines` (default) is newline-separated, `shell` is space-separated, `json` is a JSON array.
- `list-projects [--format lines|shell|json]`: Same as `list-repos`, but filtered to repos where `go_project` is true.
- `clean --force [--discard-changes]`: Delete configured repository directories that hold no local work. A repo is skipped, with its reason printed, when it has:
  - uncommitted or untracked changes (gitignored files do not count and are deleted with the repo),
  - commits not reachable from any remote-tracking branch (includes a detached HEAD, and a repo with no remote), judged by the last fetch; clean never fetches,
  - a stash,
  - no `.git`, or is a symlink,
  - a git state it could not read (skipped rather than assumed clean).

  Skipped repos stay on disk and the command exits 1. A repo not found on disk is ignored. `--discard-changes` deletes the skipped repos as well, printing a `Discarding` line with each reason first; a symlink is unlinked, never followed. A repo that cannot be removed is reported and exits 1. `--dry-run` runs the same checks and deletes nothing.
- `init-config [--output PATH] [--force]`: Write `assets/workspace.example.json` into the workspace as a starting point. Defaults to `<root>/.go-workspace.json`; `--output` writes elsewhere; `--force` overwrites an existing file (the command fails otherwise).

## Tests

`cd scripts && python3 -I -m unittest` runs `test_workspace.py`: stdlib only, local bare repos over `file://`, no network; the Go tests need `go` on PATH.
