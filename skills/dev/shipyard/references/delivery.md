# Delivery and merged branches

## Publish and merge

Inspect the exact diff/staged files for credentials, private data, and unrelated changes. Use an available privacy-preserving commit identity without changing global Git identity. Push only the assigned branch without force and create/update its Draft PR when remote delivery is authorized, selected checks pass, and applicable review is complete. Include requirement, changed behavior, revision-specific checks, and remaining work. A Draft PR is a checkpoint, not acceptance.

Merge only within the user's authorization after coordinator acceptance and the repository's required CI/reviews pass for the candidate. New commits invalidate checks they affect. Permission to implement/open a PR does not itself authorize merge or deployment.

## Automatic post-merge cleanup

The coordinator owns cleanup as the final step of each authorized merge. Stop/release the ticket's workers, reconcile other client sessions and the task record, and move off the task branch. If a dedicated worktree is no longer needed, remove it only after confirming it is clean (including untracked files) and no session owns it; otherwise keep it and defer cleanup. Never remove or detach a live worktree just to make cleanup pass.

From the matching repository, run the bundled helper after all claims are released:

```bash
python3 /path/to/shipyard/scripts/cleanup_merged.py --repo owner/repo --pr 123 --released --apply
```

Resolve `/path/to/shipyard` from the loaded skill's directory. Omit `--apply` for a read-only preview. The script needs Python 3, Git, authenticated `gh`, and access to the matching Git remote. `--released` is a coordinator assertion of exclusive release; the script cannot discover live model sessions or provide a distributed lock. Keep dispatch paused for that branch until cleanup finishes and serialize other clients' Git checkout/ref edits with this operation. Worktree rechecks narrow race windows but do not lock out unrelated Git processes.

The helper binds API proof to `github.com`, verifies same-repository merged PR provenance, protects the default/base and common long-lived branch names, checks configured protection for a live remote branch, rejects symbolic local heads, skips every checked-out worktree, and requires existing local/remote heads to equal the merged PR's exact head. Squash/rebase merges are supported through this PR evidence rather than ancestry alone. Remote deletion uses a SHA lease; local deletion compares the expected SHA without dereferencing symbolic refs. It never sweeps unrelated branches or removes worktrees. Retain branches needed by a dependent ticket or configured as long-lived/protected even if merged; check these in the task record and repository rules before invoking it.

An absent branch is already clean. An advanced branch, active worktree, unknown provenance, unavailable authentication, or failed guard remains `cleanup-pending` with its reason; do not retry destructively or roll back the merge. Retry once the recorded reason is resolved. Record merge SHA, deleted refs, retained refs, and reason in the task record. This is an agent-executed merge step, not a daemon or a Git hook; a merge done outside the agent needs a follow-up cleanup invocation.
