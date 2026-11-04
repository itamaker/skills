# Agent Tooling

Command-line tools and skills for building and evaluating LLM agents: reading traces, scoring retrieval, testing prompts and auditing datasets.

Most of these wrap a command-line tool that lives in its own repository. Install the tool first (`brew install itamaker/tap/<name>`, or a release binary); each skill says how.

- **[runlens](./runlens/SKILL.md)**: Find failures, flaky tools and latency outliers in agent JSONL traces.
- **[ragcheck](./ragcheck/SKILL.md)**: Score retrieval runs with P/R/MRR/MAP/nDCG@k and check answers by word overlap.
- **[promptdeck](./promptdeck/SKILL.md)**: Render prompt templates, expand variant matrices and rank scored variants.
- **[datasetlint](./datasetlint/SKILL.md)**: Audit JSONL datasets for duplicates, train/eval leakage and label conflicts.
