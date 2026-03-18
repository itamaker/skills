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
- `clean --force`: Delete every configured repository directory from the workspace. Treat this as destructive.
- `init-config`: Write `assets/workspace.example.json` into the workspace as a starting point.

## Current Repository

This repository uses its own workspace config at `/Users/jonny/Documents/code/github/.go-workspace.json`.
