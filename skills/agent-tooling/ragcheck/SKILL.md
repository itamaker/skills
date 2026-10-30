---
name: ragcheck
description: Score retrieval runs against qrels (P/R/HitRate/MRR/MAP/nDCG@k) and check RAG answers by lexical token overlap with the ragcheck CLI. Use when comparing retriever configs on one qrels set, or flagging answer words absent from contexts.
---

# ragcheck

Offline and deterministic: no network, no model calls. Inputs are JSON arrays (not JSONL); schemas in `references/REFERENCE.md`, samples in `examples/`.

## Get the binary

`brew install itamaker/tap/ragcheck`, a release binary from github.com/itamaker/ragcheck-skill, or `go build -o ragcheck .` in a clone of that repo.

Bare `ragcheck` opens an interactive TUI that hangs an agent shell; always pass a subcommand. There is no `-h` or `--version`: run `ragcheck x` (invalid subcommand) for usage, `ragcheck score -h` for flags.

## Run

```bash
ragcheck score -qrels qrels.json -run run.json -k 5 [-json]   # retrieval metrics
ragcheck judge -input judge.json [-json]                      # lexical answer check; per-query hints need -json
```

Compare retriever configs by running `score` once per `-run` file with the same `-qrels` and `-k`, then diffing the numbers.

## Reading `score`

- All metrics are means over every query in qrels, so a query with no run entry (`Missing runs`) or no relevant docs counts as 0. Fix `Missing runs` > 0 before comparing.
- `HitRate@k` low: relevant docs never reach the top k; look at retrieval itself (index, chunking, query).
- `HitRate@k` high but `MRR@k` or `nDCG@k` low: relevant docs appear but ranked low; try a reranker or scoring changes.
- `Recall@k` well below `HitRate@k`: only some relevant docs are found; raise `-k` or improve coverage. `Precision@k` is capped at relevant/k, so judge it relative to another run.
- The tool defines no pass/fail thresholds; compare run against run.

## Reading `judge`

`judge` is a lexical heuristic (lowercased word overlap, no stemming, no embeddings, no LLM). Every score is the share of unique answer/context words found in another text, so each number moves with wording, not with correctness.

- `groundedness` (answer words found in contexts): the useful signal. Read `unsupported_tokens` (first 5 alphabetically, not the most important) for answer words to verify by hand.
- `reference_coverage` is answer words found in the reference, so an answer that omits reference content can still score 1.0.
- `answer_relevance` (answer words found in the question) and `context_relevance` (context words found in the question) drop as answers or contexts get longer, and an answer that repeats the question scores 1.0. The bundled example scores 0.225 and 0.113 on reasonable answers; use them only to compare runs on the same questions.
- `missing_context_hints` (reference words absent from contexts) point at facts retrieval failed to bring.

## Limits

- `score` treats unjudged docs as non-relevant, so a new retriever's valid hits missing from qrels lower its score.
- `score` counts a doc ID repeated in `results` as a repeated hit, which can push Recall above 1; dedupe `results` first.
- `-k` 0 or below prints all-zero metrics with `Queries: 0`; `grades` overrides `relevant` when both are set.
- `judge` misses paraphrase (`slower` vs `slow`), negation, and numbers under 3 characters (`42` vs `24` ground to 1.0). Text without spaces (CJK) becomes one word per run, so scores are all or nothing. Use human or LLM grading for correctness.

Exit 0 ok, 1 unreadable or invalid JSON, 2 usage error.
