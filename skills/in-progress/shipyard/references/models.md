# Task-level model and effort selection

Choose settings for each **new subagent**. The primary session keeps the user's chosen client configuration. Model/effort cannot be hot-swapped merely by changing instructions or resuming a fixed agent.

`assets/model-policy.json` is the single source for economy/balanced/deep model pairs, supported efforts, and automatic role floors. These are configurable capability declarations and relative tiers, not live account availability, dollar metering, or a guarantee of cheapest pricing. Confirm access and the actual host schema before dispatch; update policy capabilities when changing models.

| Automatic task characteristics | Choice |
| --- | --- |
| Low-complexity, low-risk worker work | Economy, subject to role/capability floors |
| Ordinary implementation, coordination, or review | Balanced |
| High complexity/risk, architecture decisions | Deep |

Use the selector after classifying the ticket. For a read-only plan:

```bash
python3 /path/to/shipyard/scripts/model_policy.py --client codex --role implementation_worker --complexity low --risk low
```

Resolve the skill path from the loaded installation. Load policy once per dispatch batch and reuse the selector's result for unchanged task facts. The helper makes no model calls and does not dispatch agents or modify client files.

## Apply only supported settings

Inspect the actual dispatch tool's parameters and native role definition first. Use `--runtime spawn` only when both model and effort overrides are supported. Pass the returned **requested** pair in those actual fields, together with the unchanged role and bounded ticket; never claim a model changed because the prompt mentions it. Default `unknown` produces a plan only; `--runtime fixed` requires a next-session preset. Keep requested/effective values separate: effective remains unknown until the host reports it.

Codex custom-file model/effort takes precedence over spawn parameters, so the bundled normal role files omit both. A host with immutable configured-role settings still cannot honor per-task overrides; preserve its role boundaries and report that constraint. Do not switch to an unrestricted role to bypass it. [Codex precedence](https://learn.chatgpt.com/docs/agent-configuration/subagents)

On Claude, pass `--claude-version` from the observed client version when planning spawn overrides. Per-invocation effort requires v2.1.292+. Model calls accept aliases; full model IDs may require a native/session preset. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, any nonempty `CLAUDE_CODE_EFFORT_LEVEL`, and managed restrictions can prevent the requested choice. Effort environment values `auto`/`unset` also take precedence: they request the API default rather than the selected explicit effort. Resolve that environment constraint before dispatch or launching a preset. Inspect `/tasks` or host-reported metadata rather than treating the selector as proof of effective settings. [Claude model/effort rules](https://code.claude.com/docs/en/sub-agents#choose-a-model), [effort environment precedence](https://code.claude.com/docs/en/model-config#send-no-effort-level)

## Explicit overrides and bounded escalation

The user's `--tier economy|balanced|deep`, `--model`, or `--effort` overrides automatic recommendations. For a model-only override, choose that model's declared default effort instead of carrying an incompatible effort from the former model. Unsupported model/effort combinations fail clearly; register custom models and capabilities in a custom policy passed with `--policy`. A visual advisor requires declared image support.

`--max-tier` is a hard relative-tier ceiling, not a currency budget. Conflicts fail rather than silently reducing required capability or increasing cost. A manual choice below the automatic recommendation remains explicit and visible; acceptance requirements still apply.

After a concrete failure or unresolved uncertainty, the coordinator may request **one** automatic tier increase per milestone using `--escalate --evidence "specific reason" --escalation-count 0`. Record the returned count; a second increase is rejected. User model/effort/tier pins and hard caps prevent automatic escalation. Prefer a new subagent with a concise handoff when a changed choice cannot be applied to the existing agent.

Manual task example:

```bash
python3 /path/to/shipyard/scripts/model_policy.py --client claude --role code-advisor --tier deep --runtime spawn --claude-version 2.1.317
```

For a host without invocation overrides, use the [explicit next-session preset](clients.md) instead. Applying a preset writes backed-up native files and requires a new session; it is distinct from task-level automatic selection.
