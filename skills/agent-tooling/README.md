# Agent Tooling

Command-line tools and skills for building and evaluating LLM agents: authoring skills, reading traces, scoring retrieval, testing prompts and auditing datasets.

Most of these wrap a command-line tool that lives in its own repository. Install the tool first (`brew install itamaker/tap/<name>`, or a release binary); each skill says how.

- **[skillforge](./skillforge/SKILL.md)**: Draft and scaffold OpenClaw-ready skills from briefs, tool catalogs and JSON specs.
- **[runlens](./runlens/SKILL.md)**: Analyze agent and tool JSONL traces for failures, flaky tools, latency outliers and token usage.
- **[ragcheck](./ragcheck/SKILL.md)**: Evaluate retrieval and RAG runs offline with Precision@k, Recall@k, MAP, nDCG and an answer judge.
- **[promptdeck](./promptdeck/SKILL.md)**: Render, batch and rank prompt variants from templates, JSON variables and experiment matrices.
- **[datasetlint](./datasetlint/SKILL.md)**: Audit JSONL datasets for duplicates, train/eval leakage and label conflicts.
