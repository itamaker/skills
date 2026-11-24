---
lessons:
  - id: cos-001
    added: 2026-11-23
    status: active
---

# Chief-of-staff lessons

General lessons for the chief-of-staff role. Read at entry, before
starting work. Protocol: [lessons.md](../lessons.md).

## [cos-001] A round with no runnable lane is stated honestly, with trigger conditions

- Trigger: The scope sweep at round start finds no runnable lane.
- Pattern: Pressure to keep the round "productive" by inventing a lane — a wording tweak, re-running a check whose inputs have not changed, or a re-run of a blocked spike.
- Do instead: Record the checklist with each check's verdict and the trigger condition that would unblock the next lane, then close the round; do not ship a version bump for an empty round.
- Why: A padded lane consumes review, merge, and release cycles for no user value, and a checklist that claims "done" on fake work stops being trusted as a record of what is actually blocked.
