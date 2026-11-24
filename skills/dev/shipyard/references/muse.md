# Muse host mapping

Shipyard 2.1.3 assumes a Codex/Claude host. This file maps every Shipyard
concept to Muse, decoupled from the Codex/Claude documentation: nothing in
the Codex/Claude sections changes meaning because of this file, and this
file is the only place Muse behavior is described. The Muse install route
(no native role install) is documented in [clients.md](clients.md).

## Roles: subagent briefs, not installed roles

Muse has no installed native roles and no resident agents. Each Shipyard
role is a spawned subagent given a bounded brief (objective, owned files,
dependencies, acceptance, delivery authorization, coordinator). Loading
the skill does not register roles or start a background scheduler, and a
skill/configuration is not an unattended runner.

| Shipyard role | Muse equivalent |
| --- | --- |
| `chief-of-staff` | The primary conversation (the main Muse agent). Owns the user's goal, priorities, integration, and final acceptance. |
| `project-manager` | A coordinator subagent. Sole writer of its assigned project task record; workers report through it. |
| `implementation-worker` | A spawned subagent with a bounded ticket brief. |
| `code-advisor`, `visual-advisor` (`architecture-advisor`) | Spawned subagents with a bounded question. Read-only: answer from current evidence, return actionable findings, finish without spawning helpers. |
| `verify-worker` | A spawned subagent that runs the ticket's selected checks and reports exact commands, revision, and results. |
| `ci-worker` | A spawned subagent used only for scoped pipeline/infrastructure failures, not as a watcher of healthy deterministic jobs. |
| `deliver-worker` | A spawned subagent used only for an authorized delegated delivery operation. |

Role names are the canonical hyphenated names in
`scripts/stage_registry.py`. There are no permanent background workers:
a role exists only for the duration of its spawned subagent session.

## Tickets: the project task record

A Muse ticket is an entry in the coordinator's project task record (in
this round, `TASK_RECORD.md` under `~/workspace/shipyard-muse/`; other
projects use their own record, e.g. an `ALIGNMENT.md` checklist).
Each ticket carries the fields in [coordination.md](coordination.md):
owner/coordinator, source, objective, repository/base, allowed files and
interfaces, dependencies, acceptance, selected checks with rationale, and
delivery authorization. For a simple task the ticket may live in the
conversation instead; sustained work uses the record.

Ticket status follows `draft -> ready -> running -> review -> done`, with
`blocked` and its reason available from active states. The coordinator
records, per dispatch, the stage, agent, requested model/effort choice,
reason, host constraints, and observed effective choice (unknown when
unavailable).

## Invocation: reading the skill, not a command

Muse has no `/shipyard` or `$shipyard` command, and no native role
install. Invocation is reading `SKILL.md` plus the references it points
to. There is no equivalent of the flat-parameter path
(`scripts/shipyard.py`, [commands.md](commands.md)): its `--client`
accepts only `codex` and `claude`, and its JSON bridge rejects any other
client, so no `/shipyard --implement ...` form exists on Muse. Stage and
model preferences are recorded in the ticket record and passed in the
subagent brief instead.

Skills load directly from `~/workspace/custom-skills/` and
`~/.agents/skills/`, kept current by a daily sync from the repository
(see the Muse section of [clients.md](clients.md)).
`install_clients.py --client muse` is a reporting no-op: it prints the
same report in preview and with `--apply`, writes nothing, and exits 0.
`--client both` still means Codex and Claude Code only; Muse is never
included in `both`.

## Model/effort selection: recorded only, never applied

Muse's subagent spawn accepts no model/effort parameters, so there is no
per-task model override on this host. Selection is a plan only:

- `model_policy.py --client muse` works end-to-end. It selects from the
  same complexity/risk tier table as Codex/Claude and records the
  requested tier/model/effort (`muse-economy` / `muse-balanced` /
  `muse-deep`) in the ticket. `muse_constraints()` forces
  `application_method` to `plan_only`; `effective_model` and
  `effective_effort` stay `null` (unknown). Never claim a model changed
  because the brief or the plan mentions one.
- `model_settings.py --client muse` works end-to-end and resolves
  defaults-only when no Muse settings exist (`tier: auto`,
  `max_tier: deep`). Muse reads and writes only its own `muse` settings
  key; Codex/Claude pins never leak into Muse resolution, and vice
  versa. There is no Muse settings schema and no Muse model IDs beyond
  the policy aliases above, so in normal use there is no Muse settings
  file: per-task overrides live in the ticket record only.
