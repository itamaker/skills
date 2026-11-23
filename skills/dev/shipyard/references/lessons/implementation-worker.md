---
lessons:
  - id: iw-001
    added: 2026-11-23
    status: active
  - id: iw-002
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
