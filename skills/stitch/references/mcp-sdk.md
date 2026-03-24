# Stitch SDK Runner Reference

This reference focuses on the executable runner bundled with the skill and the official `@google/stitch-sdk` surface it wraps.

## Bundled runner

Primary entrypoint:

```bash
skills/stitch/scripts/run.sh <command> [options]
```

Use it for operational Stitch requests instead of writing throwaway code.

## Commands

- `init-config`: write an example config file
- `show-config`: print the resolved config with secrets redacted
- `save-config`: persist resolved auth/default/runtime options into `.stitch.json` or another config path
- `install-sdk`: bootstrap `@google/stitch-sdk` into the runtime directory
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

## Common options

- `--config`
- `--api-key`
- `--access-token`
- `--google-cloud-project`
- `--base-url`
- `--timeout-ms`
- `--runtime-dir`
- `--sdk-package`
- `--json`
- `--save-config`

## Generation options

- `--project-id`
- `--create-project-title` for `generate` if no project exists yet
- `--prompt`
- `--prompt-file`
- `--device-type`
- `--model-id`
- `--html-out`
- `--image-out`

## Variant options

- `--variant-count`
- `--creative-range`
- `--aspects`

The runner maps these to the official SDK shape:

```ts
screen.variants(prompt, {
  variantCount,
  creativeRange,
  aspects
});
```

## Official SDK methods behind the runner

Top-level:

- `stitch.createProject(title?)`
- `stitch.projects()`
- `stitch.project(id)`
- `client.listTools()`
- `client.callTool(name, args)`

Project:

- `project.generate(prompt, deviceType?, modelId?)`
- `project.screens()`
- `project.getScreen(screenId)`

Screen:

- `screen.edit(prompt, deviceType?, modelId?)`
- `screen.variants(prompt, variantOptions, deviceType?, modelId?)`
- `screen.getHtml()`
- `screen.getImage()`

## Auth modes

API key:

- simplest for local use
- uses `STITCH_API_KEY` or `auth.apiKey`

OAuth:

- uses `STITCH_ACCESS_TOKEN` plus `GOOGLE_CLOUD_PROJECT`
- useful when long-lived API keys should not be stored

## Low-level tools

Use `list-tools` and `call-tool` when the user wants raw Stitch MCP tool access through the SDK client rather than the domain classes.

## Config persistence

- `save-config` writes the resolved config immediately.
- `--save-config` can be added to `show-config`, `generate`, `edit`, and other commands to persist after a successful run.
- By default, persistence writes to the loaded config file. If none was loaded, it writes to `<cwd>/.stitch.json`.

Typical raw tool names:

- `create_project`
- `list_projects`
- `list_screens`
- `get_screen`
- `generate_screen_from_text`
- `edit_screens`
- `generate_variants`
