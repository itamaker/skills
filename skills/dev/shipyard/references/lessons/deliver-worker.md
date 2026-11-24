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
  - id: dw-004
    added: 2026-11-23
    status: active
  - id: dw-005
    added: 2026-11-24
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

## [dw-004] Verify a shared resource is free before judging the product

- Trigger: A step needs a shared resource (a display, a port).
- Pattern: Running the step and reading its failure as a product defect.
- Do instead: Verify the resource is free first — check for a stale holder — and free it or pick another before judging the product.
- Why: Shared resources outlive the processes that used them.

## [dw-005] Verify a synced copy with diff before trusting it

- Trigger: Syncing an installed or deployed copy from a source tree.
- Pattern: Using a destructive sync (delete mode) with a filter set, and assuming the result matches the source.
- Do instead: Copy from the source without delete mode, or first prove the filter set with a dry run; then diff the target against the source and confirm zero unexpected differences before running anything from it.
- Why: A sync that deletes is indistinguishable from a successful sync until something reads the missing file, and by then the damage looks like a defect in the target.
