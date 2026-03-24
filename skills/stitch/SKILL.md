---
name: stitch
description: Request Google Stitch through the bundled SDK runner or by writing @google/stitch-sdk code. Trigger when creating or listing Stitch projects, generating screens, editing screens, generating variants, downloading HTML or images, configuring STITCH_API_KEY or OAuth parameters, or converting Stitch output into React, Vue, or other app code.
---

# Stitch

Use this skill when the task needs to actually talk to the Stitch service. Prefer the bundled runner in `scripts/run.sh` over ad-hoc one-off code when the request is operational: listing projects, generating screens, editing, variants, or exports.

## Workflow

1. Resolve configuration first.
   - Use `--config /abs/path/to/file.json` when the user points to a config file.
   - Otherwise the runner checks `STITCH_SKILL_CONFIG`, then `.stitch.json`, then `stitch.json` in the current working directory.
   - Config schema and an example file live in `references/config.md` and `assets/stitch.example.json`.
   - Use `save-config` or `--save-config` when the user wants resolved parameters written back to `.stitch.json` or another target config path.

2. Resolve authentication.
   - Prefer `STITCH_API_KEY` for local scripted use.
   - OAuth is supported through `STITCH_ACCESS_TOKEN` plus `GOOGLE_CLOUD_PROJECT`.
   - CLI flags override env vars, and env vars override config-file values.

3. Choose the execution path.
   - Use the bundled runner for direct service operations:
     - `list-projects`
     - `create-project`
     - `list-screens`
     - `get-screen`
     - `generate`
     - `edit`
     - `variants`
     - `download-html`
     - `download-image`
     - `list-tools`
     - `call-tool`
     - `save-config`
   - Use handwritten TypeScript with `@google/stitch-sdk` only when the user wants checked-in code, automation inside an application, or a custom integration.

4. Bootstrap the SDK runtime through the wrapper.
   - Run `scripts/run.sh install-sdk` before first use, or let the first SDK-backed command auto-install the package.
   - The runner installs `@google/stitch-sdk` into a user cache directory by default, so it does not need to modify the repository.
   - Override the runtime location with `--runtime-dir` or `STITCH_SKILL_RUNTIME_DIR` if needed.

5. Execute the Stitch operation with the smallest sufficient command.
   - Use `create-project` and `generate` for first-pass concepts.
   - Use `edit` for focused revisions.
   - Use `variants` for exploration.
   - Use `download-html` or `download-image` when the user needs local artifacts instead of URLs.

## Runner Usage

Always prefer the wrapper:

```bash
skills/stitch/scripts/run.sh <command> [options]
```

Common options:

- `--config`: explicit config file
- `--api-key`
- `--access-token`
- `--google-cloud-project`
- `--base-url`
- `--timeout-ms`
- `--runtime-dir`
- `--json`
- `--save-config`

Prompt-bearing commands also support:

- `--prompt "..."` for short prompts
- `--prompt-file /abs/path/to/prompt.txt` for long prompts

Generation defaults can come from config, then be overridden per command:

- `--device-type MOBILE|DESKTOP|TABLET|AGNOSTIC`
- `--model-id GEMINI_3_PRO|GEMINI_3_FLASH`
- `--variant-count`
- `--creative-range REFINE|EXPLORE|REIMAGINE`
- `--aspects LAYOUT,COLOR_SCHEME,...`

## Command Patterns

- List projects:
- `scripts/run.sh list-projects --json`
- Save parameters into `.stitch.json`:
  - `scripts/run.sh save-config --api-key "$STITCH_API_KEY" --project-id 123 --device-type DESKTOP --json`
- Create a project:
  - `scripts/run.sh create-project --title "My App" --json`
- Generate a screen:
  - `scripts/run.sh generate --project-id 123 --prompt-file ./prompt.txt --device-type DESKTOP --model-id GEMINI_3_PRO --json`
  - Add `--save-config` to persist the resolved auth/default parameters after a successful run.
- Edit a screen:
  - `scripts/run.sh edit --project-id 123 --screen-id abc --prompt "Make the hero more compact" --json`
- Generate variants:
  - `scripts/run.sh variants --project-id 123 --screen-id abc --prompt "Explore cleaner layouts" --variant-count 3 --creative-range EXPLORE --aspects LAYOUT,COLOR_SCHEME --json`
- Download HTML:
  - `scripts/run.sh download-html --project-id 123 --screen-id abc --out ./tmp/screen.html`

## When To Write Code

Use direct `@google/stitch-sdk` code when:

- the user wants a committed script or service integration
- the project already has a Node or Bun runtime
- the request needs `stitchTools()` with the Vercel AI SDK
- the agent must integrate Stitch operations into a larger app workflow

When writing code, prefer the official object model:

- `stitch.createProject(title)`
- `stitch.projects()`
- `stitch.project(id)`
- `project.generate(prompt, deviceType?, modelId?)`
- `project.screens()`
- `project.getScreen(screenId)`
- `screen.edit(prompt, deviceType?, modelId?)`
- `screen.variants(prompt, variantOptions, deviceType?, modelId?)`
- `screen.getHtml()`
- `screen.getImage()`

## Safety Rules

- Never commit `STITCH_API_KEY`, `STITCH_ACCESS_TOKEN`, or copied auth headers.
- `save-config` and `--save-config` can write secrets into `.stitch.json`; keep that file out of version control when it contains credentials.
- Do not log secrets back to the user unless they explicitly ask to inspect the config and understand the exposure.
- Treat export URLs as transient download artifacts, not stable permanent URLs.
- When converting Stitch output into another framework, state clearly whether the source is Stitch HTML or a Stitch image.
- If first-run SDK installation needs network access and the environment blocks it, surface that blocker or request approval.

## Example Requests

- "Use $stitch to create a Stitch project and generate a landing page."
- "Use $stitch to list my Stitch projects."
- "Use $stitch to generate three variants for this screen and save the HTML for the best one."
- "Use $stitch to write a committed TypeScript helper around @google/stitch-sdk."
- "Use $stitch to download the image for this Stitch screen."

## Resources

- `scripts/run.sh`: stable entrypoint for the skill.
- `scripts/stitch.mjs`: SDK-backed Stitch runner with config support.
- `assets/stitch.example.json`: example config file.
- `references/config.md`: config lookup order and schema.
- `references/mcp-sdk.md`: SDK methods, auth fields, and low-level tool usage.
- `references/prompting.md`: prompt-writing guidance for generation and edits.
- `references/design-md.md`: DESIGN.md guidance when the user wants consistent multi-screen design systems.
