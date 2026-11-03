# Client installation and roles

Shipyard is published from `itamaker/skills/skills/dev/shipyard` in the stable skill catalog and Claude Code plugin. Pick one installation route. The repository's Claude plugin exposes `/itamaker-skills:shipyard`; a direct skill installation exposes `/shipyard` in Claude Code and `$shipyard` in Codex. Both accept the same parameters. See the [Claude plugin command convention](https://code.claude.com/docs/en/plugins).

For the optional native roles, choose a direct global skill installation instead of the Claude plugin: the bundled role templates reference user-global skill paths. Install the skill directly:

```bash
npx skills@latest add itamaker/skills --skill=shipyard
```

Select **Global** installation scope and the clients you use when asked. For setup with `--client both`, select both Codex and Claude Code. Project scope does not satisfy the native adapters' user-global paths. Codex's personal entry is `~/.agents/skills/shipyard/SKILL.md`; Claude's is `~/.claude/skills/shipyard/SKILL.md`. For noninteractive installs, explicitly add `-g` as well as your client selections; `--yes` alone defaults to project scope. For a maintainer checkout, the repository's `scripts/link-skills.sh` links all eligible skills, including this one, into both directories; inspect existing links before running it because that script replaces existing destinations. Pick one installation route to avoid duplicate skill discovery.

Publication and installation are managed by the skills repository. Native role sources are part of this skill, not a separate dotfiles dependency. Installing the Claude plugin makes the skill available; native role installation remains an explicit setup step through the direct global route above.

## Optional native role setup

The skill is self-contained: `assets/codex` and `assets/claude` own the native role templates and optional launch configuration; `assets/model-policy.json` centralizes model/effort choices. The old `dot_codex` and `dot_claude` source directories are retired from dotfiles. Do not load all assets into context during ordinary work.

After globally installing the skill, preview then explicitly apply its native configuration:

```bash
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both --apply
```

For a Claude-only installation, run the same script from `~/.claude/skills/shipyard` with `--client claude`. The installer backs up changed named destinations, preserves unrelated/global settings, and only installs the package's nine roles and optional launch files. Install scripts do not run on ordinary skill invocation. The native installer targets Linux/macOS and uses POSIX filesystem protection. Python 3.11+ is required for the Codex launcher; cleanup needs Python 3, Git and authenticated `gh`.

Launch the configured primary session:

```bash
~/.codex/chief-of-staff
claude --settings ~/.claude/chief-of-staff.settings.json --agent chief-of-staff
```

The default installation leaves model/effort unpinned so supported hosts can apply task-level choices. The primary session inherits the user's client settings; Shipyard does not silently change a running primary session. The Codex launcher reads its adjacent standalone config and passes role registrations as CLI overrides; it preserves the user's global config and does not require a pre-existing named profile. `~/.codex/chief-of-staff --print-command` previews the arguments. Skill-only sessions can invoke `$shipyard` in Codex or `/shipyard` in Claude Code; delegation requires installed/native roles. None of these configurations starts a background runner.

When upgrading from fixed-role assets, preview and apply the native installer again with its default `--tier inherit` to remove old pins, then start a new session. Updating the skill package alone does not rewrite already installed role files.

Both clients now use the same hyphenated agent names and filenames. Legacy underscore role keys remain readable in saved settings and custom policies. During an explicit Codex setup upgrade, regular legacy agent files identified as Shipyard-owned are moved to adjacent backups after the new assets install; unowned or linked legacy files are retained and reported. Global configuration and session/authentication data are never purged.

If the host cannot pass task-level overrides, preview an explicit next-session preset and then add `--apply` when wanted:

```bash
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both --tier balanced
```

`--tier economy`, `balanced`, or `deep` pins the selected pair in the installed native files. Those pins intentionally constrain per-task selection (especially on Codex); start a new primary session after applying. Reinstall with `--tier inherit --apply` to remove them and restore task-level override capability. Use `--policy /path/to/models.json` with an explicit tier to render a customized policy; see [models.md](models.md) for automatic selection and manual task overrides. Existing sessions/agents do not become dynamically reconfigured merely because files change.

| Responsibility | Codex role | Claude role |
| --- | --- | --- |
| Primary dispatcher | `chief-of-staff` / main | `chief-of-staff` / main |
| Workstream coordinator | `project-manager` | `project-manager` |
| Implementation | `implementation-worker` | `implementation-worker` |
| Architecture | `architecture-advisor` | `architecture-advisor` |
| Code review | `code-advisor` | `code-advisor` |
| Visual review | `visual-advisor` | `visual-advisor` |
| Independent verification | `verify-worker` | `verify-worker` |
| Scoped CI repair | `ci-worker` | `ci-worker` |
| Authorized delivery | `deliver-worker` | `deliver-worker` |

Use the actual configured role name. If delegation is unavailable, the primary agent handles work serially and records required independent evidence as unavailable; it does not claim a second review happened. Advisors remain read-only. Follow the host's permission model for every action; skill invocation does not expand authorization.
