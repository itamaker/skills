# Coordination

## Intake and ownership

One primary conversation is the authoritative dispatcher across both clients. Separate clients share an atomic claim service or route assignments through this dispatcher; a text owner field is not a lock. Reconcile the existing ticket, worker, branch, worktree, PR, and pending checks before takeover or retry.

Turn requirements into verifiable tickets. Each needs an owner/coordinator, source, objective, repository/base, allowed files and interfaces, dependencies, acceptance, selected checks with rationale, and delivery authorization. Keep incomplete decisions out of ready work while independent tickets proceed. For a simple task keep this in the conversation; use the project's task records for sustained work. Agree on the source of truth, repository scope, budget/window, and stop conditions before unattended execution.

Use one PM only for a workstream needing sustained decomposition or acceptance tracking. CoS owns portfolio priorities and integration; each PM is the sole writer of its assigned project record. Workers report through their coordinator and preserve everyone else's changes.

## Dispatch and milestones

Parallel ticket branches in one repository need separate worktrees/checkouts. Otherwise serialize their checkout, edits, tests, commits, and pushes. Specify ownership before dispatch; coordinate shared interfaces before dependent edits. Workers implement one active milestone at a time and do not dispatch PMs or implementation workers.

Choose independently reviewable behavior slices, usually 30–90 minutes of active work. Each has acceptance, dependencies, a reviewer, and a checkpoint. When remote delivery is authorized, publish a Draft PR at the first meaningful verified slice after applicable reviews; update the same PR at later verified checkpoints. After 60 minutes without a publishable checkpoint, return diff, checks, blocker, and next slice; do not make empty commits to satisfy a timer.

Track `draft -> ready -> running -> review -> done`, with `blocked` and its reason available from active states. An early Draft PR leaves the ticket running. Review starts when all planned work and evidence are ready; done requires acceptance and the authorized delivery outcome. Checkpoint revision, worktree, branch, PR, checks, findings, and next action before interruption.

## Reviews and acceptance

CoS schedules only applicable gates:

- Architecture before consequential shared-interface, data-model, or migration decisions.
- Impeccable before each agent's UI implementation; independent visual advice after design direction and rendered implementation when visual judgment is material.
- Code review after relevant checks and before consequential PR publication/updates.
- A focused advisor when targeted investigation leaves a consequential failure unresolved.

Workers return evidence and release their slot before waiting on review when possible. Reuse a review only when the question and covered evidence remain unchanged. Record why a gate was skipped instead of consulting every advisor by default.

PM (or CoS without a PM) accepts each criterion with revision-specific evidence and distinguishes passed, failed, and unverified. CoS checks integration before final delivery. For authentication, payments, destructive migrations, or critical user journeys, assign independent functional verification to CoS/PM or a temporary verification-only worker; an author's self-test is not independent verification.

Continue already approved ready work within the budget. Preserve blocked work and proceed with independent work. A skill/configuration is not an unattended runner: verify the actual session/scheduler and access before claiming continuous execution.
