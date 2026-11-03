# Staffing and cost

| Role | Activate when | Default |
| --- | --- | --- |
| Main conversation / CoS | Goal, dispatch, integration, acceptance, delivery | Always one dispatcher |
| Implementation worker | Bounded work saves time through parallelism or isolation | On demand; small tasks stay with CoS |
| PM | Independent workstream needs sustained dependencies and acceptance tracking | Omit for simple tasks |
| Architecture advisor | Consequential cross-module tradeoff, migration, unresolved design failure | Focused consultation |
| Code advisor | Nontrivial execution path or consequential review | After relevant evidence exists |
| Visual advisor | UI direction/rendered result needs independent judgment | Paired with Impeccable when relevant |
| CI / platform specialist | Pipeline, runner, caching, permissions, or persistent flaky infrastructure failure | Temporary task for an existing worker; no standing CI role |
| QA / security / performance / release / domain specialist | High-risk acceptance or expertise missing from current evidence | Temporary bounded assignment |

No additional permanent roles are required by default. CI is deterministic automation; a named human or CoS owns failures and the change author fixes code regressions. Create a dedicated platform role only after repeated pipeline maintenance consumes enough time to justify it. An independent verification assignment can use an existing role and does not require a permanent QA layer.

Optimize total time and tokens together: coarse enough milestones to amortize handoffs, enough parallelism for independent ready work, and fewer concurrent agents when tests or reviews are the bottleneck. Use [model selection](models.md) to choose economy, balanced, or deep settings for each task instead of fixing every role to high effort. Preserve user-specified models, budgets, and runtime limits.

Keep always-loaded instructions short. Send minimum relevant context, read only your role's reference, and return revision plus evidence rather than a conversation replay. Prefer tool scripts for deterministic checks and CI over model-driven repeated test runs. Summarize at transitions/blockers; do not poll unchanged CI logs continuously or spawn agents just to monitor jobs.
