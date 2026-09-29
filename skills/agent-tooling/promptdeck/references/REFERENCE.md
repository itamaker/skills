# promptdeck Reference

Verified against the `render`, `matrix`, and `optimize` subcommands in `internal/app/commands.go`, `internal/app/render.go`, and `internal/app/optimize.go`.

## Global behavior

- `promptdeck` with no arguments launches the TUI (see SKILL.md step 5).
- `promptdeck <unknown>` prints usage to stderr and exits `2`.
- There is no `-h`/`--help` flag; passing one is treated as an unknown subcommand (usage on stderr, exit `2`).
- There is no `version` subcommand.

## `render`

```text
promptdeck render -template <path> -vars <path> [-out <path>]
```

| Flag | Required | Description |
| --- | --- | --- |
| `-template` | yes | Path to a Go `text/template` file. |
| `-vars` | yes | Path to a JSON object, or a JSON array of objects. |
| `-out` | no | Write rendered output here instead of stdout. Overwrites silently. |

- Missing `-template` or `-vars`: prints `both -template and -vars are required` to stderr, exit `2`.
- Template parse/read errors or vars decode errors: message to stderr, exit `1`.
- If `-vars` is a JSON array, each item is rendered independently and the results are joined with `\n---\n`.
- Success exits `0`.

## `matrix`

```text
promptdeck matrix -template <path> -matrix <path> [-out-dir <dir>] [-ext <ext>] [-manifest <path>]
```

| Flag | Required | Default | Description |
| --- | --- | --- | --- |
| `-template` | yes | | Path to a Go `text/template` file. |
| `-matrix` | yes | | Path to a JSON object of `string -> []string`. |
| `-out-dir` | no | (stdout) | If set, write one file per candidate here instead of printing to stdout. |
| `-ext` | no | `.txt` | Extension used for files written under `-out-dir`. |
| `-manifest` | no | | If set, also write a JSON array of candidates (`{index, vars, prompt}`) here. |

- Missing `-template` or `-matrix`: `both -template and -matrix are required` to stderr, exit `2`.
- Candidate generation: the Cartesian product of all matrix value arrays, in **sorted key order**, is expanded into one candidate per combination. Candidates are numbered `index = "001", "002", ...` in generation order; an empty matrix (`{}`) produces exactly one candidate with `index = "001"` and no other vars.
- Each candidate's `vars` map includes its own `index` key alongside the matrix keys — if the matrix JSON itself defines an `"index"` array, it is silently overwritten by the generated sequential index.
- Without `-out-dir`: all rendered prompt bodies print to stdout, separated by `\n---\n`.
- With `-out-dir`: directory is created if missing (`0o755`); one file per candidate is written as `<index><ext>` (e.g. `001.txt`); on success prints `wrote <N> prompts to <dir>` to stdout. Existing files with the same name are overwritten.
- `-manifest` can be combined with either output mode; it writes `json.MarshalIndent` of the full candidate list (`[]PromptCandidate`), pretty-printed with a trailing newline.
- Errors reading/parsing the template or matrix, or writing output: message to stderr, exit `1`.

## `optimize`

```text
promptdeck optimize -template <path> -matrix <path> -scores <path> [-top N] [-out <path>] [-json]
```

| Flag | Required | Default | Description |
| --- | --- | --- | --- |
| `-template` | yes | | Same template used to (re)build candidates. |
| `-matrix` | yes | | Same matrix used to (re)build candidates. |
| `-scores` | yes | | Path to a JSON array of `{index, score, notes?, extra?}`. |
| `-top` | no | `3` | Number of ranked candidates to include in the `top` list/report. Values `<= 0` fall back to `3`. |
| `-out` | no | | Write the single best-scoring prompt body here. Overwrites silently. Skipped if no candidate matched a score. |
| `-json` | no | `false` | Emit a single `OptimizationReport` JSON object instead of the human-readable report. |

- Missing any of `-template`/`-matrix`/`-scores`: `template, matrix, and scores are required` to stderr, exit `2`.
- `optimize` recomputes candidates the same way `matrix` does (same Cartesian expansion, same `index` numbering) — it does **not** read a manifest file directly. The `-matrix` passed to `optimize` must be the one that produced the `index` values referenced in `-scores`.
- Candidates whose `index` has no matching entry in `-scores` are dropped from ranking (excluded from `scored`, `best`, `top`, and factor effects).
- Ranking sorts by `score` descending, then `index` ascending as a tiebreak.
- `factor_effects` averages `score` per individual `variable=value` pair (excluding the `index` key) across all scored candidates that used it, sorted by average score descending (ties broken by variable, then value), capped at 8 entries.
- Human-readable output (default): `Candidates: N`, `Scored: N`, `Best prompt: #<index> score=<3dp>`, a `Top prompts:` list, and a `Best factors:` list.
- `-json` output shape (`OptimizationReport`):
  ```json
  {
    "candidates": 16,
    "scored": 4,
    "best": { "index": "002", "score": 0.91, "vars": {...}, "prompt": "...", "notes": "..." },
    "top": [ { "index": "002", "score": 0.91, "vars": {...}, "prompt": "...", "notes": "..." }, ... ],
    "factor_effects": [ { "variable": "tone", "value": "skeptical", "count": 2, "avg_score": 0.875 }, ... ]
  }
  ```
- Errors building candidates or loading scores: message to stderr, exit `1`. Success exits `0` in both output modes.

## Template format

- Templates are standard Go `text/template` files, parsed with `template.ParseFiles`.
- Registered template functions: `join` (`strings.Join`), `upper` (`strings.ToUpper`), `lower` (`strings.ToLower`), `title` (`strings.Title`).
- Variables are referenced as `{{.key}}`, where `key` matches a field in the vars object or matrix.

## JSON schemas

**`vars.json`** (for `render`) — one of:
```json
{"artifact": "retrieval experiment report", "audience": "platform engineers", "tone": "direct", "depth": "high", "risk": "low"}
```
or a JSON array of such objects (rendered and concatenated with `\n---\n`).

**`matrix.json`** (for `matrix` and `optimize`) — object of string arrays; any key can supply zero, one, or many values:
```json
{
  "artifact": ["agent runbook", "evaluation report"],
  "audience": ["researchers", "infra engineers"],
  "tone": ["direct", "skeptical"],
  "depth": ["medium"],
  "risk": ["low", "medium"]
}
```
An empty array for a key still produces one candidate with that key set to `""`.

**`scores.json`** (for `optimize`) — array of score records, matched to matrix candidates by `index`:
```json
[
  {"index": "001", "score": 0.72, "notes": "Good structure, but too soft on blocking issues."}
]
```
`notes` is optional; an `extra` object of `string -> number` is accepted on the input type but is not currently used in ranking or output.

**manifest output** (`-manifest` on `matrix`) — array of `{index, vars, prompt}`, identical in shape to the `top`/`best` candidate objects `optimize -json` emits (minus `score`/`notes`).
