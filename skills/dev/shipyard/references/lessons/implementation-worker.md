---
lessons:
  - id: iw-001
    added: 2026-11-23
    status: active
  - id: iw-002
    added: 2026-11-23
    status: active
  - id: iw-003
    added: 2026-11-23
    status: active
  - id: iw-004
    added: 2026-11-23
    status: active
  - id: iw-005
    added: 2026-11-24
    status: active
  - id: iw-006
    added: 2026-11-24
    status: active
  - id: iw-007
    added: 2026-11-25
    status: active
  - id: iw-008
    added: 2026-11-25
    status: active
  - id: iw-009
    added: 2026-11-25
    status: active
  - id: iw-010
    added: 2026-11-25
    status: active
  - id: iw-011
    added: 2026-11-25
    status: active
  - id: iw-012
    added: 2026-11-25
    status: active
---

# Implementation-worker lessons

General lessons for the implementation-worker role. Read at entry,
before starting work. Protocol: [lessons.md](../lessons.md).

## [iw-001] Check which copy is canonical before asserting a contradiction

- Trigger: The same document exists in two places and they disagree.
- Pattern: Reading the first copy found and asserting the other is wrong.
- Do instead: Verify which copy is canonical — check modification time and which copy the work actually cites — before asserting a contradiction.
- Why: A stale copy is not evidence of an error; asserting one from it creates a false correction that then has to be undone.

## [iw-002] Parameterize the harness target

- Trigger: A differential harness must run both before and after merge.
- Pattern: Hardcoding the branch under test as the harness target.
- Do instead: Parameterize the harness target (branch or merge commit) so the same harness runs unmodified on the branch and on main after merge.
- Why: A hardcoded target forces a patched copy for the post-merge run, and the patch itself becomes something to verify.

## [iw-003] Check the fallback, not just the absent symptom

- Trigger: Removing or scoping a rule that produced a visible symptom.
- Pattern: Declaring the fix done when the old symptom is gone.
- Do instead: Inspect the final rendered state and check what the fallback now shows — a scoped rule can expose a default you never wrote.
- Why: The absence of the old symptom is not proof the new state is correct.

## [iw-004] An evidence record describes only checks the harness ran

- Trigger: Writing the evidence record for a harness run.
- Pattern: Describing a check the harness never ran as if it passed.
- Do instead: Record only checks with an artifact behind them; mark unrun checks as not run.
- Why: Reviewers check artifacts, not prose — a claim without an artifact is not evidence.

## [iw-005] Preserve an interrupted run's partial output before re-running it

- Trigger: A long-running query or analysis is cancelled mid-run.
- Pattern: Re-running it overwrites its output file, so the cancellation itself leaves no artifact.
- Do instead: Copy or rename the cancelled run's output file (or its partial output) to a preserved name before the re-run.
- Why: The interruption is itself evidence — what was running and how far it got — and once overwritten it can only be described in prose.

## [iw-006] A content ban covers comments and strings, not just executable code

- Trigger: A standing rule bans certain content from code.
- Pattern: Writing the banned content into comments or string literals, assuming the ban covers only executable code.
- Do instead: Treat comments, strings, and docs-in-code as code for the ban's scope.
- Why: Reviewers and checkers read comments too; a ban that leaks into comments is not a ban.

## [iw-007] Return the same shape on every path, including error paths

- Trigger: An operation returns a structured result with named fields.
- Pattern: Success paths include a field that error paths omit, so consumers must branch on whether the field is present.
- Do instead: Return the same fields on every path, empty when there is nothing to report.
- Why: A consumer that assumes the field exists breaks on the error path, and the break surfaces far from the omission.

## [iw-008] When the defect is a missing key, assert presence and type, not just a count

- Trigger: Writing a test for a defect where a field is missing from a result.
- Pattern: Asserting only that a count is zero — a nil collection also has length zero, so the test passes on the broken code.
- Do instead: Assert the field is present and of the right type (an empty array, not nil).
- Why: A count assertion cannot discriminate a missing key from an empty one; only a presence-and-type assertion can.

## [iw-009] Test emptiness on the normalised form, not the raw value

- Trigger: Deciding whether a value is empty or meaningless.
- Pattern: Testing the raw value, which looks non-empty.
- Do instead: Apply the same normalisation the matcher uses first, then test the normalised form.
- Why: A value can be non-empty raw and empty after normalisation, and the raw check misses it.

## [iw-010] Before implementing a capability, search for an existing unwired implementation; if one exists, build only the seam

- Trigger: A lane to add a capability.
- Pattern: Implementing the capability from scratch.
- Do instead: Search the codebase first for an existing implementation behind a missing seam; if one exists, build only the wiring.
- Why: Re-implementing what exists wastes the lane and risks two divergent implementations of one capability.

## [iw-011] Confirm the current published number of a numbered spec before implementing against it; do not implement from a remembered draft number

- Trigger: Implementing against a numbered specification.
- Pattern: Implementing against the draft number remembered from earlier work.
- Do instead: Fetch the current published text and confirm the number first.
- Why: Draft numbers change on publication, and an implementation built to a superseded draft silently diverges from the live spec.

## [iw-012] Judge a lane's scope on the merge diff, not on the post-merge tree

- Trigger: A harness scope check diffs a base commit against a tree that already contains other lanes.
- Pattern: Treating the scope failure as a lane overreach.
- Do instead: Evaluate scope on the merge diff (merge-base to branch tip); record a base-comparison failure on the merged tree as a harness artifact, not a scope violation.
- Why: The merged tree legitimately contains other lanes' files, so a tree-versus-base diff cannot distinguish this lane's scope.
