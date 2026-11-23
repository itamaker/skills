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
