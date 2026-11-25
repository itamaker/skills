---
lessons:
  - id: ca-001
    added: 2026-11-23
    status: active
  - id: ca-002
    added: 2026-11-24
    status: active
  - id: ca-003
    added: 2026-11-25
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

## [ca-002] Scope a negative claim to the surface actually searched

- Trigger: A report states "no X exists" for a whole target.
- Pattern: The evidence covers one class or entry point, but the sentence claims the whole target.
- Do instead: Write the negative for the searched surface only ("within class C, no X"), and state what a whole-target search would need to look like for the broader claim.
- Why: A surface-scoped search cannot support a whole-target negative, and the over-claim survives review precisely because it reads like the supported one.

## [ca-003] Reproduce the worker's discriminating evidence yourself

- Trigger: A review whose verdict rests on the worker's test or mutation claims.
- Pattern: Quoting the worker's pass counts as the review's evidence.
- Do instead: Re-run the suite and the mutation or negative controls in a scratch copy and report your own numbers.
- Why: A review that repeats the worker's numbers adds no independent evidence; only a reproduction can catch a harness that passes for the wrong reason.
