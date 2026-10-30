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

- `name`: local directory name and selection key for `sync <repo...>`. It must be a plain directory name: not empty, not `.` or `.git` (any case), not absolute, not ending in `.` or a space, and without `/`, `\`, `:` or `..`. A config with any other name is rejected on load with a one-line error, so a name cannot step outside the workspace root. A symlinked entry is still followed by `sync` and `build`/`test`; `clean` skips it.
- `url`: clone URL for `git clone`
- `go_project`: whether `build` and `test` should run in this repo

## Command Semantics

Exit status is 0 only when every repo succeeded.

- `sync [repo...]`: With no names, sync every configured repository; named repos must be in the config. Clone a missing repo (`git clone -- URL DIR`), run `git pull --ff-only` in an existing one. A repo that fails (clone error, non-fast-forward, detached HEAD, local changes that conflict with the pull, a non-git directory in the way) is reported and the loop continues to the next. A summary lists PASS/FAIL per repo; exit 1 if any failed. `--ff-only` never merges or overwrites local work, so a repo with unrelated uncommitted changes still pulls.
- `build`: Run `go build ./...` in every Go project. Each command streams its output. Every project runs even after a failure; a missing project directory or missing `go` binary counts as that project's FAIL. A summary lists PASS/FAIL per project; exit 1 if any failed, and also exit 1 with a warning when no repo has `go_project: true`.
- `test`: Same as `build`, with `go test ./...`.
- Ctrl-C during `sync`, `build` or `test` prints the summary so far (the interrupted repo as FAIL) and exits 130; during `clean` it stops and exits 130.
- `list-repos [--format lines|shell|json]`: Print every configured repo's `name`. `lines` (default) is newline-separated, `shell` is space-separated, `json` is a JSON array.
- `list-projects [--format lines|shell|json]`: Same as `list-repos`, but filtered to repos where `go_project` is true.
- `clean --force [--discard-changes NAME [NAME ...]]`: Delete configured repository directories that hold no local work. A repo is skipped, with its reason printed, when it has:
  - uncommitted or untracked changes (submodule changes included, whatever `submodule.<n>.ignore` says), or files hidden by assume-unchanged or skip-worktree,
  - ignored files (`git ls-files --others --ignored --exclude-standard`); build artifacts cause false skips, which is the safe direction,
  - a stash,
  - commits reachable from any ref (`--all`: branches, tags, notes, HEAD) but from no remote-tracking branch, judged by the last fetch; clean never fetches,
  - linked worktrees, or is itself a linked worktree or submodule checkout (`.git` is a file),
  - initialized submodules,
  - no `.git`, or is a symlink,
  - a git state it could not read (skipped rather than assumed clean).

  Skipped repos stay on disk and the command exits 1. A repo not found on disk is ignored. `--discard-changes` deletes only the named repos that were skipped, printing a `Discarding` line with each reason first; every other skipped repo stays skipped and is reported, and a name not in the config is an error before anything is deleted. A named repo that holds no local work is removed normally with a note. A symlink is unlinked, never followed. A repo that cannot be removed is reported and exits 1. `--dry-run` runs the same read-only checks (git runs with `--no-optional-locks`, so the index is not rewritten) and deletes nothing. Known limit: a remote that is just another directory on this machine counts as a remote, so commits pushed only there are treated as saved.
- `init-config [--output PATH] [--force]`: Write `assets/workspace.example.json` into the workspace as a starting point. Defaults to `<root>/.go-workspace.json`; `--output` writes elsewhere; `--force` overwrites an existing file (the command fails otherwise).

## Tests

`cd scripts && python3 -I -m unittest` runs `test_workspace.py`: stdlib only, local bare repos over `file://`, no network; the Go tests need `go` on PATH.
