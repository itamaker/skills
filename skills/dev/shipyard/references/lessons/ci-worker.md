---
lessons:
  - id: cw-001
    added: 2026-11-24
    status: active
---

# CI-worker lessons

General lessons for the ci-worker role. Read at entry, before starting
work. Protocol: [lessons.md](../lessons.md).

## [cw-001] Capture a producer's output before grepping it under pipefail

- Trigger: A shell gate asserts on `producer | grep -q pattern` with `set -o pipefail`.
- Pattern: The check intermittently fails on a binary that provably satisfies it — a SIGPIPE race: the producer dies on a closed pipe as grep exits.
- Do instead: Capture the producer's output to a variable or file first, then grep the captured output.
- Why: The failure reads as a product defect and burns a re-run, while the product was never at fault.
