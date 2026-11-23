---
lessons:
  - id: dw-001
    added: 2026-11-23
    status: active
---

# Deliver-worker lessons

General lessons for the deliver-worker role. Read at entry, before
starting work. Protocol: [lessons.md](../lessons.md).

## [dw-001] Try the provider's API or CLI before concluding a release is broken

- Trigger: A published release asset's plain download URL fails.
- Pattern: Concluding the asset is missing or the release is broken.
- Do instead: Try the provider's API or CLI download for the same asset before concluding anything about the release.
- Why: A plain-URL failure can be an egress or proxy quirk; the API path exercises a different route to the same bytes.
