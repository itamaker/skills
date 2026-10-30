---
name: datasetlint
description: Audit train/eval JSONL datasets with the datasetlint CLI: duplicates, word-overlap near-duplicates, train/eval leakage, label conflicts, missing IDs, empty fields. Use when checking an eval set for leakage or gating CI on dataset issues.
---

# datasetlint

Rows are JSON objects with string fields `id`, `input`, `output`, `label` (all optional; a non-string value is a decode error). Only `input` drives duplicate, overlap and conflict checks. Samples in `examples/`, flags and report schema in `references/REFERENCE.md`.

## Get the binary

`brew install itamaker/tap/datasetlint`, a release binary from github.com/itamaker/datasetlint-skill, or `go build -o datasetlint .` in a clone of that repo.

Bare `datasetlint` opens an interactive TUI that hangs an agent shell; always pass a subcommand. There is no `-h` or `--version`: run `datasetlint x` (invalid subcommand) for usage, `datasetlint scan -h` for flags.

## Run

```bash
datasetlint scan -train train.jsonl -eval eval.jsonl [-json] [-strict] [-semantic-threshold 0.6] [-max-samples 5]
```

Both files are required. Use `-json` to see duplicate, near-duplicate and conflict samples; text output lists only literal-overlap examples and the first semantic one.

## Reading the result

- `overlap_count` > 0: identical inputs (case and whitespace folded) sit in train and eval, so eval scores are inflated. Remove them from train, or from eval when the repeat is unintended, and rescan.
- `semantic_overlap_count` > 0: cross-split pairs with Jaccard word-set similarity >= threshold (counted per pair). Read `semantic_overlap_samples` before deleting anything. Templated prompts that share boilerplate flood this count: raise `-semantic-threshold` toward 0.8. Lower it to 0.4-0.5 to catch looser paraphrase.
- `duplicate_inputs` counts distinct repeated inputs within a split (not extra rows); `near_duplicate_pairs` counts similar non-identical pairs. Dedupe, or keep repeats that carry different outputs on purpose.
- `label_conflicts` counts same or near-identical inputs whose labels differ within one split. Adjudicate each conflict sample and fix the label.
- `missing_id`, `empty_input`, `empty_output`: fix at the source.
- `length_stats` counts words, not model tokens. Compare train against eval for distribution shift.

## Limits

- Similarity is Jaccard over lowercase word sets (words of 3+ characters): no embeddings, so order, negation and synonyms are invisible. "The model is not safe to deploy" matches "The model is safe to deploy" at 0.8, a shuffled sentence scores 1.0, and a translation scores 0.
- Only `input` is compared. Same output with different inputs, and label disagreement across train and eval, go unreported.
- Samples are the first pairs found in row order, so they can omit the strongest pair; the counts are exact.
- Pair search grows roughly with the square of row count when rows share common words (5,000 train + 500 eval rows took about 11 s).

## Gating

`-strict` exits 1 if any count above is nonzero (a missing `id` included) and cannot be narrowed; for a specific gate, read the field from `-json`. Without `-strict` a parsed scan exits 0. Exit 1 also means an unreadable file or bad line (names the line); exit 2 is a usage error.

To audit one file, pass it as both `-train` and `-eval`, ignore the two overlap counts, and read the split fields; `-strict` then always fails.
