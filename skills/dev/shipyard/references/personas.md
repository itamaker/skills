# Role personalities

A profile describes habits of reasoning and communication. Apply them within the assigned role, task scope and authorization. Use the person's documented working method in your own voice. The source links explain the design choice and need no network access during delivery.

## Select and customize

Use the usual skill prefix for the client. For example, in Codex:

```text
$shipyard --personas
$shipyard --persona chief-of-staff:andy-grove
$shipyard --persona-create morgan --name "Morgan" --traits "Name the dependency and one step we can verify today."
$shipyard --persona chief-of-staff:morgan
$shipyard --persona-show chief-of-staff
$shipyard --persona-reset chief-of-staff
```

The list shows available IDs and assignments. Creation adds a reusable personal profile. Selection assigns one profile to one role. Multiple roles may use the same profile. Show returns the selected file path. Edit that Markdown to refine the display name or traits while keeping its ID stable. Reset restores the role's bundled default and keeps the personal profile available.

Each bundled default lives in `references/personas/<role>.md`, with additional choices in `references/personas/alternatives/`. A profile starts with a Markdown heading containing its display name, then an `ID: ...` line. The rest describes its working style and may include a rationale and sources. For changes you want to keep across package upgrades, create and edit a personal profile.

## Apply the selected profile

The coordinator uses the existing [command bridge](commands.md#safe-host-bridge) with `--persona-show ROLE` at role entry or dispatch. Read the returned `profile.path` or use its `profile.content`. Include the role, profile ID and absolute path in the handoff so a read-only advisor can open it directly. A successful switch or reset for the current role takes effect when the conversation reads the resulting profile. For another role, apply it at the next invocation. To change a running worker on explicit request, send the resolved path as a follow-up. A preview only reports the proposed change.

Directly invoked roles with read-only tools can resolve a profile using file reads:

1. Use the path supplied by the coordinator when available.
2. Otherwise read `shipyard/persona-settings.json` under the user's configuration directory (`XDG_CONFIG_HOME` if set, otherwise `~/.config`). Use the ID at `roles[<role>]`. With no settings file or role entry, open the bundled `references/personas/<role>.md` relative to this skill.
3. Look up a selected ID in the same config directory at `shipyard/personas/<id>.md` or by its exact `ID: <id>` line in the bundled profile directories. Accept only a valid profile ID from the command's ID format. If the selected file is missing or its contents disagree with the selected ID, report the unresolved selection. When the host cannot expose the configured root, ask the coordinator for the resolved path or identify the bundled fallback being used.

Selections and custom profiles are shared by Claude Code and Codex for the same personal configuration directory. Profile selection never changes model settings or the tools available to a role.
