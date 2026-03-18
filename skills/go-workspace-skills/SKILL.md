---
name: go-workspace-skills
description: Manage configurable multi-repo Go workspaces using a user-provided workspace config file. Use when you need to sync managed repositories, update only a subset of repositories, build all configured Go projects, run workspace-wide Go tests, initialize a workspace config for a new user, or clean cloned repo directories. Trigger for requests like "sync the repos", "pull skillforge and runlens", "build the workspace", "run all tests", "set up the workspace config", or "remove the checked out repos".
---

# Go Workspace Skills

Use a workspace config file as the source of truth for repository membership, clone URLs, and which repositories are Go projects. Prefer `scripts/run.sh` over assembling Git and Go commands by hand; it delegates to the skill's own Python executor and does not require the target workspace to contain a `Makefile`.

## Workflow

1. Resolve the workspace root.
   - If already in the workspace root, run `scripts/run.sh` directly.
   - If invoking the skill from a global skill install, pass `--root /abs/path/to/workspace`.

2. Resolve the workspace config.
   - By default, the script looks for `.go-workspace.json` and then `go-workspace.json` in the workspace root.
   - Override that path with `--config /abs/path/to/config.json` or the `GO_WORKSPACE_SKILLS_CONFIG` environment variable.
   - If no config exists yet, create one with `scripts/run.sh --root /path/to/workspace init-config`.

3. Choose the action.
   - `sync [repo...]`: clone or fast-forward pull all managed repos, or only the named subset.
   - `build`: run `go build ./...` in each Go project.
   - `test`: run `go test ./...` in each Go project.
   - `clean --force`: delete managed repo directories from the workspace.
   - `init-config`: write an example config file for a new workspace.

4. Validate the request before running it.
   - For `sync`, only use repo names declared in the loaded config file.
   - For `build` and `test`, do not accept repo filters; the skill runs them across every configured Go project.
   - For `clean`, require explicit user confirmation and pass `--force`.

5. Execute through the wrapper.
   - `scripts/run.sh --root /path/to/workspace sync`
   - `scripts/run.sh --root /path/to/workspace sync skillforge runlens`
   - `scripts/run.sh --root /path/to/workspace build`
   - `scripts/run.sh --root /path/to/workspace test`
   - `scripts/run.sh --root /path/to/workspace clean --force`
   - `scripts/run.sh --root /path/to/workspace init-config`
   - Add `--dry-run` before the action when you need to preview commands.

## Safety Rules

- Treat `clean` as destructive. Do not run it unless the user clearly asks to delete the managed checkouts.
- Expect `sync` to require network access and Git credentials. If the environment blocks network access, request approval or surface the blocker.
- If a target path exists but is not a Git repository, expect `sync` to skip it rather than force-replacing it.
- When changing repo membership, clone URLs, or Go-project status for a workspace, update that workspace's config file.
- In this repository, the root `Makefile` is only a compatibility layer that delegates to the skill. Do not treat it as the source of truth.

## Prompt Patterns

- "Sync all repos in this workspace."
- "Pull only `skillforge` and `go-chrome-ai`."
- "Build the Go projects in this workspace."
- "Run the workspace tests."
- "Create a workspace config for this repo set."
- "Clean the local repo directories."

## Resources

- `assets/workspace.example.json`: example config that users can copy or write with `init-config`.
- `scripts/workspace.py`: execute `sync`, `build`, `test`, `clean`, and list operations from the workspace config.
- `scripts/run.sh`: shell wrapper around `scripts/workspace.py`.
- `references/config.md`: config format, lookup order, and bootstrap guidance.
