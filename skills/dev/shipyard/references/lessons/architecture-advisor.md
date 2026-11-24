---
lessons:
  - id: aa-001
    added: 2026-11-23
    status: active
---

# Architecture-advisor lessons

General lessons for the architecture-advisor role. Read at entry,
before starting work. Protocol: [lessons.md](../lessons.md).

## [aa-001] A new credential type leaking through an existing reporting path blocks the lane

- Trigger: A lane introduces a new kind of credential.
- Pattern: Treating a leak of the new credential through an existing configuration-reporting tool as a follow-up because the leak predates the lane for other credential types.
- Do instead: Check every existing reporting/inspection path that dumps configuration for leaks of the new credential before merge; a leak of the new type blocks the lane.
- Why: The lane would ship a new leak, and the fix is usually the same small change that closes the older leaks of the same shape.
