---
name: promptdeck
description: Render prompt templates (Go text/template plus JSON vars), expand a variable matrix into numbered variants, and rank scored variants with the promptdeck CLI. Use when generating prompt-experiment variants or picking the best-scoring one.
---

# promptdeck

Prompt-experiment bookkeeping. `promptdeck` renders text and ranks scores you supply; it calls no model and computes no scores. Samples in `examples/`, flag and schema tables in `references/REFERENCE.md`.

## Get the binary

`brew install itamaker/tap/promptdeck`, a release binary from github.com/itamaker/promptdeck-skill, or `go build -o promptdeck .` in a clone of that repo.

Bare `promptdeck` opens an interactive TUI that hangs an agent shell; always pass a subcommand. Usage: run `promptdeck x` (an invalid subcommand). Flags: `promptdeck matrix -h`. Both exit 2, which is expected; the CLI has no `--version`.

## Experiment loop

```bash
promptdeck render   -template t.tmpl -vars vars.json [-out f]        # one prompt (object) or several joined by ---
promptdeck matrix   -template t.tmpl -matrix matrix.json -out-dir prompts -manifest manifest.json
# score every prompts/<index>.txt yourself, write scores.json: [{"index":"001","score":0.72,"notes":"..."}]
promptdeck optimize -template t.tmpl -matrix matrix.json -scores scores.json [-top N] [-out best.txt] [-json]
```

`matrix` takes the Cartesian product of all value lists, numbered `001`, `002`, ... in sorted-key order. `optimize` rebuilds the candidates from the same template and matrix and joins your scores by `index`; it does not read the manifest, which exists to help you score.

## Reading `optimize`

- `Scored` must equal the number of rows in scores.json. Lower means some indices matched no candidate, usually because the matrix or template changed after scoring.
- `Best prompt` is the highest score (ties go to the lower index); `-out` writes its body to a file.
- `Best factors` are mean scores per `variable=value` with the count of scored candidates in parentheses. Compare values of the same variable. A count of 1 or 2 is an anecdote, and a value shared by every scored candidate carries no signal. In the example, 4 of 16 variants are scored, so `artifact`, `audience` and `depth` all show 0.782 (4).
- To trust a factor, score the full matrix or at least a few variants per value, then rerun. Only the top 8 factors print.

## Limits

- A template key missing from the vars renders as `<no value>` with exit 0. Grep rendered output for `<no value>` after any template or matrix edit.
- Matrix values must be strings; a number is a decode error (exit 1). An `index` key in the matrix is overwritten by the generated index. An empty matrix `{}` renders one prompt with only `index` set.
- Indices are positional. Adding, removing or reordering a matrix value renumbers candidates, and old scores then attach to different prompts without any warning.
- Combination counts multiply (3 keys of 5 values is 125 files); count them before running `matrix -out-dir`.
- `-top` of 0 or below becomes 3.

## Safety Rules

- `-out`, `-out-dir` and `-manifest` overwrite files without confirmation, and `-out-dir` never deletes: a run with fewer candidates leaves earlier `NNN.txt` files in place. Use an empty directory per matrix.
- `optimize -out` writes nothing, with exit 0, when no score matched.

Exit 0 ok, 1 template/JSON/file error, 2 missing required flag or unknown subcommand.
