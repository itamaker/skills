# My day-to-day development skills

Reusable agent skills published by Zhaoyang Jia.

This repository is structured to work with the open `skills` installer ecosystem, so you can install skills directly from GitHub with `npx skills add`.

## Available Skills

- `go-workspace-skills`: Manage configurable multi-repo Go workspaces from a workspace config file.
- `stitch`: Request Google Stitch through a bundled SDK runner, with configurable auth and generation parameters.

## Install

```bash
# List skills in this repository
npx skills add itamaker/skills --list

# Install go-workspace-skills
npx skills add itamaker/skills --skill go-workspace-skills

# Install stitch
npx skills add itamaker/skills --skill stitch
```

### Install to specific agents

```bash
# Install only to Codex and Claude Code
npx skills add itamaker/skills --skill go-workspace-skills -a codex -a claude-code
```

### Global install

```bash
# Install globally without prompts
npx skills add itamaker/skills --skill go-workspace-skills -g -y
```

## Repository Layout

The `skills` CLI automatically discovers skills from the `skills/` directory in this repository:

```text
skills/
  go-workspace-skills/
    SKILL.md
    agents/
    assets/
    references/
    scripts/
  stitch/
    SKILL.md
    agents/
    assets/
    references/
    scripts/
```

The repository also includes `.claude-plugin/marketplace.json` so the same skill layout is compatible with Claude Code plugin-manifest discovery.

## Configuring `go-workspace-skills`

`go-workspace-skills` is intentionally generic. Repository lists are not hardcoded into the skill. Each workspace provides its own config file.

Lookup order:

1. `--config /path/to/file.json`
2. `GO_WORKSPACE_SKILLS_CONFIG=/path/to/file.json`
3. `<workspace-root>/.go-workspace.json`
4. `<workspace-root>/go-workspace.json`

### Bootstrap a workspace config

You can either:

1. Copy [`workspace.example.json`](./skills/go-workspace-skills/assets/workspace.example.json) into your workspace as `.go-workspace.json`
2. Or run the bundled script from a checkout of this repository:

```bash
python3 skills/go-workspace-skills/scripts/workspace.py --root /path/to/workspace init-config
```

Then edit the generated config to match your repositories:

```json
{
  "repos": [
    {
      "name": "example-cli",
      "url": "https://github.com/example/example-cli.git",
      "go_project": true
    },
    {
      "name": "docs-site",
      "url": "git@github.com:example/docs-site.git",
      "go_project": false
    }
  ]
}
```

### What the skill does

- `sync [repo...]`: clone or fast-forward pull all configured repositories, or a named subset
- `build`: run `go build ./...` across configured Go projects
- `test`: run `go test ./...` across configured Go projects
- `clean --force`: delete configured repository directories
- `init-config`: write a starter config file

## Usage Examples

After installation, ask your coding agent things like:

- `Use $go-workspace-skills to sync all repos in this workspace.`
- `Use $go-workspace-skills to pull only skillforge and runlens.`
- `Use $go-workspace-skills to build the workspace.`
- `Use $go-workspace-skills to run workspace tests.`
- `Use $go-workspace-skills to create a workspace config for this repo set.`
- `Use $stitch to list my Stitch projects.`
- `Use $stitch to create a Stitch project and generate a login screen.`
- `Use $stitch to download the HTML for a Stitch screen into ./tmp/screen.html.`
- `Use $stitch to save my Stitch auth and defaults into ./.stitch.json.`
- `Use $stitch to write committed @google/stitch-sdk code for this app.`

## Future Skills

This repository is meant to hold multiple skills over time. Add new skills under `skills/<skill-name>/`.

## License

[MIT](./LICENSE)
