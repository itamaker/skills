# ragcheck reference

Full CLI, JSON schema, and metric reference for the `ragcheck` binary. Load this only when you need field-level or formula-level detail beyond what `SKILL.md` covers. In v0.3.0 `ragcheck score -h` and `ragcheck judge -h` print the flag list and exit 2, and there is no `--version`; builds after v0.3.0 (itamaker/ragcheck-skill#3) accept `-h`, `-help`, `--help`, `help` and `--version`/`version` (stdout, exit 0), send an unknown subcommand's usage to stderr (exit 2), and make `ragcheck score -h` exit 0 with the flags on stdout.

## CLI

### `ragcheck score`

```
ragcheck score -qrels <path> -run <path> [-k N] [-json]
```

| Flag | Required | Default | Meaning |
| --- | --- | --- | --- |
| `-qrels` | yes | — | Path to qrels JSON |
| `-run` | yes | — | Path to retrieval run JSON |
| `-k` | no | `5` | Top-k cutoff for all metrics |
| `-json` | no | `false` | Emit machine-readable JSON instead of text |

Text output prints, in order: `Queries`, `Missing runs`, `Precision@k`, `Recall@k`, `HitRate@k`, `MRR@k`, `MAP@k`, `nDCG@k`. `-json` emits the same fields as a `Metrics` object: `queries`, `k`, `missing_runs`, `precision_at_k`, `recall_at_k`, `hit_rate_at_k`, `mrr_at_k`, `map_at_k`, `ndcg_at_k`.

### `ragcheck judge`

```
ragcheck judge -input <path> [-json]
```

| Flag | Required | Default | Meaning |
| --- | --- | --- | --- |
| `-input` | yes | — | Path to a judge input JSON file |
| `-json` | no | `false` | Emit machine-readable JSON instead of text |

Text output prints averaged `Queries`, `Answer relevance`, `Context relevance`, `Groundedness`, `Reference coverage`, then one line per query with answer relevance, groundedness and any unsupported tokens. Per-query `context_relevance`, `reference_coverage` and `missing_context_hints` appear only with `-json`. `-json` emits a `JudgeReport`: `queries`, `answer_relevance`, `context_relevance`, `groundedness`, `reference_coverage`, and a `results[]` array of per-query `JudgeResult` objects (`query_id`, `answer_relevance`, `context_relevance`, `groundedness`, `reference_coverage`, `unsupported_tokens[]`, `missing_context_hints[]`).

### No-argument / TUI

`ragcheck` (no args), `ragcheck tui`, and `ragcheck interactive` all launch the same Bubble Tea interactive UI. Any other unrecognized first argument prints `unknown subcommand "x"` to stderr, a usage block to stdout, and exits `2`.

### Exit codes

- `0`: success.
- `1`: runtime error (e.g. file not found, invalid JSON) — message printed to stderr.
- `2`: usage error (missing required flag, unknown subcommand, flag parse failure, `-h`) — message printed to stderr.

## JSON schemas

### qrels file (`-qrels`)

Array of query relevance judgments. Each entry supports either binary relevance (`relevant`) or graded relevance (`grades`) — if both are omitted the query has no relevant documents.

```json
[
  { "query_id": "q1", "relevant": ["doc-1", "doc-3"] },
  { "query_id": "q2", "grades": { "doc-4": 2, "doc-9": 1 } }
]
```

- `query_id` (string, required): joins against the run file's `query_id`.
- `relevant` (string[], optional): document IDs treated as relevance grade `1`.
- `grades` (object, optional): document ID → numeric grade (used directly for graded nDCG; any grade `> 0` counts as relevant for Precision/Recall/HitRate/MRR/MAP). Takes precedence over `relevant` when both are present.

### run file (`-run`)

Array of retrieval results, one per query, ranked best-first.

```json
[
  { "query_id": "q1", "results": ["doc-1", "doc-2", "doc-9"] }
]
```

- `query_id` (string, required): should match a qrels entry; queries in `-run` with no corresponding qrels entry are ignored, and qrels entries with no matching run count toward `missing_runs`.
- `results` (string[], required): ranked document IDs, best match first. Only the first `k` are considered. Dedupe the list first: a repeated ID is counted as a repeated hit (`results: [d1,d1,d1]` for one relevant doc gives per-query Precision 1.0 and Recall 3.0; verified).

### judge input file (`-input`)

Array of RAG records to judge.

```json
[
  {
    "query_id": "q1",
    "question": "What caused the retrieval latency spike?",
    "answer": "The latency spike came from cache misses and slower vector search.",
    "reference": "Cache misses and slow vector search caused the retrieval latency spike.",
    "contexts": [
      "The incident review says cache misses increased tail latency during the rollout.",
      "A slower vector search path also contributed to the retrieval latency spike."
    ]
  }
]
```

- `query_id` (string, required)
- `question` (string, required)
- `answer` (string, required): the generated answer being judged.
- `reference` (string, optional): a gold/reference answer, used to compute `reference_coverage`. If omitted, `reference_coverage` is `0`.
- `contexts` (string[], required): retrieved passages the answer should be grounded in.

## Metric definitions

### Retrieval metrics (`score`), computed per query then averaged

All metrics only look at the top `k` entries of `results` and are means over every qrels entry (`queries`). Documents absent from qrels grade as 0 (non-relevant). `-k` of 0 or below returns an all-zero report with `queries: 0`.

- **Precision@k**: `hits / k`, where `hits` = count of top-k results with grade `> 0`.
- **Recall@k**: `hits / relevantCount`, where `relevantCount` = total documents with grade `> 0` in qrels. A query with `relevantCount` 0 adds 0 to the sum but still counts in the denominator (the mean is over all qrels queries).
- **HitRate@k**: `1` if `hits > 0` else `0`, averaged across queries.
- **MRR@k**: `1 / rank` of the first relevant hit within top-k (0 if no hit).
- **MAP@k**: average precision within top-k — sum of `(running hit count / rank)` at each relevant hit, divided by `min(relevantCount, k)`.
- **nDCG@k**: `DCG@k / IDCG@k` using gain `2^grade - 1` and discount `log2(rank + 1)`; `IDCG@k` uses qrels grades sorted descending as the ideal ranking.
- **missing_runs**: count of qrels entries whose `query_id` has no corresponding entry in the run file (their `hits` are treated as 0 for all metrics above).

### Judge metrics (`judge`), computed per record then averaged

All four scores are token-overlap ratios: tokenize both sides (lowercase, split on anything that is not a letter or digit, tokens shorter than 3 bytes dropped, stopwords removed; no stemming), then `matched-unique-source-tokens / unique-source-tokens`.

- **answer_relevance**: overlap of `answer` tokens against `question` tokens.
- **context_relevance**: overlap of joined `contexts` tokens against `question` tokens.
- **groundedness**: overlap of `answer` tokens against joined `contexts` tokens.
- **reference_coverage**: overlap of `answer` tokens against `reference` tokens (`0` if `reference` is empty/omitted).
- **unsupported_tokens**: the first 5 (alphabetically) unique `answer` tokens not found in `contexts` tokens.
- **missing_context_hints**: the first 5 (alphabetically) unique `reference` tokens not found in `contexts` tokens.

Stopwords: the, and, for, with, that, this, from, into, are, was, were, have, has, had, your, about, then, than, when, what, why, how, using, used, their, there, will.

Direction matters: each ratio is the share of the *first* text's unique tokens present in the second, so `answer_relevance` and `context_relevance` shrink as the answer or contexts grow, `reference_coverage` ignores reference content the answer omits, and an answer equal to the question scores `answer_relevance` 1.0. Numbers under 3 characters are dropped (`42` and `24` both vanish), and text without spaces (CJK) tokenizes into one token per run of characters. Verified by running `judge` on crafted records.

This is a lexical heuristic (no LLM, no embeddings): the scores order runs on the same questions and surface answer words to verify by hand; they do not establish correctness.
