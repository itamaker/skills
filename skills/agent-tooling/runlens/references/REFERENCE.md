# runlens Reference

Detail beyond what's needed for a routine invocation: full flag list, JSON output schema, and the exact rules `runlens diagnose` uses to flag flaky tools and outliers. Source of truth is `internal/app/` in the tool's repository (github.com/itamaker/runlens-skill) (`commands.go`, `summary.go`, `diagnose.go`, `types.go`).

## Subcommands and flags

```text
runlens                          # launch interactive Bubble Tea TUI (avoid in agent contexts)
runlens summary  -input <path> [-json]
runlens diagnose -input <path> [-json]
runlens tui                      # alias for the bare TUI form
runlens interactive              # alias for the bare TUI form
```

Both `summary` and `diagnose` use Go's `flag` package:

- `-input string` (required): path to a JSONL log file.
- `-json` (optional, default false): emit machine-readable JSON instead of the human-readable report.

In v0.3.0 there is no top-level `--help`/`-h`/`--version`: any unrecognized first argument prints `unknown subcommand "x"` to stderr, a short usage block to stdout, and exits with status 2, and `runlens summary -h` (and `diagnose -h`) prints the flag list and exits 2. Builds after v0.3.0 (itamaker/runlens-skill#3) accept `-h`, `-help`, `--help`, `help` and `--version`/`version` (stdout, exit 0), send an unknown subcommand's usage to stderr (exit 2), and make `runlens summary -h` exit 0 with the flags on stdout.

## Input event shape (JSONL, one object per line)

```json
{
  "timestamp": "2026-03-11T08:00:03Z",
  "agent": "writer",
  "tool": "code-exec",
  "latency_ms": 310,
  "tokens_in": 320,
  "tokens_out": 80,
  "success": false,
  "error": "timeout"
}
```

`error` and `agent` are optional strings; everything else is required for meaningful stats. `timestamp` is not used: events are processed in file order. A missing `success` field decodes as `false` (counts as a failure). Only truly empty lines are skipped; a whitespace-only line fails with `decode JSONL line N`, and a line longer than 64 KB fails with `scan log file: bufio.Scanner: token too long` (exit 1). An empty file reports `Runs: 0` and exits 0.

## `summary -json` output schema

```json
{
  "total_runs": 5,
  "success_rate": 0.8,
  "avg_latency_ms": 158,
  "p95_latency_ms": 310,
  "total_tokens_in": 1180,
  "total_tokens_out": 280,
  "tools": [
    { "name": "retriever", "runs": 2, "failures": 0, "avg_latency_ms": 140 }
  ]
}
```

`tools` is sorted by run count descending, then name ascending.

## `diagnose -json` output schema

Adds four sections on top of the `summary` object (each field is omitted from JSON entirely when empty):

```json
{
  "summary": { "...": "same shape as summary -json" },
  "error_clusters": [
    { "signature": "timeout", "count": 1, "tools": ["code-exec"] }
  ],
  "flaky_tools": [
    {
      "name": "code-exec",
      "runs": 1,
      "failures": 1,
      "failure_rate": 1,
      "avg_latency_ms": 310,
      "p95_latency_ms": 310,
      "avg_tokens": 400
    }
  ],
  "transitions": [
    { "from": "retriever", "to": "code-exec", "count": 1 }
  ],
  "outliers": [
    {
      "index": 4,
      "tool": "code-exec",
      "agent": "writer",
      "latency_ms": 310,
      "error": "timeout",
      "reason": "failed"
    }
  ]
}
```

### Flaky tool classification

A tool is reported in `flaky_tools` when either is true:

- `failure_rate >= 0.2` (at least 20% of its runs failed), OR
- its per-tool p95 latency is strictly greater than `int(1.25 * global_p95_latency_ms)`.

The global p95 covers all tools together, so a high-volume fast tool lowers the bar for slower ones. A tool with a single failed run is reported at 100%.

Sorted by failure rate descending, then p95 latency descending.

### Error clustering

Errors are grouped by a normalized signature: the `error` string is lowercased, trimmed, and internal whitespace collapsed. Every event with `success: false` or a non-empty `error` is clustered (so a successful event that carries an `error` string counts too); a failure with an empty `error` goes under `"unspecified failure"`. Sorted by count descending, then signature ascending.

### Transitions

Counts consecutive `tool -> tool` pairs across the event sequence (only when both events have a non-empty `tool`). Sorted by count descending, then `from`/`to` ascending, and **truncated to the top 5**.

### Outliers

An event is an outlier if any of these hold, and `reason` lists all that apply (comma-joined):

- `failed`: `success` is `false`.
- `tool-latency-outlier`: the event's latency is at or above that tool's `mean + 2*stddev` latency (population stddev), AND also exceeds the global p95.
- `global-latency-outlier`: only assigned when no other reason applied (not `failed`, not `tool-latency-outlier`), and the event's latency exceeds the global p95 (and global p95 > 0).

The global p95 is `sorted[round(0.95*(n-1))]`, so with fewer than 12 events it equals the maximum and no event can exceed it (verified: 11 events with a 10x spike report no outlier, 12 do). `index` is the 1-based event number (blank lines excluded), not the file line number.

Sorted by latency descending, then original index ascending, and **truncated to the top 5**.

## Exit codes

- `0`: success.
- `1`: runtime error (e.g. file not found, malformed JSONL line) — message goes to stderr.
- `2`: usage error (missing `-input`, bad flag, unknown subcommand).
