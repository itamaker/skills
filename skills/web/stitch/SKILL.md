---
name: stitch
description: Google Stitch design generation through a bundled runner on @google/stitch-sdk, or handwritten SDK code. Use when generating, editing or varying Stitch screens, applying design systems, downloading HTML or images, or writing Stitch integration code.
---

# Stitch

`scripts/run.sh` is a runner over the official `@google/stitch-sdk` (pinned to 0.4.0). `scripts/run.sh --help` lists the commands and `scripts/run.sh <command> --help` its flags. [references/mcp-sdk.md](references/mcp-sdk.md) holds the shared options, enums, SDK object model, 0.3.x to 0.4.0 differences and error codes.

## Configure

Every setting resolves as CLI flag, then environment variable, then config file, then default.

- Config file: `--config`, else `STITCH_SKILL_CONFIG`, else `.stitch.json` or `stitch.json` in the working directory. Schema, saving and runtime fields: [references/config.md](references/config.md).
- Auth: `STITCH_API_KEY`, or OAuth with `STITCH_ACCESS_TOKEN` and `GOOGLE_CLOUD_PROJECT` together. `STITCH_BASE_URL` (alias `STITCH_HOST`) overrides the endpoint.
- Done when `scripts/run.sh list-projects --json` succeeds (`show-config` only proves a credential is set).
- The first SDK command installs the SDK into a per-version folder under `~/.cache/itamaker-skills/stitch-sdk`; `install-sdk` does it up front. If the network is blocked, tell the user or request approval. `--sdk-package @google/stitch-sdk@0.3.5` runs the previous release from its own folder and leaves other versions alone.

## Choose a path

- The runner covers operations: projects, screens, generate, edit, variants, design systems, downloads, raw tool calls (`list-tools`, `call-tool`).
- Handwritten SDK code covers a deliverable that is code, in a project with a Node or Bun runtime: a committed script, an app integration, `stitchTools()` for the Vercel AI SDK, `stitchAdkTools()` for Google ADK, or `StitchProxy` as your own MCP server. Snippets: [references/mcp-sdk.md](references/mcp-sdk.md).

## Generate, inspect, download

1. Pick a project: `scripts/run.sh create-project --title "My App" --json`, or `generate --create-project-title`. Pass `--save-config` to keep the project id as the default.
2. First pass: `scripts/run.sh generate --project-id ID --prompt-file ./prompt.txt --json`. Prompt guidance: [references/prompting.md](references/prompting.md). Done when the JSON carries `id`, `htmlUrl` and `imageUrl` (an empty URL means the screen has no such export). With no `--device-type` and no configured default, 0.4.0 generates `DESKTOP`. Further screens of one response land in `additionalScreens` with URLs only; `--html-out` and `--image-out` save the first screen.
3. Iterate with `edit --screen-id ID --prompt "..."` for focused revisions and `variants --screen-id ID --variant-count 3` for exploration. For one visual language across screens, run `create-design-system` then `apply-design-system` ([references/design-md.md](references/design-md.md)).
4. Export: `download-html` or `download-image` with `--screen-id ID --out ./path`; `generate` and `edit` also take `--html-out` and `--image-out`. Done when the file exists locally.

If Stitch asks a question instead of designing (exit 1, error code `CLARIFICATION_REQUIRED`; the question and suggested replies are in the error JSON on stderr), rerun with a prompt that answers it.

## Safety

- `STITCH_API_KEY`, `STITCH_ACCESS_TOKEN` and copied auth headers stay out of commits and replies; show `show-config` output, which redacts them, and reveal a secret only when the user asks to inspect it and understands the exposure.
- `save-config` and `--save-config` write the resolved secrets into the config file, so keep `.stitch.json` out of version control.
- Export URLs are transient: download what the user needs.
- When converting Stitch output into another framework, state whether the source is Stitch HTML or a Stitch image.
- In handwritten code, catch `StitchError` and branch on `error.code` before retrying.
