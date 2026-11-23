---
lessons:
  - id: dw-001
    added: 2026-11-23
    status: active
  - id: dw-002
    added: 2026-11-23
    status: active
  - id: dw-003
    added: 2026-11-23
    status: active
---

# Deliver-worker lessons

General lessons for the deliver-worker role. Read at entry,
before starting work. Protocol: [lessons.md](../lessons.md).

## [dw-001] Try the provider's API or CLI before concluding a release is broken

- Trigger: A published release asset's plain download URL fails.
- Pattern: Concluding the asset is missing or the release is broken.
- Do instead: Try the provider's API or CLI download for the same asset before concluding anything about the release.
- Why: A plain-URL failure can be an egress or proxy quirk; the API path exercises a different route to the same bytes.

## [dw-002] A lane's new dependency is re-resolved in every module that shares the graph

- Trigger: A lane adds a dependency to one module of a multi-module repo.
- Pattern: Assuming the other modules still build and discovering the breakage only at packaging time.
- Do instead: Re-resolve dependencies and build every module that shares the module graph before packaging.
- Why: A new dependency can enter another module's graph through a shared workspace directive, and the failure surfaces only when that module is built.

## [dw-003] Re-verify the build toolchain after an environment replacement

- Trigger: Building or packaging after the environment has been replaced.
- Pattern: Starting the build assuming the toolchain survived, because the workspace files look unchanged.
- Do instead: Re-verify the build toolchain and required dev packages exist before starting the build/packaging steps; reinstall first if they are gone.
- Why: An environment replacement wipes installed system packages as well as running processes, so the failure appears mid-ship instead of at setup.
