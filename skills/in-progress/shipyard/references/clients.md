# Client installation and roles

This skill is maintained in `itamaker/skills/skills/in-progress/shipyard`. This is the development location, excluded from the promoted Claude plugin bundle and release catalog. Development here does not trigger a release. Once the source is available on the selected repository ref, install it directly for development use:

```bash
npx skills@latest add itamaker/skills --skill=shipyard
```

Select **Global** installation scope and both Codex and Claude Code when asked. Project scope does not satisfy the native adapters' user-global paths. Codex's personal entry is `~/.agents/skills/shipyard/SKILL.md`; Claude's is `~/.claude/skills/shipyard/SKILL.md`. For noninteractive installs, explicitly add `-g` as well as your client selections; `--yes` alone defaults to project scope. For a maintainer checkout, the repository's `scripts/link-skills.sh` links all eligible skills, including this one, into both directories; inspect existing links before running it because that script replaces existing destinations. Pick one installation route to avoid duplicate skill discovery.

Future publication and installation belong to the skills repository. Promote to a stable bucket and update that repository's catalog/plugin metadata only as a separate authorized release task. Native role sources are part of this skill, not a separate dotfiles dependency.

## Optional native role setup

The skill is self-contained: `assets/codex` and `assets/claude` own the native role templates, model choices, and optional launch configuration. The old `dot_codex` and `dot_claude` source directories are retired from dotfiles. Do not load all assets into context during ordinary work.

After globally installing the skill, preview then explicitly apply its native configuration:

```bash
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both --apply
```

For a Claude-only installation, run the same script from `~/.claude/skills/shipyard` with `--client claude`. The installer backs up changed named destinations, preserves unrelated/global settings, and only installs the package's six roles and optional launch files. Install scripts do not run on ordinary skill invocation. The native installer targets Linux/macOS and uses POSIX filesystem protection. Python 3.11+ is required for the Codex launcher; cleanup needs Python 3, Git and authenticated `gh`.

Launch the configured primary session:

```bash
~/.codex/chief-of-staff
claude --settings ~/.claude/chief-of-staff.settings.json --agent chief-of-staff
```

The Codex launcher reads its adjacent standalone config and passes role registrations as CLI overrides; it preserves the user's global config and does not require a pre-existing named profile. `~/.codex/chief-of-staff --print-command` previews the arguments. Skill-only sessions can invoke `$shipyard` in Codex or `/shipyard` in Claude Code; delegation requires installed/native roles. None of these configurations starts a background runner.

| Responsibility | Codex role | Claude role |
| --- | --- | --- |
| Primary dispatcher | `chief_of_staff` / main | `chief-of-staff` / main |
| Workstream coordinator | `project_manager` | `project-manager` |
| Implementation | `implementation_worker` | `implementation-worker` |
| Architecture | `architecture_advisor` | `architecture-advisor` |
| Code review | `code_advisor` | `code-advisor` |
| Visual review | `visual_advisor` | `visual-advisor` |

Use the actual configured role name. If delegation is unavailable, the primary agent handles work serially and records required independent evidence as unavailable; it does not claim a second review happened. Advisors remain read-only. Follow the host's permission model for every action; skill invocation does not expand authorization.
