---
lessons:
  - id: va-001
    added: 2026-11-23
    status: active
  - id: va-002
    added: 2026-11-24
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

## [va-002] Never ship a prototype's overflow to dodge a clipping defect

- Trigger: A prototype avoids a clipping defect by overflowing its container.
- Pattern: Copying the prototype's overflow into the product to dodge the defect.
- Do instead: Verify the shipped layout at the target width and fix the layout to fit (narrow the element, shorten the content, or reflow) — never ship the overflow.
- Why: The overflow hides the defect in the prototype and ships it in the product.
