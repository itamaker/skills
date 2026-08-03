# itamaker/skills

A Claude Code plugin marketplace that indexes the standalone `itamaker` skill repositories. The skill source lives in those repos; this one only ships `.claude-plugin/marketplace.json`.

## Install via Claude Code

Register the marketplace once, then install the skills you want:

```text
/plugin marketplace add itamaker/skills
/plugin install stitch-skills@itamaker-skills
/plugin install go-workspace-skills@itamaker-skills
/plugin install webpage-to-pdf-skill@itamaker-skills
```

## Install via the `skills` CLI

```bash
npx skills add itamaker/stitch-skills
npx skills add itamaker/go-workspace-skills
npx skills add itamaker/webpage-to-pdf-skill
```

## Skills in this marketplace

- [`itamaker/stitch-skills`](https://github.com/itamaker/stitch-skills) — Google Stitch workflows with an SDK-backed runner.
- [`itamaker/go-workspace-skills`](https://github.com/itamaker/go-workspace-skills) — configurable multi-repo Go workspace management.
- [`itamaker/webpage-to-pdf-skill`](https://github.com/itamaker/webpage-to-pdf-skill) — export live webpages to pixel-perfect paginated PDFs via headless Chrome screenshots.

## Contributing

New skill content goes into the standalone repositories above. This repo only changes when the marketplace metadata (`.claude-plugin/marketplace.json`) needs to add, remove, or repoint a skill.

## License

[MIT](./LICENSE)
