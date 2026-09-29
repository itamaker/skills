---
name: runlens
description: Analyze JSONL agent and tool execution traces with the runlens CLI. Use when summarizing success rate, latency, and token usage, diagnosing why a run failed, finding flaky tools or latency outliers, or clustering recurring errors.
---

# runlens

`runlens` is a Go CLI that reads a JSONL log of agent/tool execution events and reports success rate, latency (avg/p95), token usage, flaky tools, recurring error clusters, hot tool-to-tool transitions, and outlier events. Prefer invoking the `runlens` binary directly over re-implementing JSONL parsing or aggregation by hand — it already computes p95 latency, per-tool failure rates, and outlier classification consistently.

## Workflow

1. Make sure `runlens` is available.
   - Install with `brew install itamaker/tap/runlens`, download a release binary from the Releases page of github.com/itamaker/runlens-skill, or build from a source checkout with `go build -o runlens .`.
   - Do not invoke bare `runlens` with no arguments — that launches an interactive Bubble Tea TUI and will hang a non-interactive/agent shell. Always use an explicit subcommand.

2. Identify the input trace file.
   - It must be JSONL (one JSON object per line). Each event has: `timestamp`, `agent`, `tool`, `latency_ms`, `tokens_in`, `tokens_out`, `success` (bool), and an optional `error` string.
   - `examples/run.jsonl` in this skill's folder is a good shape reference if the user hasn't supplied their own trace file.

3. Choose the subcommand based on what the user wants to know.
   - `runlens summary -input <path>`: aggregate stats only — total runs, success rate, avg/p95 latency, total tokens in/out, and a per-tool run/failure/latency breakdown. Use this for a quick health check or token/latency report.
   - `runlens diagnose -input <path>`: everything `summary` produces, plus flaky-tool detection, error clustering, top tool-to-tool transitions, and outlier events. Use this whenever the user asks "why did this fail," "what's flaky," or "what's slow."

4. Add `-json` to either subcommand when the output needs to be parsed programmatically or fed into another step (e.g. summarizing across multiple trace files, or building a table). Omit it for a direct human-readable report.
   - Example: `runlens diagnose -input run.jsonl -json`

5. Read the report.
   - `summary` output: `Runs`, `Success rate`, `Latency avg/p95`, `Tokens in/out`, then a `Tool usage` line per tool.
   - `diagnose` output adds up to four extra sections, only printed when non-empty: `Flaky tools`, `Error clusters`, `Top transitions` (top 5), `Outliers` (top 5). See `references/REFERENCE.md` for the exact JSON schema and the thresholds used to classify flaky tools and outliers.

6. Handle errors.
   - Missing `-input`: exits 2 with `-input is required`.
   - Unreadable/missing file or malformed JSONL line: exits 1 with a `open log file: ...` or `decode JSONL line N: ...` message — report the line number back to the user so they can fix their trace.
   - Unknown subcommand: exits 2 and prints usage; there is no dedicated `--help`/`-h` flag on the top-level command.

## Prompt Patterns

- "Summarize this agent run log."
- "Why is my agent trace failing so much?"
- "Which tools are flaky in this run.jsonl?"
- "Find the latency outliers in this trace."
- "Cluster the errors in this JSONL log."
- "How many tokens did this evaluation run use?"
- "Give me a JSON report of this trace for a dashboard."
- "What tool call sequences show up most before failures?"

## Resources

- `examples/run.jsonl` (in this skill's folder): example trace file matching the expected JSONL shape.
- `references/REFERENCE.md`: full JSON output schema for `summary`/`diagnose`, and the exact thresholds used to flag flaky tools and outliers.
