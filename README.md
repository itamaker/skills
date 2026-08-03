# itamaker/skills

A Claude Code plugin marketplace that indexes the standalone `itamaker` skill repositories. The skill source lives in those repos; this one only ships `.claude-plugin/marketplace.json`.

## Install via Claude Code

Register the marketplace once, then install the skills you want:

```text
/plugin marketplace add itamaker/skills
/plugin install stitch-skill@itamaker-skills
/plugin install go-workspace-skill@itamaker-skills
/plugin install webpage-to-pdf-skill@itamaker-skills
/plugin install forge-skill@itamaker-skills
/plugin install runlens-skill@itamaker-skills
/plugin install ragcheck-skill@itamaker-skills
/plugin install promptdeck-skill@itamaker-skills
/plugin install datasetlint-skill@itamaker-skills
```

## Install via the `skills` CLI

```bash
npx skills add itamaker/stitch-skill
npx skills add itamaker/go-workspace-skill
npx skills add itamaker/webpage-to-pdf-skill
npx skills add itamaker/forge-skill
npx skills add itamaker/runlens-skill
npx skills add itamaker/ragcheck-skill
npx skills add itamaker/promptdeck-skill
npx skills add itamaker/datasetlint-skill
```

## Skills in this marketplace

- [`itamaker/stitch-skill`](https://github.com/itamaker/stitch-skill) — Google Stitch workflows with an SDK-backed runner.
- [`itamaker/go-workspace-skill`](https://github.com/itamaker/go-workspace-skill) — configurable multi-repo Go workspace management.
- [`itamaker/webpage-to-pdf-skill`](https://github.com/itamaker/webpage-to-pdf-skill) — export live webpages to pixel-perfect paginated PDFs via headless Chrome screenshots.
- [`itamaker/forge-skill`](https://github.com/itamaker/forge-skill) — draft and scaffold OpenClaw-ready agent skills with skillforge.
- [`itamaker/runlens-skill`](https://github.com/itamaker/runlens-skill) — analyze agent and tool JSONL traces for failures, flaky paths, latency outliers, and token usage.
- [`itamaker/ragcheck-skill`](https://github.com/itamaker/ragcheck-skill) — evaluate retrieval and RAG runs offline with Precision@k, Recall@k, MAP, nDCG, and an answer judge.
- [`itamaker/promptdeck-skill`](https://github.com/itamaker/promptdeck-skill) — render, batch, and optimize prompt templates from JSON variables and experiment matrices.
- [`itamaker/datasetlint-skill`](https://github.com/itamaker/datasetlint-skill) — audit JSONL datasets for duplicates, semantic leakage, and label conflicts.

## Contributing

New skill content goes into the standalone repositories above. This repo only changes when the marketplace metadata (`.claude-plugin/marketplace.json`) needs to add, remove, or repoint a skill.

## License

[MIT](./LICENSE)
