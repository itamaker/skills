# Configure through Shipyard

Claude Code's `/shipyard ...` and Codex's `$shipyard ...` invoke this skill with a natural-language request. These are skill-interpreted intents, not a new native slash-command parser. Follow this map before dispatching or saving settings:

| User intent | Action and lifetime |
| --- | --- |
| "Use deep for this task" | Keep a task override in the coordinator's task record; pass it to plans for new matching agents until task completion/cancellation. No settings file writes. |
| "Next worker: model=sonnet, effort=high" | Reserve a one-shot override for the next matching worker/ticket. Consume only after successful agent creation returns its ID. |
| "Save economy for this project's workers" | Preview then apply `set --scope project --role implementation_worker --tier economy` for the active client and authorized project. |
| "Save medium effort as my personal default" | Preview then apply `set --scope user --effort medium` for the active client. |
| "Show active settings" | Run read-only `status`; show source layers, resolved requested preferences, policy path, and runtime constraints. Do not consume pending task overrides. |
| "Restore auto for this task" | Replace task overrides with `tier=auto`, clearing inherited model/effort pins for that task. No native installation. |
| "Reset the project's worker defaults" | Preview then apply `reset --scope project --role implementation_worker`; reveal any remaining personal/default layer, which might still pin a model. |

Infer the client from the active host. Without an explicit save intent, keep adjustments task-scoped. Ask for scope only when the request genuinely leaves persistence ambiguous. An explicit save request authorizes the helper's scoped `--apply`; do not demand another confirmation for an already authorized save. When changing both clients, validate both previews before applying and report any partial outcome.

## Task and one-shot ownership

The single dispatcher records override values, client/role filter, target ticket, lifetime, and pending/consumed state. For a parallel batch, assign a one-shot override to one specific ticket before dispatch. Planning, status, creation of a different role, and failures before agent creation do not consume it. After creation returns an agent ID, record consumption and the ID before another dispatch. Pending state survives interruption only through the existing task record; this skill does not create a background session-state service. Existing agents and the primary session remain unchanged.

For a matching dispatch, precedence is saved settings → task-wide override → next-worker override. Normalize each override layer separately before combining it: a model-only next-worker request clears the older task tier/effort instead of producing conflicting flags. Retain the strictest ceiling across every layer. Pass the resulting request fields to the planner; do not concatenate superseded task pins with the one-shot request.

Pass task overrides through the [planner's explicit fields](models.md). Never interpret a requested model as an effective model without host-reported evidence. If native pins, host schema, or environment constraints block the choice, keep a pending one-shot override unconsumed and report the constraint instead of spawning an incorrectly configured worker.

## Persistent settings

Use `scripts/model_settings.py` with `status`, `set`, or `reset`. All examples below assume the active client is Claude; substitute `--client codex` on Codex. Resolve `/path/to/shipyard` from the loaded skill.

```bash
# Preview; add --apply for an explicitly requested save.
python3 /path/to/shipyard/scripts/model_settings.py set --client claude --scope project --project /authorized/repo --role implementation_worker --tier economy
python3 /path/to/shipyard/scripts/model_settings.py set --client claude --scope user --effort medium

# Show the current worker's requested defaults and their sources.
python3 /path/to/shipyard/scripts/model_settings.py status --client claude --project /authorized/repo --role implementation_worker

# Remove only this project's worker overrides, revealing lower layers.
python3 /path/to/shipyard/scripts/model_settings.py reset --client claude --scope project --project /authorized/repo --role implementation_worker
```

Personal settings live at `$XDG_CONFIG_HOME/shipyard/model-settings.json`, or `~/.config/shipyard/model-settings.json`. Project settings live at the Git root's `.shipyard/model-settings.json`; a non-Git project requires an explicit `--project`. `--user-config` selects an alternate personal file for controlled environments/tests.

Only read a project's settings after the host trusts that workspace or the user's task authorizes it. Pass `--project /authorized/repo` to assert that established context, or `--trust-project` for an already trusted discovered Git root. Otherwise project settings are ignored with a diagnostic; `--no-project-settings` explicitly ignores them while keeping personal defaults. No repeated approval is needed for an already authorized workspace.

Precedence is bundled policy → personal defaults → personal role → project defaults → project role → current request. Current-request fields supplied to the planner override saved preferences. Setting a tier masks lower model/effort pins; setting a model without effort uses that model's declared default effort. A `null` masks a lower value, while a missing field inherits. `reset --field ...` removes only the selected scope's field; resetting an entry never clears another client or role. Reset is distinct from deliberately setting `tier=auto`.

Every participating `max_tier` is a planning ceiling: the strictest one wins. A task override, a higher layer, or a `null` cannot relax a lower ceiling. To raise it, explicitly change/reset the scope defining it. This is not a billing limiter and does not reconfigure a primary session or native installation.

The helper validates settings and selected policy, previews without writes, and uses a lock, backup, and atomic replacement for an explicit save. It touches only its selected settings file and associated lock/backups, not client global/native configuration. Malformed settings or missing/invalid selected policies fail visibly rather than silently reverting to bundled defaults.

## Saved custom policies and reload

To change tier mappings or add a model, create a validated custom policy based on `assets/model-policy.json`, then save its path at the client-default scope:

```bash
python3 /path/to/shipyard/scripts/model_settings.py set --client claude --scope project --project /authorized/repo --policy /authorized/repo/shipyard-models.json
```

Saved relative policy paths resolve against the settings file that owns them, independent of the next invocation's working directory. Policy paths are client defaults, not role-specific fields. The planner reloads personal/project settings and the chosen policy on fresh calls; a direct `--policy` is a one-request override. Reuse a resolved result only while task facts and settings/policy files are unchanged.

Project files are declarative JSON, not executable hooks. Preserve all native role/tool boundaries. If resetting preferences exposes an old native model/effort pin, explain the separate explicit `install_clients.py --tier inherit` migration; do not run it as a side effect of a settings command.
