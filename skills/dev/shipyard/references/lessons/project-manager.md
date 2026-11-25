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
  - id: pm-004
    added: 2026-11-23
    status: active
  - id: pm-005
    added: 2026-11-23
    status: active
  - id: pm-006
    added: 2026-11-25
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

## [pm-004] "Ready for review" is a request for review, not a review

- Trigger: A worker reports "ready for review" but cannot invoke reviewers itself.
- Pattern: Treating "ready for review" as reviewed and merging.
- Do instead: The coordinator obtains the review itself before merging; "ready for review" is a request for review, not a review.
- Why: Review coverage is the coordinator's responsibility when the worker has no way to obtain it.

## [pm-005] A post-GO suggestion needs the reviewer's stated re-proof, nothing more

- Trigger: A reviewer returns GO with an optional hardening suggestion.
- Pattern: Either ignoring the suggestion silently or demanding a full re-review after adopting it.
- Do instead: Adopt it only if the reviewer stated what re-proof suffices — if they did not, ask them to name it rather than guessing — run exactly that, and record it.
- Why: The reviewer's stated re-proof is the contract for the change; anything more wastes a review cycle, anything less leaves it unproven.

## [pm-006] A blocked review channel is neither a review nor a reason to freeze

- Trigger: The coordinator cannot reach any reviewer — the review channel itself has failed, not merely a worker that cannot invoke one.
- Pattern: Stalling the round waiting for the channel, or merging the work unreviewed.
- Do instead: Verify the work yourself where the rules allow, record exactly what could not be independently reviewed, and report the block upward.
- Why: A blocked channel is not a review, but it is also not a reason to freeze the round — the work can still be checked within authority and the gap made explicit.
