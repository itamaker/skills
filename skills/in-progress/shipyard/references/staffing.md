# Staffing and cost

| Role | Activate when | Default |
| --- | --- | --- |
| Main conversation / CoS | Goal, dispatch, integration, acceptance, delivery | Always one dispatcher |
| Implementation worker | Bounded work saves time through parallelism or isolation | On demand; small tasks stay with CoS |
| PM | Independent workstream needs sustained dependencies and acceptance tracking | Omit for simple tasks |
| Architecture advisor | Consequential cross-module tradeoff, migration, unresolved design failure | Focused consultation |
| Code advisor | Nontrivial execution path or consequential review | After relevant evidence exists |
| Visual advisor | UI direction/rendered result needs independent judgment | Paired with Impeccable when relevant |
| Verify worker | Independent acceptance or explicitly assigned integration verification | New `verify-worker` invocation; implementation source stays read-only |
| CI worker | Pipeline, runner, caching, permissions, or persistent flaky infrastructure failure | Activate `ci-worker` only for a scoped fault |
| Deliver worker | Authorized delegated PR/publication/merge/cleanup checkpoint | Activate `deliver-worker` only for the approved operation |
| Security / performance / domain specialist | Expertise missing from current evidence | Temporary bounded assignment |

Nine native role definitions are available, but they are not nine resident agents. CI is deterministic automation; CoS owns failure disposition, the change author fixes application regressions, and `ci-worker` owns assigned infrastructure fixes. Independent acceptance uses `verify-worker` when needed, and `deliver-worker` does not gain merge/deploy authority merely by its role name. Avoid creating agents only to consume every configured stage.

Optimize total time and tokens together: coarse enough milestones to amortize handoffs, enough parallelism for independent ready work, and fewer concurrent agents when tests or reviews are the bottleneck. Use [model selection](models.md) to choose economy, balanced, or deep settings for each task instead of fixing every role to high effort. Preserve user-specified models, budgets, and runtime limits.

Keep always-loaded instructions short. Send minimum relevant context, read only your role's reference, and return revision plus evidence rather than a conversation replay. Prefer tool scripts for deterministic checks and CI over model-driven repeated test runs. Summarize at transitions/blockers; do not poll unchanged CI logs continuously or spawn agents just to monitor jobs.
