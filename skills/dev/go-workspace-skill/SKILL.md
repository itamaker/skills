---
name: go-workspace-skill
description: Config-driven manager for a multi-repo Go workspace: sync, build, test, list and safely clean its repos. Use when syncing, building or testing several Go repos together, or when deleting their local checkouts.
---

# Go Workspace Skill

A workspace config file is the source of truth for repo names, clone URLs, and which repos are Go projects. Run everything through `scripts/run.sh`; it needs Python 3.8+, `git`, and `go`, and the workspace needs no `Makefile`. Command semantics and exit codes live in `references/config.md`.

## Workflow

1. Locate the workspace root and config.
   - Inside the root, run `scripts/run.sh` directly; from a global skill install, pass `--root /abs/path/to/workspace`.
   - The config is `.go-workspace.json`, then `go-workspace.json`, in the root; override with `--config /abs/path.json` or `GO_WORKSPACE_SKILLS_CONFIG`.
   - With no config, write one with `scripts/run.sh --root /path init-config` (`--output PATH` to place it elsewhere, `--force` to overwrite), then edit it.
   - After changing repo membership, clone URLs, or Go-project status, edit that config.

2. Run the action: `scripts/run.sh --root /path <action>`; put `--dry-run` before the action to preview commands.
   - `sync [repo...]`: clone or fast-forward each repo; names must exist in the config.
   - `build`, `test`: run across every Go project; they take no repo filter.
   - `list-repos`, `list-projects` (`--format lines|shell|json`): read-only.
   - `clean --force`: delete repos that hold no local work; skip the rest.

3. Read the result.
   - `sync`, `build` and `test` finish with a per-repo PASS/FAIL summary and exit non-zero if any failed. Report every FAIL to the user with its cause; a failure never stops the other repos.
   - `sync` needs network access and Git credentials; surface a blocked network instead of retrying.
   - A path that exists but is not a git repository is never replaced; `sync` reports it as FAIL.

## Cleaning safely

`clean` deletes directories, so treat each step as a checkpoint:

1. Confirm the user wants the managed checkouts deleted, then run `clean --force` (use `--dry-run` first if unsure).
2. It deletes only repos with a clean tree and every commit on a remote branch. Any other repo is listed as SKIPPED with its reason, and the command exits non-zero.
3. If anything was skipped, show the user the skipped list with reasons and ask whether to delete those too.
4. Only after a fresh yes to that list, run `clean --force --discard-changes`. Earlier consent to `clean` does not cover discarding local work.
