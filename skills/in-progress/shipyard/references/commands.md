# Flat stage parameters

Use the same parameters after Claude Code's `/shipyard` or Codex's `$shipyard`. Natural-language requests remain supported. A parameter input goes through `scripts/shipyard.py` for deterministic validation; unknown or conflicting flags are errors, not a request to guess another setting.

```text
/shipyard --implement sonnet:medium --code-review opus:high
/shipyard --verify sonnet:high --ci sonnet:medium --deliver haiku:low
```

Codex uses its configured model IDs:

```text
$shipyard --implement gpt-6.1-sol:medium --verify gpt-6.1-sol:high
```

Every value is `MODEL:EFFORT` or `auto`. The parser splits on the final colon so registered provider IDs containing colons are preserved. Models and efforts must be declared in the selected policy. `auto` masks inherited model/effort pins for that stage; it is not a literal model name.

There are six main workflow phases plus an optional CI-diagnostics branch: seven configuration stages and nine stage/agent targets. The single registry in `scripts/stage_registry.py` owns this mapping.

| Parameter | Stage | Agent |
| --- | --- | --- |
| `--plan` | `plan` | `project-manager` |
| `--architecture` | `design` | `architecture-advisor` |
| `--design-review` | `design` | `visual-advisor` |
| `--implement` | `implement` | `implementation-worker` |
| `--code-review` | `review` | `code-advisor` |
| `--visual-review` | `review` | `visual-advisor` |
| `--verify` | `verify` | `verify-worker` |
| `--ci` | `ci` | `ci-worker` |
| `--deliver` | `deliver` | `deliver-worker` |

Saving configuration does not enable every stage or create agents. CI tests and cleanup scripts remain deterministic automation. CI diagnostics and delegated delivery run only when needed. Independent verification requires a new verification invocation, not renaming an implementation thread. The running primary `chief-of-staff` is not changed by these flags.

## Save, inspect, and reset

Assignments explicitly save the selected stage/agent pairs in the current authorized project. Multiple assignments use one validated transaction, one backup, and one atomic replacement; an invalid entry prevents the whole batch from writing.

```text
/shipyard --implement sonnet:medium --preview
/shipyard --config
/shipyard --implement auto
/shipyard --reset implement
```

`--preview` validates without writing. `--config` is read-only and shows all nine targets with requested preferences and sources; automatic values are not presented as a fixed future model. `--reset implement,verify` removes those stage overrides; `--reset all` removes all nine registered targets at the selected scope. Generic defaults, generic role settings, other clients, and native client files remain unchanged. Reset can reveal a lower-layer pin; it is different from assigning `auto`.

Optional controls are separate from everyday assignments:

- `--user`: save/read personal defaults instead of project settings; project data is ignored.
- `--task`: return validated overrides for this task; do not write settings.
- `--next`: return one one-shot stage override; consume it only after a matching agent creation returns an ID.
- `--help`: display the full parameter list without loading settings.

`--user`, `--task`, and `--next` are mutually exclusive. A next-agent assignment accepts one target; a task assignment can configure several targets. Task/next results are coordinator-owned intents, not a hidden session-state service. `--config` or `--reset` with these controls reads/clears the coordinator's matching pending entries and never consumes or persists them. See [configuration.md](configuration.md) for lifetime and normalization rules.

## Safe host bridge

The skill host supplies the active client and established authorized project. It must not interpolate raw skill arguments into a shell command or a dynamic skill `!` expression.

1. Put a JSON object into a temporary file using a structured Write/apply-patch tool: `arguments` is the literal tail after the skill name, `client` is `codex` or `claude`, and `project` is the established authorized root. Optional controlled fields are `user_config`, `trust_project`, and `no_project_settings`.
2. Run the fixed helper path with `--input-json`, redirecting stdin from that generated temporary path. No user argument text belongs in the shell command itself.
3. Interpret the result's mode. `delivery` continues the original workflow; `natural` follows the natural-language configuration/delivery path. `settings`/`config` report the helper result. `task_override_intent`/`next_override_intent` update only the coordinator task record when `record=true`; status intents query that record without consumption.

The JSON bridge rejects duplicate/unknown keys and embedded host-context flags. Tokenization uses `shlex` without shell evaluation. A direct backend call can use literal argv and private `--client`, `--project`, and `--user-config` options; these context options are not the daily skill interface. Outside Git, a project write needs an explicit authorized project path; it never falls back to a personal save.

These flags control future new agents' requested settings. A host's immutable role configuration, environment, model restrictions, or unavailable override fields can still prevent application. Preserve requested/effective separation and verify actual settings through host metadata as described in [models.md](models.md).
