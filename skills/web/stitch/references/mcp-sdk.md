# Stitch SDK Runner Reference

This reference focuses on the executable runner bundled with the skill and the official `@google/stitch-sdk` surface it wraps. Tracks the v0.3.5 release of the SDK (and the `next` channel where called out). The documented class surface (`Stitch`, `Project`, `Screen`, `DesignSystem`, `StitchToolClient`, `StitchProxy`) has been stable since v0.1.1 through v0.3.5 — the version bumps in between were maintenance releases, not API changes.

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
- `list-design-systems`
- `create-design-system`
- `update-design-system`
- `apply-design-system`
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

- `--variant-count` (1–5)
- `--creative-range`
- `--aspects`

The runner maps these to the official SDK shape:

```ts
screen.variants(prompt, {
  variantCount,
  creativeRange,
  aspects,
});
```

## Design system options

- `--design-system-file`: JSON file describing the design system payload
- `--asset-id`: ID of an existing design system on the project
- `--selections-file`: JSON file with `[{ id, sourceScreen }]` selected screen instances

## Official SDK methods behind the runner

Top-level (`stitch` singleton, `Stitch` class):

- `stitch.projects()` → `Promise<Project[]>`
- `stitch.project(id)` → `Project` (no API call)
- `stitch.listTools()` → `Promise<{ tools }>`
- `stitch.callTool<T>(name, args)` → `Promise<T>`

Project:

- `project.generate(prompt, deviceType?)` → `Promise<Screen>`
- `project.screens()` → `Promise<Screen[]>`
- `project.getScreen(screenId)` → `Promise<Screen>`
- `project.createDesignSystem(designSystem)` → `Promise<DesignSystem>`
- `project.listDesignSystems()` → `Promise<DesignSystem[]>`
- `project.designSystem(id)` → `DesignSystem` (no API call)

Screen:

- `screen.edit(prompt, deviceType?, modelId?)` → `Promise<Screen>`
- `screen.variants(prompt, variantOptions, deviceType?, modelId?)` → `Promise<Screen[]>`
- `screen.getHtml()` → `Promise<string>` (download URL)
- `screen.getImage()` → `Promise<string>` (download URL)

DesignSystem:

- `designSystem.update(designSystem)` → `Promise<DesignSystem>`
- `designSystem.apply(selectedScreenInstances)` → `Promise<Screen[]>`

`selectedScreenInstances` is `Array<{ id: string, sourceScreen: string }>`. Source the entries from `project.data.screenInstances`.

### Project creation

The README documents project creation through the tool client:

```ts
const result = await stitch.callTool("create_project", { title: "My App" });
```

Older releases also exposed `stitch.createProject(title)`; the runner's `create-project` command uses whichever path the installed SDK supports.

## Offline tool introspection

`toolMap` and `toolDefinitions` (static exports, also on `stitch.toolMap`) list every tool's pre-parsed parameters without a network call or API key:

```ts
import { stitch } from "@google/stitch-sdk";

const tool = stitch.toolMap.get("generate_screen_from_text");
const required = tool.params.filter(p => p.required).map(p => p.name);
```

Reach for this instead of a live `list-tools` call when the user wants to inspect available tools/parameters and no `STITCH_API_KEY` is configured yet.

## Enums

- `DeviceType`: `MOBILE` | `DESKTOP` | `TABLET` | `AGNOSTIC`
- `modelId`: `GEMINI_3_PRO` | `GEMINI_3_FLASH`
- `creativeRange`: `REFINE` | `EXPLORE` | `REIMAGINE`
- `aspects` (variants): `LAYOUT`, `COLOR_SCHEME`, `IMAGES`, `TEXT_FONT`, `TEXT_CONTENT`

## Auth modes

API key:

- simplest for local use
- uses `STITCH_API_KEY` or `auth.apiKey`

OAuth:

- uses `STITCH_ACCESS_TOKEN` plus `GOOGLE_CLOUD_PROJECT`
- the SDK requires both together when no API key is provided
- useful when long-lived API keys should not be stored

Endpoint override:

- `STITCH_HOST` or `auth.baseUrl` overrides the default `https://stitch.googleapis.com/mcp`

## Error handling

Domain class methods throw `StitchError` on failure. Inspect the typed code before retrying:

```ts
import { stitch, StitchError } from "@google/stitch-sdk";

try {
  await stitch.project("bad-id").screens();
} catch (error) {
  if (error instanceof StitchError) {
    console.error(error.code);        // see codes below
    console.error(error.message);
    console.error(error.recoverable);
  }
}
```

Codes: `AUTH_FAILED`, `NOT_FOUND`, `PERMISSION_DENIED`, `RATE_LIMITED`, `NETWORK_ERROR`, `VALIDATION_ERROR`, `UNKNOWN_ERROR`.

## Agent and tool integrations

Vercel AI SDK (`@google/stitch-sdk/ai`):

```ts
import { generateText, stepCountIs } from "ai";
import { google } from "@ai-sdk/google";
import { stitchTools } from "@google/stitch-sdk/ai";

const { text, steps } = await generateText({
  model: google("gemini-2.5-flash"),
  tools: stitchTools(),                 // optional: { apiKey, include }
  prompt: "Create a project and generate a dashboard",
  stopWhen: stepCountIs(5),
});
```

Google Agent Development Kit (`@google/stitch-sdk/adk`):

```ts
import { stitchAdkTools } from "@google/stitch-sdk/adk";
import { LlmAgent } from "@google/adk";

const tools = stitchAdkTools();         // optional: { include }

const designer = new LlmAgent({
  name: "Designer",
  model: "gemini-2.5-pro",
  instruction: "You are a designer. Create a project and generate a screen.",
  tools,
});
```

Both helpers accept `{ include: string[] }` to filter to specific tool names.

## Low-level tools

Use `list-tools` and `call-tool` when the user wants raw Stitch MCP tool access through the SDK client rather than the domain classes.

Typical raw tool names:

- `create_project`
- `list_projects`
- `list_screens`
- `get_screen`
- `generate_screen_from_text`
- `edit_screens`
- `generate_variants`
- design-system tools surfaced by v0.1.1 (`list_tools` to discover their exact names in the running SDK)

`StitchToolClient` and `StitchProxy` provide explicit configuration:

```ts
import { StitchToolClient, StitchProxy } from "@google/stitch-sdk";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const client = new StitchToolClient({
  apiKey: "...",
  baseUrl: "https://stitch.googleapis.com/mcp",
  timeout: 300_000,
});

const proxy = new StitchProxy({ apiKey: "..." });
await proxy.start(new StdioServerTransport());
```

## Config persistence

- `save-config` writes the resolved config immediately.
- `--save-config` can be added to `show-config`, `generate`, `edit`, design-system, and other commands to persist after a successful run.
- By default, persistence writes to the loaded config file. If none was loaded, it writes to `<cwd>/.stitch.json`.
