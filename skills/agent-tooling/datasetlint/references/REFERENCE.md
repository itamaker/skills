# datasetlint reference

## Subcommands

- `datasetlint` (no args): launches the interactive Bubble Tea TUI. Not suitable for scripted/agent use.
- `datasetlint tui` / `datasetlint interactive`: same TUI, explicit alias.
- `datasetlint scan <flags>`: non-interactive scan. Use this one. `datasetlint scan -h` prints the flag list (exit 2).
- v0.3.0: any other first argument prints `unknown subcommand "x"` to stderr, a usage block to stdout, and exits `2`; there is no `--help` or `--version`. Builds after v0.3.0 (itamaker/datasetlint-skill#3) accept `-h`, `-help`, `--help`, `help` and `--version`/`version` (stdout, exit 0), send an unknown subcommand's usage to stderr (exit 2), and make `datasetlint scan -h` exit 0 with the flags on stdout.

## `scan` flags

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `-train` | string | (required) | Path to the train-split JSONL file. |
| `-eval` | string | (required) | Path to the eval-split JSONL file. |
| `-semantic-threshold` | float | `0.6` | Jaccard similarity cutoff (0-1) over lowercase word sets, for near-duplicate / semantic-overlap / semantic label-conflict detection. A pair counts at similarity `>=` threshold. Words shorter than 3 bytes are ignored when building the set. Not embeddings: word order, negation and synonyms are invisible (verified: "The model is not safe to deploy" vs "The model is safe to deploy" = 0.8; a reordered sentence = 1.0). |
| `-max-samples` | int | `5` | Max number of example strings/pairs kept per issue category. Does not change the reported counts. Samples are the first pairs found scanning rows in order (sorted by similarity afterwards), so they can miss the highest-similarity pair. Text output shows only `overlap_examples` and the first semantic overlap sample; every other sample list needs `-json`. |
| `-strict` | bool | `false` | Exit `1` if any issue was found; exit `0` otherwise. "Issue" means any nonzero `missing_id`, `empty_input`, `empty_output`, `duplicate_inputs`, `near_duplicate_pairs` or `label_conflicts` in either split, or nonzero `overlap_count` or `semantic_overlap_count`. `length_stats` and labels never trigger it, and the set cannot be narrowed. |
| `-json` | bool | `false` | Emit the full report as JSON instead of the human-readable summary. |

Both `-train` and `-eval` are always required; omitting either exits `2` with a usage error before any file is read.

## Input record shape (one JSON object per line)

```json
{"id": "train-1", "input": "Summarize the retrieval benchmark setup.", "output": "A summary of the benchmark setup.", "label": "summary"}
```

- All four fields must be JSON strings when present; a number or other type is a decode error (`decode line N: json: cannot unmarshal number ...`, exit `1`). Unknown fields are ignored.
- `id` (string, optional): row identifier. Blank/missing increments `missing_id`. Rows without an ID fall back to `row-<n>` (1-indexed) when referenced in near-duplicate sample output.
- `input` (string): the prompt/query text. Blank (after trimming) increments `empty_input` and is excluded from duplicate/near-duplicate comparisons.
- `output` (string): the target/response text. Blank (after trimming) increments `empty_output`.
- `label` (string, optional): classification label, used only for label-conflict detection (exact duplicate inputs with differing labels, and near-duplicate inputs above `-semantic-threshold` with differing labels).

Only truly empty lines are skipped. A line that fails to JSON-decode aborts the whole scan with `decode line N: ...` (exit `1`); a line over 64 KB fails with `scan dataset: bufio.Scanner: token too long`.

## JSON report schema (`-json`)

Top level `Report`:

| Field | Type | Meaning |
| --- | --- | --- |
| `train` | `SplitReport` | Per-row stats for the train split. |
| `eval` | `SplitReport` | Per-row stats for the eval split. |
| `overlap_count` | int | Number of distinct normalized input strings present in both splits (literal train/eval leakage). |
| `overlap_examples` | []string | Up to `-max-samples` of the overlapping normalized strings. |
| `semantic_overlap_count` | int | Number of cross-split row pairs at/above `-semantic-threshold` similarity that are not literal duplicates (one eval row similar to three train rows counts 3). |
| `semantic_overlap_samples` | []SimilarPair | Up to `-max-samples` cross-split pairs, the first found in row order (not necessarily the highest similarity), sorted by similarity. |

`SplitReport` (one per split, `name` is `"train"` or `"eval"`):

| Field | Type | Meaning |
| --- | --- | --- |
| `rows` | int | Total rows parsed. |
| `missing_id` | int | Rows with blank/missing `id`. |
| `empty_input` | int | Rows with blank `input`. |
| `empty_output` | int | Rows with blank `output`. |
| `duplicate_inputs` | int | Count of distinct normalized input strings (lowercased, whitespace collapsed) that appear more than once in this split; a string repeated 5 times counts 1. |
| `duplicate_samples` | []string | Up to `-max-samples` of the duplicated normalized strings. |
| `near_duplicate_pairs` | int | Count of within-split row pairs at/above `-semantic-threshold` similarity (excluding exact duplicates). |
| `near_duplicate_samples` | []SimilarPair | Up to `-max-samples` within-split pairs, the first found in row order, sorted by similarity. |
| `label_conflicts` | int | Within-split count: rows whose exact normalized input already appeared with a different non-blank label (compared with the first label seen), plus near-duplicate pairs (similarity `>=` threshold) with different non-blank labels. Train-vs-eval label disagreement is not checked. |
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
| `avg_input_tokens` / `avg_output_tokens` | float | Mean word count across the split (split on non-letter/digit characters, including words under 3 bytes; not model tokens). |
| `p95_input_tokens` / `p95_output_tokens` | int | 95th-percentile token count across the split. |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Scan completed. With `-strict`, this also means no issues were found. |
| `1` | File read/JSON-decode error, JSON-marshal error, or (`-strict` only) issues were found. With `-json -strict` the report is still printed before exiting `1`. |
| `2` | Usage error: unknown subcommand, missing `-train`/`-eval`, or bad flag. |
