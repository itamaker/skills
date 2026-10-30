---
name: runlens
description: Summarize and diagnose JSONL agent/tool execution traces with the runlens CLI (success rate, p95 latency, tokens, flaky tools, error clusters). Use when a trace needs a health report, or when finding why a run failed, which tool is flaky or slow.
---

# runlens

Deterministic stats over a JSONL trace (one event per line: `tool`, `latency_ms`, `tokens_in`, `tokens_out`, `success`, optional `agent`, `error`). Run it instead of hand-aggregating.

## Get the binary

`brew install itamaker/tap/runlens`, a release binary from github.com/itamaker/runlens-skill, or `go build -o runlens .` in a clone of that repo.

Bare `runlens` opens an interactive TUI that hangs an agent shell; always pass a subcommand. There is no `-h` or `--version`: run `runlens x` (invalid subcommand) for usage, `runlens summary -h` for flags.

## Run

```bash
runlens summary  -input trace.jsonl [-json]   # totals and per-tool breakdown
runlens diagnose -input trace.jsonl [-json]   # summary + flaky tools, error clusters, transitions, outliers
```

Start with `diagnose`. `examples/run.jsonl` shows the event shape.

## Reading the result

- `Success rate` below 100%: read `Error clusters` first. Each line is `signature: count (tools)`; fix the biggest cluster first.
- `Flaky tools` lists a tool with failure rate >= 20% or tool p95 above 1.25x the global p95. Inspect that tool's calls and error text before changing the agent.
- `Outliers` shows `#N`, the Nth event (1-based, blank lines excluded). Reason `failed`, `tool-latency-outlier` (>= mean + 2 stddev for its tool) or `global-latency-outlier` (above global p95). Open those events in the trace.
- `Top transitions` is the 5 most common consecutive `tool -> tool` pairs; a repeated `x -> x` pair signals a retry loop.
- `Tokens in/out` are totals only; divide by `Runs` for a per-call figure.

## Limits

- Order is file order; `timestamp` and `agent` are ignored. Sort or split interleaved concurrent agents first, or transitions mix them.
- A missing `success` field counts as a failure.
- Small samples mislead: one failed call makes a tool 100% flaky. Latency outliers need at least 12 events (below that p95 is the max, so nothing exceeds it).
- Outliers list only the 5 slowest, so fast failures drop out; use `Error clusters` for the failure inventory.
- Clusters group by exact lowercased text; IDs or timestamps inside messages split one cause into many.
- Cost, retries, and tool arguments are outside the schema; wrong-but-successful calls are invisible.

Exit 0 ok, 1 unreadable file or bad line (message names the line), 2 usage error. Fields, schema and thresholds: `references/REFERENCE.md`.
