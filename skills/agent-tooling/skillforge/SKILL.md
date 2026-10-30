---
name: skillforge
description: Draft a skill spec from a brief and tool catalog, and scaffold a skill folder from a JSON spec, with the skillforge CLI. Use when wrapping several CLI tools into one skill; for a single skill without a catalog, write SKILL.md directly.
---

# skillforge

Turns a brief plus a JSON tool catalog into a spec (`draft`), and a spec into a skill folder (`init`). The value is the consistent scaffold around real tool commands. `draft` is keyword matching with canned text, so the wording of the result is yours to write.

## Get the binary

`brew install itamaker/tap/skillforge`, a release binary from github.com/itamaker/forge-skill, or `go build -o skillforge .` in a clone of that repo.

Bare `skillforge` opens an interactive TUI that hangs an agent shell; always pass a subcommand. Flags: `skillforge draft -h`, `skillforge init -h`. Builds after v0.3.0 also accept `skillforge -h` and `--version`; v0.3.0 exits 2 on both, and an invalid subcommand prints its usage.

## Run

```bash
skillforge draft -brief brief.md -catalog tools.json -out spec.json   # -catalog optional, -max-tools N (default 3)
skillforge init  -spec spec.json -out <dir>/<skill-name>               # -force deletes an existing <dir> first
```

`init` needs `name`, `description` and at least one tool with `name` and `command`; exit 1 prints which is missing. Spec schema, catalog shapes and generated files: `references/REFERENCE.md`; samples in `examples/`.

## Finish the scaffold by hand

Treat `draft` and `init` output as a first draft. Done when every item holds:

1. `SKILL.md` starts with a `---` frontmatter block holding `name` (lowercase letters, digits, hyphens) and `description`. v0.3.0 writes no frontmatter: add it yourself, with `name` equal to the folder name.
2. The `description` says what the skill is and one `Use when ...` sentence, about 250 characters.
3. No `replace-me` tool remains. `draft` inserts it when no catalog tool matched the brief.
4. The canned sections (`When To Use`, `Constraints`, `Validation`, workflow steps) are rewritten for this skill or deleted. Their text comes from category defaults, so it fits any skill equally.
5. The folder name equals `name`, and `agents/openai.yaml` exists (builds after v0.3.0 write it; add it otherwise).

## Limits

- `draft` ranks catalog tools by word overlap with the brief, so a brief that never uses a tool's words will not select it. List the tools in the spec yourself when the match matters.
- `init -force` deletes the whole `-out` directory, including files you added; use it only when the user asks to replace the folder.
- A name with no ASCII letters or digits has no slug: set an ASCII `slug` in the spec (builds after v0.3.0 exit 1 without one).
- Exit 0 ok, 1 invalid spec or unreadable file, 2 usage error.
