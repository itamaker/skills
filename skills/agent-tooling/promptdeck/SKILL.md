---
name: promptdeck
description: Render, batch, and rank prompt variants with the promptdeck CLI from templates and JSON variables. Use when rendering a prompt from a template, expanding an experiment matrix into variants, or ranking scored variants to find the best combination.
---

# promptdeck

`promptdeck` is a Go CLI that renders Go text-template prompts from JSON variables, expands them into Cartesian experiment matrices, and ranks variants against a scores file. It has three real subcommands (`render`, `matrix`, `optimize`) plus an interactive Bubble Tea TUI. Prefer invoking the subcommands directly — they are the same commands the TUI shells out to internally.

## Workflow

1. Make sure `promptdeck` is available.
   - If installed (`brew install itamaker/tap/promptdeck`), call it directly: `promptdeck <subcommand> ...`.
   - If working from a source checkout of the tool's repository (github.com/itamaker/promptdeck-skill), build once with `go build -o promptdeck .` and call `./promptdeck`, or run ad hoc with `go run . <subcommand> ...`.

2. Render one prompt from a template and a JSON vars file:
   - `promptdeck render -template <template.tmpl> -vars <vars.json> [-out <file>]`
   - `-vars` accepts either a single JSON object (one rendered prompt) or a JSON array of objects (each rendered, joined with a `\n---\n` separator).
   - Without `-out`, the rendered body prints to stdout. With `-out`, it is written to that file instead (silently overwriting it) and nothing prints to stdout.

3. Batch-render an experiment matrix into every variable combination:
   - `promptdeck matrix -template <template.tmpl> -matrix <matrix.json> [-out-dir <dir>] [-ext .txt] [-manifest <manifest.json>]`
   - `-matrix` is a JSON object whose values are string arrays; every combination (Cartesian product) becomes one candidate, numbered `001`, `002`, ... in sorted-key order.
   - Without `-out-dir`, all rendered prompts print to stdout separated by `\n---\n`. With `-out-dir`, each candidate is written as `<index><ext>` (default extension `.txt`) inside that directory instead, and a `wrote N prompts to <dir>` summary prints to stdout.
   - Add `-manifest <path>` (combinable with either output mode) to also write a JSON array of `{index, vars, prompt}` objects — this is the input `optimize` expects to pair with a scores file.

4. Rank scored prompt variants and surface the best-performing factors:
   - `promptdeck optimize -template <template.tmpl> -matrix <matrix.json> -scores <scores.json> [-top N] [-out <file>] [-json]`
   - `optimize` rebuilds the same candidates `matrix` would produce from `-template`/`-matrix`, then joins them by `index` against `-scores` (a JSON array of `{index, score, notes?}`). Candidates with no matching score entry are dropped from ranking.
   - Default `-top` is 3. Human-readable output (default) prints candidate/scored counts, the best candidate, the top-N ranked list, and per-factor average scores. Pass `-json` to emit the same data as a single `OptimizationReport` JSON object instead.
   - Pass `-out <file>` to also write the single best-scoring prompt body to that file (silently overwriting it).

5. Interactive mode: running `promptdeck` with no arguments (or `promptdeck tui` / `promptdeck interactive`) launches a Bubble Tea terminal UI that walks through the same three actions with prompted fields. It requires a real terminal — don't use it for scripted/agent-driven invocations; use the direct subcommands above instead.

For the full flag list, JSON schema details, template function reference, and exit codes, see `references/REFERENCE.md`.

## Safety Rules

- `-out`, `-out-dir`, and `-manifest` overwrite existing files without confirmation or backup.
- `matrix -out-dir` file names come only from that run's own sequential index (`001.txt`, `002.txt`, ...). Re-running with a different template or matrix against the same `-out-dir` silently overwrites unrelated prior output with no warning — confirm the target directory is empty or expendable before reusing it.

## Prompt Patterns

- "Render examples/review.tmpl with examples/vars.json and show me the output."
- "Generate every prompt variant from this experiment matrix."
- "Batch-render this template against the matrix and write a manifest I can score later."
- "Write all the rendered variants out as individual .txt files."
- "Which tone and risk combination scored best in this experiment?"
- "Rank the top 5 scored prompt variants as JSON."
- "Optimize this prompt template using the scores file and save the winning prompt to a file."

## Resources

- `examples/review.tmpl`: example Go text template (`{{.artifact}}`, `{{.audience}}`, `{{.tone}}`, `{{.depth}}`, `{{.risk}}`).
- `examples/vars.json`: example single-object input for `render`.
- `examples/matrix.json`: example matrix input (object of string arrays) for `matrix` and `optimize`.
- `examples/scores.json`: example scored-run input for `optimize`.
- `references/REFERENCE.md`: full flag reference per subcommand, JSON schema for vars/matrix/scores/manifest, template functions, and exit codes.
