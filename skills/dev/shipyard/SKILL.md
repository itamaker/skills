---
name: shipyard
description: Coordinate scoped agent delivery across Codex and Claude Code. Use when configuring agent model/effort defaults, delegating work, planning projects, accepting high-risk changes, delivering PRs, or cleaning up merged task branches.
---

# Shipyard

The main conversation owns the user's goal, priorities, integration, and final acceptance. Handle small tasks directly; introduce workers or a PM only when their independent work saves more time than the handoff costs.

If the text after the skill name (`/shipyard`, `/itamaker-skills:shipyard` in the Claude plugin, or `$shipyard`) begins with `--`, follow [commands.md](references/commands.md) first and pass the literal arguments to the flat-parameter helper. Do not reinterpret malformed flags as natural language or interpolate them into shell code. With no parameters, continue the normal workflow; natural-language requests remain available.

## Load only your path

- **Configure models:** for `/shipyard` or `$shipyard` requests to change/show/reset model settings, read [configuration.md](references/configuration.md) first. Map intent to task, one-shot, project, or personal scope; persist only an explicit save request.
- **Coordinator / PM:** read [coordination.md](references/coordination.md) for dispatch, exclusive ownership, milestones, and recovery. Read [verification.md](references/verification.md) when defining checks or accepting a revision.
- **Model / effort selection:** before starting a subagent, follow [models.md](references/models.md). Select by task and risk from the central policy, honor explicit overrides, and check the actual host's override support.
- **Implementation worker:** read [implementation.md](references/implementation.md). Run only tests and checks related to the ticket's behavior and affected dependencies; full-suite execution belongs to the coordinator's CI/integration stage.
- **Advisor:** answer the bounded question using current evidence. Remain read-only, return actionable findings, and finish without spawning helpers. Read [verification.md](references/verification.md) only when test/acceptance policy is the question.
- **Merge / cleanup:** read [delivery.md](references/delivery.md) before publishing, merging, or deleting a task branch.
- **Team design / CI placement:** read [staffing.md](references/staffing.md) only when choosing roles or changing the pipeline.
- **Client setup:** read [clients.md](references/clients.md) when installing the bundled native role assets or mapping role names. Installation is an explicit setup step; loading the skill does not register roles or start a background scheduler.

## Execution budget

Delegate a bounded context packet: objective, source requirement, owned files/interfaces, dependencies, acceptance, test selection, delivery authorization, and coordinator. Share paths and relevant excerpts rather than complete conversation histories. On tools supporting isolated context, use it for independent tickets; retain history only when needed.

Use available slots, API quotas, and local test capacity; queue when constrained and reserve capacity for required reviews. Reuse the same role for follow-up on unchanged context. Return changed files, revision/PR, exact checks and outcomes, blockers, and the next action; keep logs in artifacts and quote only relevant failure lines.

Reuse passing checks and reviews for unchanged evidence at the same revision and environment. Re-run checks affected by later changes. Stop retries on an unchanged failure and route the evidence to the coordinator. Installation or invocation of this skill does not grant permission to push, merge, deploy, or delete unrelated branches.
