---
name: datasetlint
description: Audit JSONL train/eval datasets with the datasetlint CLI. Use when checking for duplicates, train/eval leakage, label conflicts, missing IDs or empty fields, or producing a strict pass/fail report for CI.
---

# datasetlint

`datasetlint` is a Go CLI that scans a pair of JSONL dataset files (train + eval) for quality, overlap, and semantic duplication issues before they quietly corrupt training or benchmark results. Prefer the `scan` subcommand for scripted/agent use — it is non-interactive and scriptable, unlike the default Bubble Tea TUI.

## Workflow

1. Resolve the binary.
   - Check `command -v datasetlint`. If it's on PATH (e.g. via `brew install itamaker/tap/datasetlint`), use it directly.
   - Otherwise build from source in the tool's repository (github.com/itamaker/datasetlint-skill): `go build -o dist/datasetlint .` (or `make build`), then invoke `./dist/datasetlint`.

2. Confirm the input shape. Each JSONL line is one JSON object with string fields `id`, `input`, `output`, `label` (only `input` and `output` are meaningfully compared; `id` and `label` are optional but drive missing-ID and label-conflict checks). See `examples/train.jsonl` and `examples/eval.jsonl` for real, minimal samples.

3. Run the baseline scan. Both `-train` and `-eval` are required flags — there is no single-file mode:
   ```bash
   datasetlint scan -train path/to/train.jsonl -eval path/to/eval.jsonl
   ```
   This prints, per split: row count, missing-ID count, empty-input/empty-output counts, duplicate-input count, near-duplicate pair count, label-conflict count, label distribution, and input/output token-length avg + p95. It also prints cross-split literal overlap and cross-split semantic overlap counts (train/eval leakage signals).

4. For machine-readable output (CI gates, further parsing), add `-json`. This emits the full report as JSON (`train`, `eval`, `overlap_count`, `overlap_examples`, `semantic_overlap_count`, `semantic_overlap_samples` — see `references/REFERENCE.md` for the full field list).

5. Tune sensitivity if the defaults over- or under-flag:
   - `-semantic-threshold <0..1>` (default `0.6`): Jaccard token-set similarity cutoff used for near-duplicate and semantic-leakage detection. Lower it to catch more borderline paraphrases; raise it to reduce false positives.
   - `-max-samples <n>` (default `5`): caps how many example strings/pairs are printed per issue category (does not affect the *counts*, only how many samples are shown).

6. Gate CI or agent decisions on pass/fail with `-strict`: the process exits `1` if any issue was found (missing IDs, empty fields, duplicates, near-duplicates, or label conflicts in either split, or any train/eval overlap), and `0` if the dataset is clean. Without `-strict`, exit code is `0` for any successfully parsed scan; malformed JSONL (bad line, unreadable file) always exits `1` regardless of `-strict`.

7. Interpret results: nonzero `duplicate_inputs` / `near_duplicate_pairs` means redundant rows within one split; nonzero `overlap_count` / `semantic_overlap_count` means eval rows leak into train (or vice versa) — the most serious finding, since it inflates eval metrics; nonzero `label_conflicts` means near-identical inputs were given different labels, a likely annotation error.

8. Auditing a single file with no train/eval split: `-train` and `-eval` are both mandatory, so pass the same file to both flags. In that mode ignore `overlap_count`/`semantic_overlap_count` (a file trivially "overlaps" with itself) and focus only on that split's own `duplicate_inputs`, `near_duplicate_pairs`, `label_conflicts`, `missing_id`, and empty-field counts.

## Prompt Patterns

- "Audit my train and eval JSONL files for leakage."
- "Check these datasets for duplicate examples."
- "Does my eval set overlap with the training data?"
- "Find label conflicts in this dataset."
- "Run datasetlint on train.jsonl and eval.jsonl."
- "Give me a strict pass/fail check for CI on this dataset."
- "Are there near-duplicate prompts between train and eval?"
- "Summarize label counts and length stats for this dataset."

## Resources

- `examples/train.jsonl`, `examples/eval.jsonl`: minimal real sample pair (in this skill's `examples/` folder) showing the required JSONL shape and exercising duplicate-input, missing-ID, and empty-output cases.
- `references/REFERENCE.md`: full flag reference, JSON report schema, and exit-code semantics.
