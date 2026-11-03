# Verification stages

| Stage | Scope and owner | Completion evidence |
| --- | --- | --- |
| Worker loop | Changed behavior, affected dependencies, necessary lint/type/build checks; worker | Exact commands, selection rationale, revision, results |
| Draft PR | Fast affected checks; CI | Artifacts and actionable failures for the current commit |
| Ready PR / merge candidate | Full correctness regression once per candidate; CI | Required checks pass for the exact candidate, including integration with current base |
| Post-merge | Smoke/integration health; CI, CoS monitors | Main remains healthy; investigate or revert through authorized process |
| Nightly / release | Expensive platform matrix, soak, load, broad compatibility; CI | Reports with an owner; release-critical results gate release |

Full correctness regression belongs **before merge**, not solely after merge or overnight. A ready PR runs it; a new head invalidates previous head evidence. A merge queue may produce a different integration candidate that must pass its checks too. If a change can be isolated rigorously, CI may select affected packages, but selection must include downstream contracts; uncertain impact triggers broader CI coverage.

For GitHub Actions, a typical split is a fast workflow on Draft updates, and full regression on non-Draft `pull_request` events (`opened`, `synchronize`, `reopened`, `ready_for_review`) plus `merge_group` when the repository uses a merge queue. A candidate already verified by an equivalent job need not be repeated without a new revision/environment reason. Shard/cache expensive jobs, cancel superseded runs for the same PR, and keep deterministic health checks distinct from flaky/soak jobs. Never use path filters that silently omit a required correctness gate.

Repository-required checks override this default placement; the coordinator records how they will be satisfied rather than duplicating the full suite across workers. Configure branch protection/rulesets when authorized so required checks gate merging; a workflow file alone does not enforce this. A skipped, missing, cancelled, stale, or failed required run is not a pass. Document baseline failures and retain open acceptance; do not label unexecuted checks successful.

Without CI, CoS assigns **one integration verification task** for the combined candidate to `verify-worker` or performs it directly. Record the exact revision/environment and full-suite result; implementation workers still run only related checks. Use `ci-worker` for actual pipeline/runner/environment failures, not as a watcher of healthy deterministic jobs. Establish CI when repeated integration verification becomes the bottleneck.

The PM/CoS owns acceptance; CI proves automated checks, not all product requirements. Use independent functional verification for high-risk user behavior. Reuse current check/review artifacts, summarize failures, and request specialist analysis only after bounded investigation cannot resolve the problem.
