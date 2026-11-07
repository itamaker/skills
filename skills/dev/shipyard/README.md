# shipyard

A skill for running agent-delivered work with Claude Code and Codex without losing track of it. The main conversation owns your goal, priorities and final acceptance. It handles small tasks itself and brings in workers, a project manager or advisors only when their independent work saves more time than the handoff costs. Shipyard also fixes which model and effort each stage uses, how checks and reviews are accepted, and how a merged branch gets cleaned up.

## What it covers

- **Delegation with clear ownership.** Every task gets one coordinator and a bounded brief: objective, owned files, interfaces, dependencies, acceptance and the checks to run. Parallel tickets in one repository need separate worktrees.
- **Scoped checks.** Workers run only the tests tied to their ticket. The full suite belongs to the coordinator's CI and integration stage, and passing checks and reviews are reused while the revision and environment are unchanged.
- **Model and effort per stage.** One central policy picks the model and effort by task and risk. You can override it for one task, for the next worker, for a project or for yourself.
- **Delivery that stays inside your authorization.** Branches are pushed without force and as Draft PRs only when you authorized it. Opening a PR never implies merge or deploy.
- **Safe cleanup.** After an authorized merge, a helper script deletes the merged branch only when every guard passes and otherwise leaves it as `cleanup-pending` with the reason.

## Quick start

Install the skill (see below), then ask in plain words, or use flat parameters:

```text
/shipyard --implement sonnet:medium --code-review opus:high
/shipyard --verify sonnet:high --ci sonnet:medium --deliver haiku:low
/shipyard --implement sonnet:medium --preview
/shipyard --config
```

Codex uses `$shipyard` with its own model IDs:

```text
$shipyard --implement gpt-6.1-sol:medium --verify gpt-6.1-sol:high
```

Plain requests also work: "use deep for this task", "next worker: model=sonnet, effort=high", "save economy for this project's workers", "show active settings".

## Stages and parameters

Every value is `MODEL:EFFORT` or `auto`. Models and efforts must be declared in the selected policy, and `auto` clears inherited pins for that stage.

| Parameter | Stage | Agent |
|---|---|---|
| `--plan` | plan | `project-manager` |
| `--architecture` | design | `architecture-advisor` |
| `--design-review` | design | `visual-advisor` |
| `--implement` | implement | `implementation-worker` |
| `--code-review` | review | `code-advisor` |
| `--visual-review` | review | `visual-advisor` |
| `--verify` | verify | `verify-worker` |
| `--ci` | ci | `ci-worker` |
| `--deliver` | deliver | `deliver-worker` |

Parameters are validated by a helper script before anything is saved: unknown or conflicting input is rejected and nothing is written. Saving a setting does not enable a stage or create an agent.

## Where a setting lives

| You ask for | Lasts |
|---|---|
| A task override ("use deep for this task") | Until the task ends or is cancelled; nothing is written to disk |
| A one-shot override ("next worker: …") | Consumed by the next matching worker once it has been created |
| A project default | Saved in that project, after a preview |
| A personal default | Saved for you, after a preview |

Requested settings are never reported as effective unless the host confirms them. If the host's role configuration or environment blocks a choice, Shipyard reports the constraint instead of starting a mis-configured agent.

## Optional native roles

The skill can install nine named roles for Codex and Claude Code, plus a `chief-of-staff` launcher. This is an explicit setup step; loading the skill never registers roles or starts a scheduler. The role templates point at user-global skill paths, so install the skill directly and with **Global** scope rather than through the Claude plugin, then preview and apply:

```bash
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both
python3 ~/.agents/skills/shipyard/scripts/install_clients.py --client both --apply
```

For Claude only, run the script from `~/.claude/skills/shipyard` with `--client claude`. The installer backs up what it changes and leaves unrelated settings alone. Start the configured primary session with `~/.codex/chief-of-staff` or `claude --settings ~/.claude/chief-of-staff.settings.json --agent chief-of-staff`.

## Cleaning up a merged branch

```bash
python3 /path/to/shipyard/scripts/cleanup_merged.py --repo owner/repo --pr 123 --released --apply
```

Omit `--apply` for a read-only preview. It needs Python 3, Git and an authenticated `gh`. The helper checks that the PR was merged in the same repository, protects the default branch and common long-lived names, skips any checked-out worktree, and requires the local and remote branch to match the merged PR's exact head. `--released` is your assertion that no worker still owns the branch.

## Where things live

```
<skills dir>/shipyard/                the skill (wherever your install puts it)
├── SKILL.md                          the workflow Claude follows
├── README.md                         this file
├── references/                       one file per role or topic:
│                                     commands, configuration, models, coordination,
│                                     implementation, verification, delivery, staffing, clients
├── scripts/                          parameter parser, settings, client installer, cleanup helper
└── assets/
    ├── model-policy.json             the central model and effort policy
    ├── claude/                       Claude Code role templates and launcher settings
    └── codex/                        Codex role templates and launcher config
```

## Install

```bash
npx skills@latest add itamaker/skills --skill=shipyard
```

The Claude Code plugin also ships it as `/itamaker-skills:shipyard`. Pick one route; both accept the same parameters.
