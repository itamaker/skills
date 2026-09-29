Skills are organized into bucket folders under `skills/`:

- `agent-tooling/`: building and evaluating LLM agents (skillforge, runlens, ragcheck, promptdeck, datasetlint)
- `web/`: web pages and web-based design tools (webpage-to-pdf, stitch, remote-browser)
- `dev/`: everyday development workflow (go-workspace-skill)
- `in-progress/`: beta: public on purpose, feedback wanted, not shipped in the plugin
- `misc/`: kept around but rarely used, not promoted
- `deprecated/`: no longer used

Every skill in `agent-tooling/`, `web/` or `dev/` (the **promoted** buckets) must have a line in its bucket `README.md`, the same line in the top-level `README.md`, and an entry in `.claude-plugin/plugin.json`'s `skills` array. The plugin ships exactly the promoted set. Skills in `in-progress/`, `misc/` and `deprecated/` must not appear in `plugin.json` or the top-level `README.md`.

Each bucket `README.md` lists every skill in the bucket as `- **[name](./name/SKILL.md)**: one-line description`. That line is the canonical short description: the top-level `README.md` repeats it verbatim (with the path prefixed by `./skills/<bucket>`), and so does the `itamaker/itamaker` profile page. Change it in the bucket `README.md` first.

The `description` in each `SKILL.md` is a separate, model-facing trigger description of about 250 characters. See `.agents/invocation.md`.

Every `SKILL.md` has an `agents/openai.yaml` beside it. Install commands are copied verbatim from `.agents/install-block.md`. Run `node scripts/check-skills.mjs` after adding, renaming or moving a skill, and `claude plugin validate . --strict` after touching `.claude-plugin/`.

Five skills wrap a Go command-line tool (skillforge, runlens, ragcheck, promptdeck, datasetlint). The tool's source, release config and Homebrew formula stay in its own repository (`itamaker/<name>-skill`); only the skill folder lives here. Do not copy tool source into this repo.

To link every skill outside `deprecated/` and `misc/` into the local harness directories (`~/.claude/skills`, `~/.agents/skills`), run `scripts/link-skills.sh`. Each entry is a symlink into this repo, so a `git pull` keeps installed skills current.

`skills.sh.json` at the repo root groups the promoted skills (one group per bucket) on the skills.sh repo page. Add a new promoted skill to its bucket's group; `scripts/check-skills.mjs` fails otherwise. The file only changes how skills.sh displays the repo, and skills.sh picks up changes after the next install with telemetry enabled.
