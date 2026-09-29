# datasetlint reference

## Subcommands

- `datasetlint` (no args): launches the interactive Bubble Tea TUI. Not suitable for scripted/agent use.
- `datasetlint tui` / `datasetlint interactive`: same TUI, explicit alias.
- `datasetlint scan <flags>`: non-interactive scan. Use this one.

## `scan` flags

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `-train` | string | (required) | Path to the train-split JSONL file. |
| `-eval` | string | (required) | Path to the eval-split JSONL file. |
| `-semantic-threshold` | float | `0.6` | Jaccard token-set similarity cutoff (0-1) for near-duplicate / semantic-overlap detection. Tokens shorter than 3 characters are ignored when building the comparison set. |
| `-max-samples` | int | `5` | Max number of example strings/pairs printed per issue category. Does not change the reported counts. |
| `-strict` | bool | `false` | Exit `1` if any issue was found; exit `0` otherwise. |
| `-json` | bool | `false` | Emit the full report as JSON instead of the human-readable summary. |

Both `-train` and `-eval` are always required; omitting either exits `2` with a usage error before any file is read.

## Input record shape (one JSON object per line)

```json
{"id": "train-1", "input": "Summarize the retrieval benchmark setup.", "output": "A summary of the benchmark setup.", "label": "summary"}
```

- `id` (string, optional): row identifier. Blank/missing increments `missing_id`. Rows without an ID fall back to `row-<n>` (1-indexed) when referenced in near-duplicate sample output.
- `input` (string): the prompt/query text. Blank (after trimming) increments `empty_input` and is excluded from duplicate/near-duplicate comparisons.
- `output` (string): the target/response text. Blank (after trimming) increments `empty_output`.
- `label` (string, optional): classification label, used only for label-conflict detection (exact duplicate inputs with differing labels, and near-duplicate inputs above `-semantic-threshold` with differing labels).

Blank lines in the file are skipped. A line that fails to JSON-decode aborts the whole scan with a decode error (exit `1`).

## JSON report schema (`-json`)

Top level `Report`:

| Field | Type | Meaning |
| --- | --- | --- |
| `train` | `SplitReport` | Per-row stats for the train split. |
| `eval` | `SplitReport` | Per-row stats for the eval split. |
| `overlap_count` | int | Number of distinct normalized input strings present in both splits (literal train/eval leakage). |
| `overlap_examples` | []string | Up to `-max-samples` of the overlapping normalized strings. |
| `semantic_overlap_count` | int | Number of cross-split pairs at/above `-semantic-threshold` similarity that are not literal duplicates. |
| `semantic_overlap_samples` | []SimilarPair | Up to `-max-samples` of the highest-similarity cross-split pairs. |

`SplitReport` (one per split, `name` is `"train"` or `"eval"`):

| Field | Type | Meaning |
| --- | --- | --- |
| `rows` | int | Total rows parsed. |
| `missing_id` | int | Rows with blank/missing `id`. |
| `empty_input` | int | Rows with blank `input`. |
| `empty_output` | int | Rows with blank `output`. |
| `duplicate_inputs` | int | Count of normalized input strings that appear more than once in this split. |
| `duplicate_samples` | []string | Up to `-max-samples` of the duplicated normalized strings. |
| `near_duplicate_pairs` | int | Count of within-split row pairs at/above `-semantic-threshold` similarity (excluding exact duplicates). |
| `near_duplicate_samples` | []SimilarPair | Up to `-max-samples` of the highest-similarity within-split pairs. |
| `label_conflicts` | int | Count of same/near-duplicate inputs that carry different, non-blank labels. |
| `conflict_samples` | []string | Up to `-max-samples` of the conflicting normalized strings/pairs. |
| `label_counts` | map[string]int | Count of rows per non-blank label. |
| `length_stats` | LengthStats | Average and p95 input/output token counts (see below). |

`SimilarPair`:

| Field | Type | Meaning |
| --- | --- | --- |
| `left_id` / `right_id` | string | Row IDs (or `row-<n>` fallback) of the compared pair. |
| `similarity` | float | Jaccard token-set similarity, 0-1. |
| `left_input` / `right_input` | string | Original (non-normalized) input text of each row. |

`LengthStats`:

| Field | Type | Meaning |
| --- | --- | --- |
| `avg_input_tokens` / `avg_output_tokens` | float | Mean token count across the split. |
| `p95_input_tokens` / `p95_output_tokens` | int | 95th-percentile token count across the split. |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Scan completed. With `-strict`, this also means no issues were found. |
| `1` | File read/JSON-decode error, JSON-marshal error, or (`-strict` only) issues were found. |
| `2` | Usage error: unknown subcommand, missing `-train`/`-eval`, or bad flag. |
