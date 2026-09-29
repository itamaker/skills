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

- `name`: local directory name and selection key for `sync <repo...>`
- `url`: clone URL for `git clone`
- `go_project`: whether `build` and `test` should run in this repo

## Command Semantics

- `sync [repo...]`: If no repo names are provided, sync every configured repository. If repo names are provided, each name must be present in the config.
- `build`: Run `go build ./...` in every Go project directory.
- `test`: Run `go test ./...` in every Go project directory.
- `list-repos [--format lines|shell|json]`: Print every configured repo's `name`. `lines` (default) is newline-separated, `shell` is space-separated, `json` is a JSON array.
- `list-projects [--format lines|shell|json]`: Same as `list-repos`, but filtered to repos where `go_project` is true.
- `clean --force`: Delete every configured repository directory from the workspace. Treat this as destructive.
- `init-config [--output PATH] [--force]`: Write `assets/workspace.example.json` into the workspace as a starting point. Defaults to `<root>/.go-workspace.json`; `--output` writes elsewhere; `--force` overwrites an existing file (the command fails otherwise).
