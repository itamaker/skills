# itamaker/skills

[![skills.sh](https://skills.sh/b/itamaker/skills)](https://skills.sh/itamaker/skills)

Agent skills by [Zhaoyang Jia](https://github.com/itamaker): tooling for building and evaluating LLM agents, web page export, and Go workspace management. Each skill is a small folder with a `SKILL.md`. They work with Claude Code, Codex and other agents that read skills.

> These skills used to live in separate repositories (`stitch-skill`, `forge-skill`, `runlens-skill` and so on). They now live here; the old repositories point back to this one.

## Installation

Pick one route. Installing both leaves you with every skill twice.

<details>
<summary><strong>Claude Code</strong></summary>

Register the marketplace once, then install the plugin:

```text
/plugin marketplace add itamaker/skills
/plugin install itamaker-skills@itamaker
```

The plugin is a managed bundle that updates when this repository does.

</details>

<details>
<summary><strong>Codex, and other agents</strong></summary>

```bash
npx skills@latest add itamaker/skills
```

Choose the skills you want and the agents to install them on. To install one skill:

```bash
npx skills@latest add itamaker/skills --skill=<name>
```

</details>

<details>
<summary><strong>For tinkerers</strong></summary>

The same `npx skills` installer writes the skills into your repo as ordinary files you own and can edit. Nothing updates behind your back; pull changes when you want them with `npx skills@latest update`.

</details>

## Requirements

| Skill | Needs |
|---|---|
| skillforge, runlens, ragcheck, promptdeck, datasetlint | Their CLI: `brew install itamaker/tap/<name>`, or a release binary from the tool's own repository |
| webpage-to-pdf | Google Chrome and Python 3 (the converter ships inside the skill) |
| remote-browser | Node.js 22.18+ with TypeScript support (the skill installs one if yours lacks it), npm, curl and a Cloudflare account; the skill deploys its own Worker for you |
| stitch | Node.js (or Bun) and Stitch credentials: `STITCH_API_KEY`, or OAuth via `STITCH_ACCESS_TOKEN` plus `GOOGLE_CLOUD_PROJECT`. The SDK runner installs itself on first use |
| go-workspace-skill | Python 3, Git and Go, plus a workspace config file (the skill can create one) |

## Reference

Every skill here is **model-invoked**: the agent reaches for it when the task matches, or you can call it by name.

### Agent Tooling

Command-line tools and skills for building and evaluating LLM agents: authoring skills, reading traces, scoring retrieval, testing prompts and auditing datasets.

- **[skillforge](./skills/agent-tooling/skillforge/SKILL.md)**: Draft and scaffold OpenClaw-ready skills from briefs, tool catalogs and JSON specs.
- **[runlens](./skills/agent-tooling/runlens/SKILL.md)**: Analyze agent and tool JSONL traces for failures, flaky tools, latency outliers and token usage.
- **[ragcheck](./skills/agent-tooling/ragcheck/SKILL.md)**: Evaluate retrieval and RAG runs offline with Precision@k, Recall@k, MAP, nDCG and an answer judge.
- **[promptdeck](./skills/agent-tooling/promptdeck/SKILL.md)**: Render, batch and rank prompt variants from templates, JSON variables and experiment matrices.
- **[datasetlint](./skills/agent-tooling/datasetlint/SKILL.md)**: Audit JSONL datasets for duplicates, train/eval leakage and label conflicts.

### Web

Work with web pages and web-based design tools.

- **[webpage-to-pdf](./skills/web/webpage-to-pdf/SKILL.md)**: Export a live webpage as a pixel-perfect, paginated PDF via headless Chrome screenshots.
- **[stitch](./skills/web/stitch/SKILL.md)**: Generate and edit designs with Google Stitch through a bundled SDK runner, and turn the output into app code.
- **[remote-browser](./skills/web/remote-browser/SKILL.md)**: Give Claude a cloud browser on your own Cloudflare account: read JavaScript-heavy pages and hand you a live session for manual logins.

### Dev

Everyday development workflow.

- **[go-workspace-skill](./skills/dev/go-workspace-skill/SKILL.md)**: Sync, build and test a configurable multi-repo Go workspace from a single config file.

## In progress

Skills still being tried out live in [`skills/in-progress`](./skills/in-progress/README.md). They are not part of the plugin.

## License

[MIT](./LICENSE)