- A saved `muse` key, if one ever exists, only feeds the recorded
  request. It cannot change the model any spawned subagent runs on,
  because spawn takes no model/effort parameters.

## Verification stages: local equivalents, Actions not assumed

GitHub Actions are not assumed on Muse. Whether a repository has Actions
is a property of that repository, not of the host; the coordinator
records how required checks will be satisfied for the repository at
hand. When Actions are unavailable or disabled for that repository (for
example, a repository whose CI is a local script), use the without-CI
mapping in [verification.md](verification.md): one integration
verification task for the combined candidate, assigned to
`verify-worker` or performed directly by the coordinator.

| Shipyard stage | Muse equivalent |
| --- | --- |
| Worker loop | The worker runs only the checks related to the ticket's behavior and affected dependencies, and reports exact commands, selection rationale, revision, and results. |
| Draft PR | No PR exists on Muse. The equivalent checkpoint is the worker's verified slice on the ticket branch, reported to the coordinator with revision-specific checks. |
| Ready PR / merge candidate | Full correctness regression once per candidate, on the ticket branch, before merge. For this skill the full suite is `python3 -m unittest discover -s skills/dev/shipyard/scripts/tests -p 'test_*.py' -v` (plus `node scripts/check-skills.mjs` where the repository workflow runs it). A new head invalidates previous head evidence. |
| Post-merge | Smoke/integration health after the merge, checked by the coordinator (or a `verify-worker`); the main-line branch must remain healthy, investigated or reverted through the authorized process. |
| Nightly / release | Only when the repository defines one; there is no Muse-provided nightly runner. |

Implementation workers still run only related checks; full-suite
execution belongs to the coordinator's merge-candidate stage. Reuse
passing checks and reviews for unchanged evidence at the same revision
and environment; re-run checks affected by later changes.

## Delivery: direct merge to the main-line branch, no PR flow

On Muse there is no PR flow. The coordinator merges each ticket branch
directly into the main-line branch (`shipyard-muse` in this round) by
merge commit, after coordinator acceptance and after the required checks
pass for the candidate. Permission to implement does not itself authorize
merge.

- Push and merge only within the user's authorization. Inspect the exact
  diff/staged files for credentials, private data, and unrelated changes
  before merging.
- `cleanup_merged.py` does not apply: it assumes PR merges via `gh`
  (it calls `gh api` against `github.com` and requires a `--pr` number).
  There is no PR number on a direct merge, so do not invoke it.
- After the merge, remove the ticket worktree only after confirming it
  is clean (including untracked files) and no session owns it; otherwise
  keep it and defer cleanup. Never remove or detach a live worktree just
  to make cleanup pass.
- Record the merge SHA and the deleted/retained refs in the task record,
  as [delivery.md](delivery.md) requires for any merge.

## Standing rules for this host

- **Lessons:** the per-role lessons files, the round-close harvest, and the harvest record follow [lessons.md](lessons.md); a round's harvest goes in that round's task record (`TASK_RECORD.md` in this round).
- **Decoupling.** Muse paths, settings keys, tests, and documentation
  stay separate from Codex/Claude. A Muse change never rewrites a
  Codex/Claude section, test, or behavior to accommodate it.
- **NO MAIN without the user's explicit permission.** Never commit to,
  merge into, or push `main` without the user explicitly authorizing it.
  Ticket work stays on its ticket branch until the coordinator merges it
  into the round's main-line branch (here, `shipyard-muse`) under the
  round's authorization.
- **Fix Shipyard-on-Muse problems on the branch.** If Shipyard misbehaves
  on Muse (a wrong mapping, a helper that rejects the Muse client, a
  doc that assumes a Codex/Claude-only capability), file it as a ticket
  with the usual fields and fix it on a branch. Do not silently work
  around it in a ticket brief, and do not edit the main-line branch to
  dodge it.

## No equivalent on Muse

- Native role install: none. Skills load from the local skill
  directories; `install_clients.py --client muse` only reports that.
- `/shipyard` / `$shipyard` command and flat-parameter helper: none.
  `shipyard.py --client` accepts only `codex` and `claude`.
- Per-task model/effort override: none. The selection is recorded in
  the ticket; the effective model stays unknown.
- Resident agents, background runner, unattended execution: none. Roles
  exist only as spawned subagent sessions; the skill starts no
  scheduler.
- PR flow and `cleanup_merged.py`: none on a direct merge. Delivery is
  a merge commit to the main-line branch, with merge SHA and refs
  recorded in the task record.
