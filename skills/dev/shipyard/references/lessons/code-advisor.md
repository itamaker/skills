---
lessons:
  - id: ca-001
    added: 2026-11-23
    status: active
---

# Code-advisor lessons

General lessons for the code-advisor role. Read at entry, before
starting work. Protocol: [lessons.md](../lessons.md).

## [ca-001] Show the before/after contrast in a narrow re-review

- Trigger: A narrow re-review of a fix.
- Pattern: Re-asserting that the fix was applied.
- Do instead: Show the before/after contrast — quote the exact pre-fix lines that fail the check and the post-fix lines that pass it.
- Why: Without the contrast, a re-review cannot prove the fix changes the outcome — it can only repeat the claim.
