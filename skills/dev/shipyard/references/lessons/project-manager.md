---
lessons:
  - id: pm-001
    added: 2026-11-23
    status: active
  - id: pm-002
    added: 2026-11-23
    status: active
  - id: pm-003
    added: 2026-11-23
    status: active
---

# Project-manager lessons

General lessons for the project-manager role. Read at entry,
before starting work. Protocol: [lessons.md](../lessons.md).

## [pm-001] Verify a lane worker's checkout is a linked worktree before it starts

- Trigger: A lane worker sets up its own checkout to implement a branch.
- Pattern: The worker builds in a standalone clone instead of a linked worktree of the main repo, so its branch does not exist in the main repo's object store and the merge fails.
- Do instead: Verify the checkout is a linked worktree of the main repo before work starts; if a standalone clone is found, fetch its branch into the main repo before attempting the merge.
- Why: A branch that lives only in a separate clone cannot be merged until it is fetched into the repo being merged into.

## [pm-002] A quiet worker's branch tip is checked before assuming it is stuck

- Trigger: A worker goes quiet past its expected completion with no handoff.
- Pattern: Assuming it is stuck and re-dispatching the same work.
- Do instead: Check the worktree/branch tip for new commits first; a missing handoff does not mean missing work.
- Why: Re-dispatching work that is already done duplicates effort and can create conflicting branches.

## [pm-003] Parallel lanes sharing a file are merged sequentially with the shared invariant re-verified

- Trigger: Two parallel lanes touch the same shared file.
- Pattern: Merging both and treating the conflict resolution as mechanical.
- Do instead: Merge sequentially; the coordinator resolves the conflict at merge time and re-verifies the merged result (tests plus the shared invariant the file expresses).
- Why: A conflict in a shared file is where two lanes' assumptions meet, and only the merged result shows whether both still hold.
