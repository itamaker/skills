---
lessons:
  - id: va-001
    added: 2026-11-23
    status: active
---

# Visual-advisor lessons

General lessons for the visual-advisor role. Read at entry,
before starting work. Protocol: [lessons.md](../lessons.md).

## [va-001] Verify a worker's 'cannot be verified here' claim by attempting the check

- Trigger: A worker claims a check cannot be performed in this environment.
- Pattern: Accepting the claim and leaving the fix unverified.
- Do instead: Attempt the check with the same tooling available to the reviewer; if it succeeds, the claim is refuted and the fix gets a real verification.
- Why: "Cannot" is often "did not try with the right driver".
