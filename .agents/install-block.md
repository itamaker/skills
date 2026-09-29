# The canonical install block

One install story, one wording. `README.md` must say this and nothing else. Change it here first, then propagate.

## Claude Code: the plugin

<canonical-block name="claude-code">

```text
/plugin marketplace add itamaker/skills
/plugin install itamaker-skills@itamaker
```

</canonical-block>

`.claude-plugin/marketplace.json` makes this repo its own single-plugin marketplace (marketplace `itamaker`, plugin `itamaker-skills`). The plugin ships exactly the promoted buckets listed in `.claude-plugin/plugin.json`.

## Codex, and other agents: skills.sh

<canonical-block name="skills-sh-whole-set">

```bash
npx skills@latest add itamaker/skills
```

</canonical-block>

<canonical-block name="skills-sh-one-skill">

```bash
npx skills@latest add itamaker/skills --skill=<name>
```

</canonical-block>

## The two routes are exclusive

The plugin is a managed, read-only bundle. skills.sh writes files you own and edit. Installing both leaves every skill twice: always say "pick one".
