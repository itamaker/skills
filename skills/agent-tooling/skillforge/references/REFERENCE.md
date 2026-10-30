# skillforge Reference

Verified against the `skillforge` source (`internal/app/` in github.com/itamaker/forge-skill) and by running the built binary against `examples/`.

## Builds after v0.3.0

v0.3.0 is the last release at the time of writing; the behaviour below is in `itamaker/forge-skill` branch `fix/init-valid-skill-output` and ships with the next release. Check `skillforge --version`: v0.3.0 and earlier reject it with exit 2.

- `init` writes `SKILL.md` starting with a `---` frontmatter block holding `name` (the slug, sanitised to `[a-z0-9]` plus single hyphens, at most 64 characters) and a one-line double-quoted `description` (capped at 300 characters; when it has no `Use when` clause, one is appended from the first one or two spec triggers).
- `init` also writes `agents/openai.yaml` (`display_name`, `short_description`, `default_prompt`), rewrites `manifest.json` `slug` and the Metadata "Slug" line to the sanitised name, and prints a stderr warning (exit stays 0) when the `-out` folder name differs from the skill name.
- A spec whose name and slug contain no ASCII letter or digit exits 1 (`set an ASCII slug in the spec`) before touching `-out`. `init` prints a `note:` line on stderr when it had to drop the `Use when` clause or cut the description.
- `draft` prints `review:` lines on stderr (the triggers, constraints, checks and workflow come from category defaults; a placeholder tool was used; the name has no ASCII slug). Stdout and the spec JSON schema are unchanged, and category-specific triggers now come before generic ones.
- `-h`, `--help`, `help`, `--version` and `version` print to stdout and exit 0, at the top level and after `init`, `draft` or `tui`. Real errors keep exit 1 and 2.

## CLI

### No arguments

`skillforge` with no arguments launches the interactive Bubble Tea TUI (`tui`/`interactive` are aliases). Do not use this from an agent; it needs a real terminal.

### `skillforge init`

```text
skillforge init -spec <path> -out <dir> [-force]
```

| Flag | Required | Meaning |
| --- | --- | --- |
| `-spec` | yes | Path to a skill spec JSON file (see schema below). |
| `-out` | yes | Directory to create the scaffolded skill in. |
| `-force` | no | Overwrite `-out` if it already exists. Without it, `init` fails if `-out` exists. |

Behavior:

- Missing `-spec` or `-out`: prints `both -spec and -out are required` to stderr, exit `2`.
- Spec fails to parse or fails validation (see "Spec validation" below): prints the error to stderr, exit `1`.
- `-out` exists and `-force` not passed: prints `output directory <dir> already exists; use -force to overwrite`, exit `1`.
- `-out` exists as a non-directory and `-force` is passed: prints `output path <dir> is not a directory`, exit `1`.
- Success: prints `generated skill scaffold in <dir>`, exit `0`.

Generated files under `-out`:

- `SKILL.md` — rendered from the spec (name, description, metadata, audience, triggers as "When To Use", constraints, workflow, tools, example prompts, checks as "Validation").
- `manifest.json` — the full spec, re-serialized as indented JSON (with `slug` filled in via `slugify(name)` if it was empty).
- `bin/README.md` — one section per tool documenting its command, purpose, inputs, outputs, and example.
- `examples/usage.md` — suggested prompts (from `spec.examples`) and a validation checklist (from `spec.checks`).

### `skillforge draft`

```text
skillforge draft -brief <path> [-catalog <path>] [-out <path>] [-name <string>] [-max-tools <int>]
```

| Flag | Required | Default | Meaning |
| --- | --- | --- | --- |
| `-brief` | yes | — | Path to a natural-language brief (Markdown or plain text). |
| `-catalog` | no | — | Path to a JSON tool catalog to retrieve candidate tools from. |
| `-out` | no | — | Path to write the drafted spec JSON. If omitted, the spec prints to stdout. |
| `-name` | no | inferred | Explicit skill name; overrides the name inferred from the brief. |
| `-max-tools` | no | `3` | Maximum number of tools to retrieve from the catalog. Values `<= 0` fall back to `3`. |

