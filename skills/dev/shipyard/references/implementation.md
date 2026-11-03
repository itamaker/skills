# Implementation worker

Reconcile the ticket, ownership, branch/worktree, and PR with your coordinator. Inspect applicable repository instructions and relevant source. Preserve other work; return ownership or interface conflicts before overlapping edits. Use the dedicated ticket worktree and stay within one assigned milestone.

For user-facing UI work, load the installed Impeccable skill in your own session before implementation and perform the applicable rendered verification. A coordinator's earlier invocation does not load it for you.

## Select tests by behavior

Map the change to its behavior, touched modules, immediate consumers, and failure paths. Run the smallest meaningful selection: regression tests for the changed behavior, relevant package/integration tests, and required static checks. Include consumers when a shared contract changes. Use file/test-name/package filters supported by the repository; do not infer relevance solely from edited filenames.

Report the selection and why it covers this ticket. When there are no appropriate tests, verify the observable outcome and say what remains unverified. Do not add tests that merely repeat configuration text or assert implementation details.

Do not run a repository-wide test suite as the worker's default, after every edit, or again merely because a check passed. Full regression belongs to CI/integration. If a repository instruction mandates a full check or the runner cannot filter it, report that requirement to the coordinator; keep the ticket's required evidence open until the coordinator assigns CI or one explicit integration fallback. Never silently waive a mandatory check. Re-run only checks invalidated by a later change, failure, or unresolved risk.

## Handoff

Resolve failures in scope; route unrelated baseline failures or needed scope changes to the coordinator with concise evidence. Return owned files, behavior delivered, commit/PR, selected commands and results, unverified criteria, and integration notes. Keep raw logs out of the handoff unless their contents explain the failure.

Before remote delivery, read [delivery.md](delivery.md). Publish a verified Draft PR/checkpoint only when authorized and applicable review is complete. Do not merge on the strength of local tests alone. Continue only the next coordinator-assigned, already approved milestone. Preserve work before interruption; do not launch new PMs/workers. Coordinate helpers required by an invoked skill within runtime capacity.
