# Model-invoked vs user-invoked

Every `SKILL.md` in this repo is a skill. The one axis that splits them is **invocation**, who can reach it:

- **User-invoked**: reachable only by the human typing its name. Set `disable-model-invocation: true` in the frontmatter (Claude Code) and `policy.allow_implicit_invocation: false` in `agents/openai.yaml` (Codex). The `description` is human-facing: a one-line summary, no trigger phrases.
- **Model-invoked**: reachable by the model or the user. The default: omit `disable-model-invocation` and the `policy` block. The `description` is model-facing and carries the triggers ("Use when ...").

Keep the two harnesses in sync: a skill is user-invoked in both or in neither.

Every skill has an `agents/openai.yaml` beside its `SKILL.md` with `interface.display_name` and `interface.short_description` for the Codex skill picker.

Today every skill in this repo is model-invoked. When the first user-invoked skill is added, split the bucket README and the top-level README lists into **User-invoked** and **Model-invoked** groups.

## Descriptions

The `description` in the frontmatter is what decides whether the agent reaches for a skill, so keep it short (about 250 characters, and `scripts/check-skills.mjs` fails above 300):

- Lead with what the skill is, then one `Use when ...` sentence.
- One trigger per distinct case. Synonyms for the same case are one trigger written twice.
- Do not repeat what the body already says (install steps, flags, examples).

The README lists are separate, human-facing one-liners; see `CLAUDE.md` for where they live.

## Dependencies between skills

Express a dependency as an explicit instruction to call the Skill tool with the named skill, not as a deep `../other-skill/FILE.md` link. Shared reference material lives inside the skill that owns it.
