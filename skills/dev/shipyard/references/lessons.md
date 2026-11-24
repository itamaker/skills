# Lessons

Per-role lessons: short, general rules learned from past rounds, so the
next round does not pay for the same mistake twice. This file is the
protocol; the lessons themselves live in `lessons/<role>.md`, one file
per role.

The skill ships with empty lessons files: no lessons are bundled, and
each installation accumulates its own lessons from its own rounds —
never copy lessons from another installation or seed them from past
rounds.

## Entry format

Each role file starts with a YAML frontmatter block listing every
lesson in the file, in the same order as the body. Each entry carries:

- `id`: stable, `<role-prefix>-NNN` (for example `pm-001`), never reused.
  The prefix is the first letters of each hyphenated word of the role
  file's stem (`project-manager` → `pm`, `chief-of-staff` → `cos`):

  | Role file | Prefix |
  | --- | --- |
  | `architecture-advisor.md` | `aa` |
  | `chief-of-staff.md` | `cos` |
  | `ci-worker.md` | `cw` |
  | `code-advisor.md` | `ca` |
  | `deliver-worker.md` | `dw` |
  | `implementation-worker.md` | `iw` |
  | `project-manager.md` | `pm` |
  | `verify-worker.md` | `vw` |
  | `visual-advisor.md` | `va` |
- `added`: the date the lesson was merged, `YYYY-MM-DD`.
- `status`: `active` or `retired`.
- When retired, also `retired` (date) and `retired_reason`.

The body is the lesson text: one `## [id] Title` section per lesson,
with exactly four lines in this order. Example — format
only, not a seeded lesson; it states generic textbook advice:

```markdown
---
lessons:
  - id: pm-001
    added: 2026-11-22
    status: active
---

## [pm-001] Confirm acceptance before starting work

- Trigger: A ticket is assigned and its acceptance criteria are unclear.
- Pattern: Starting work and discovering the real acceptance halfway through.
- Do instead: Confirm the acceptance criteria with the coordinator before writing code.
- Why: Rework costs more than a question asked up front.
```

- **Trigger:** the situation in which the lesson applies.
- **Pattern:** the mistake, stated as the behaviour to avoid.
- **Do instead:** the behaviour to use.
- **Why:** the reason, in one line.

Humans read the Markdown; `scripts/check_lessons.py` parses the
frontmatter and enforces: required fields present, status values valid,
retired entries carry a date and a reason, ids unique per file and
matching the body sections, and the general-only rule below.

## When a lesson is recorded

- At round close, from the round-close retrospective (see below).
- When an advisor verdict is CONDITIONAL with a generalizable cause.
- When a failure or blocker turns out not to be project-specific.

A candidate that only makes sense inside one project is dropped on the
spot, not filed.

## Who writes it

- The worker or advisor **proposes** a lesson in its final report
  (trigger, pattern, what to do instead, why).
- The advisor **validates** its generality — see
  [verification.md](verification.md).
- The coordinator **merges** it into the file and assigns the next
  stable `id` and the `added` date. ONLY the coordinator writes the
  lessons files, so parallel workers never conflict on them.

## Who reads it

- Every role reads its own `lessons/<role>.md` at entry, before starting
  work.
- The coordinator reads all nine role files at round start.

## Hard rule 1: general only

No project names, no repo paths, no commit hashes, no version numbers,
no product-specific identifiers. A lesson that only makes sense inside
one project does not belong here. If a lesson cannot be stated without
one of those, leave it out.

## Hard rule 2: dedup and retire

- Check the file before adding: if the lesson is already there, do not
  add a second copy. Never reuse an `id`.
- If a lesson turns out wrong, retire it — never silently delete it.
  Set `status: retired` in the frontmatter and add the date and the
  reason:

```yaml
  - id: pm-001
    added: 2026-11-22
    status: retired
    retired: 2026-11-22
    retired_reason: Later evidence showed the opposite, so the lesson's premise was wrong.
```

  The entry stays in the file as a record, body included.

## Self-learning loop

The files above are the memory; this loop is what keeps them alive.
It is a defined coordinator duty, not a background daemon. There is no
harvester that auto-extracts lessons from logs: pattern-matching on
logs produces noise, and the coordinator's judgment is the harvester.

### 1. Round-close retrospective (mandatory)

Before the coordinator marks a round done, it runs a lessons harvest
from that round's own artifacts: worker final reports, advisor verdicts
(especially CONDITIONAL blockers), test logs, failures, and stalls. For
each candidate, state the trigger, the general pattern, and what to do
instead. Candidates that are project-specific are dropped on the spot,
not filed.

### 2. Lesson lifecycle

Propose (worker or advisor, in the final report) → validate generality
(advisor, same check as the example entry) → merge (coordinator only,
assigns `id` and `added`) → read at next entry (every role reads its
own file before starting) → retire with a date and a reason if later
evidence contradicts it (`status: retired`, never silently delete). A
lesson that keeps failing to prevent the same mistake is flagged for
rewrite at the next retrospective.

### 3. Harvest record

Each round's harvest is appended to the round's own record, listing
lessons added, lessons retired, and candidates dropped as
project-specific — so the learning itself is auditable. (On Muse, the
round's record is the round's task record; see [muse.md](muse.md).)