Behavior:

- Missing `-brief`: prints `-brief is required` to stderr, exit `2`.
- Unreadable `-brief` file: prints `read brief: <os error>`, exit `1`.
- Unreadable or malformed `-catalog`: prints `read tool catalog: <os error>` or `decode tool catalog: <json error>`, exit `1`.
- Success without `-out`: prints the drafted spec JSON to stdout, exit `0`.
- Success with `-out`: writes the spec JSON (plus trailing newline) to that path, prints `wrote drafted spec to <path>`, exit `0`.

Drafting heuristics (all derived purely from text pattern-matching over the brief — treat as a starting point, not ground truth):

- **Name**: first non-empty, non-heading-only line under ~8 words with no colon or trailing period; falls back to `"Generated Skill"`.
- **Description**: first substantive line that isn't the name and doesn't start with `audience:`; falls back to a generic sentence.
- **Audience**: an explicit `Audience: ...` line in the brief, else a category-based default.
- **Tags / category**: keyword matches against a fixed list (`retrieval`, `rag`, `dataset`, `evaluation`, `prompt`, `trace`, `observability`, `incident`, `benchmark`, `tool`, `policy`, `research`) mapped to a small set of categories (`retrieval-evaluation`, `dataset-quality`, `observability`, `prompt-optimization`, `agent-workflow`).
- **Triggers / constraints / checks / examples / workflow**: category-specific canned strings, plus any `- `/`* ` bullet lines in the brief become `examples` verbatim.
- **Tools**: if `-catalog` is given, tools are scored by token overlap between the brief and each tool's name (weight 3) and description+example+command+inputs+outputs (weight 2), sorted by score then name, and the top `-max-tools` are kept (ties/zero-score handling included). With no catalog, or if scoring finds nothing, a single placeholder tool `replace-me` (`echo 'replace me with a real tool'`) is used instead.

If the drafted spec still fails validation (extremely unlikely given the above, but possible with an empty/whitespace-only brief and no catalog), `draft` silently falls back to a minimal spec containing only `name`, `slug`, `description`, and `tools` — it never errors out.

## Spec Schema (`SkillSpec`, used by both `-spec` for `init` and the output of `draft`)

```json
{
  "name": "string, required",
  "slug": "string, optional (auto-derived from name via slugify if empty)",
  "description": "string, required",
  "audience": "string, optional",
  "category": "string, optional",
  "tags": ["string", "..."],
  "triggers": ["string", "..."],
  "constraints": ["string", "..."],
  "checks": ["string", "..."],
  "examples": ["string", "..."],
  "workflow": [
    { "name": "string", "goal": "string" }
  ],
  "tools": [
    {
      "name": "string, required",
      "command": "string, required",
      "description": "string",
      "example": "string, optional",
      "inputs": ["string", "..."],
      "outputs": ["string", "..."]
    }
  ]
}
```

### Spec validation (used by `init`, and internally by `draft`'s fallback check)

- `name` must be non-empty after trimming whitespace.
- `description` must be non-empty after trimming whitespace.
- `tools` must contain at least one entry.
- Every tool must have a non-empty `name` and a non-empty `command`.

Error strings (printed to stderr, exit `1` from `init`):

- `spec.name is required`
- `spec.description is required`
- `spec.tools must contain at least one tool`
- `every tool requires a name and command`

## Tool Catalog Shapes (`-catalog` for `draft`)

Either shape is accepted:

1. A plain JSON array of tool objects (see `ToolSpec` fields above) — this is the shape used by `examples/tools.json`.
2. A wrapped object: `{"tools": [ ...same tool objects... ]}`.

`skillforge` tries the plain-array shape first; if that fails to parse or yields zero tools, it falls back to the wrapped shape. A catalog that is neither shape produces `decode tool catalog: <json error>`.

## slug Generation

`slugify(name)` lowercases the name, keeps letters/digits, collapses everything else to single `-` separators, and trims leading/trailing `-`. Example: `"Retrieval Evaluator"` -> `"retrieval-evaluator"`.
