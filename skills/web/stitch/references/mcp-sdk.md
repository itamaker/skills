# Stitch SDK Runner Reference

The options, enums and SDK surface behind `scripts/run.sh`. Written against `@google/stitch-sdk` 0.4.0, the runner's default pin; [0.3.x to 0.4.0 differences](#03x-to-040-differences) lists what changed. `scripts/run.sh --help` lists the commands and `scripts/run.sh <command> --help` the flags of each.

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
- `--prompt-file` (`-` reads stdin)
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
- `stitch.createProject(title | { title })` → `Promise<Project>` (the `{ title }` form is 0.4.0 only)
- `stitch.listTools()` → `Promise<{ tools }>`
- `stitch.callTool<T>(name, args)` → `Promise<T>`

Project:

- `project.generate(prompt, deviceTypeOrOptions?, modelId?)` → `Promise<Generation<Screen>>`
- `project.screens()` → `Promise<Screen[]>`
- `project.getScreen(screenId)` → `Promise<Screen>`
- `project.screen(id)` → `Screen` (no API call)
- `project.createDesignSystem(designSystem)` → `Promise<DesignSystem>`
- `project.listDesignSystems()` → `Promise<DesignSystem[]>`
- `project.designSystem(id)` → `DesignSystem` (no API call)
- `project.uploadDesignMd(base64)` and `project.createDesignSystemFromDesignMd(selectedScreenInstance, deviceTypeOrOptions?)` (0.4.0)

Screen:

- `screen.edit(prompt, deviceTypeOrOptions?, modelId?)` → `Promise<Generation<Screen>>`
- `screen.variants(prompt, variantOptions, deviceTypeOrOptions?, modelId?)` → `Promise<Generation<Screen>>`
- `screen.getHtmlUrl()` / `screen.getImageUrl()` → `Promise<string>` (signed download URLs; `getHtml()` / `getImage()` are deprecated aliases)
- `screen.readHtml()` → `Promise<string>` and `screen.readImage()` → `Promise<Uint8Array>` fetch the content itself (0.4.0)

DesignSystem:

- `designSystem.update(designSystem)` → `Promise<DesignSystem>`
- `designSystem.apply(selectedScreenInstances)` → `Promise<Generation<Screen>>`

`deviceTypeOrOptions` is a device type string or `{ deviceType, modelId }`. `selectedScreenInstances` is `Array<{ id: string, sourceScreen: string }>`, sourced from `project.data.screenInstances`.

`Generation` holds every screen of the response in `.screens` (also iterable) and the full tool response in `.raw`; `.first` is the first screen, and property access on the Generation falls through to `.first`, so code written for a single `Screen` keeps working. The runner prints the first screen and lists the rest under `additionalScreens`. When Stitch answers with a question instead of screens, the call throws `StitchError` with code `CLARIFICATION_REQUIRED` and `error.clarification` = `{ question, suggestions }`.

### Project creation

`stitch.createProject(title)` exists in 0.3.5 and 0.4.0 and is what the runner's `create-project` and `generate --create-project-title` call. `stitch.callTool("create_project", { title })` reaches the same tool.

## Offline tool introspection

`toolMap` and `toolDefinitions` list every tool's pre-parsed parameters without a network call or API key:

```ts
import { toolMap } from "@google/stitch-sdk/tools"; // 0.3.x: from "@google/stitch-sdk"

const tool = toolMap.get("generate_screen_from_text");
const required = tool.params.filter(p => p.required).map(p => p.name);
```

Reach for this instead of a live `list-tools` call when the user wants to inspect available tools/parameters and no `STITCH_API_KEY` is configured yet.

## Enums

- `DeviceType`: `MOBILE` | `DESKTOP` | `TABLET` | `AGNOSTIC`
- `modelId`: `GEMINI_3_8_FLASH` | `GEMINI_3_5_FLASH_LITE` | `GEMINI_3_PRO` | `GEMINI_3_FLASH` | `GEMINI_3_1_PRO` (the 0.4.0 type declarations; 0.3.5 declares `GEMINI_3_PRO`, `GEMINI_3_FLASH`, `GEMINI_3_1_PRO`). The runner uppercases the value and passes it through unchecked, so the service decides which ids it accepts.
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

- `STITCH_BASE_URL` (or `STITCH_HOST`, which SDK 0.4.0 deprecates) or `auth.baseUrl` overrides the default `https://stitch.googleapis.com/mcp`

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

Codes: `AUTH_FAILED`, `NOT_FOUND`, `PERMISSION_DENIED`, `RATE_LIMITED`, `NETWORK_ERROR`, `VALIDATION_ERROR`, `UNKNOWN_ERROR`; 0.4.0 adds `SERVICE_UNAVAILABLE`, `CLIENT_CLOSED`, `CLARIFICATION_REQUIRED`. The runner prints `code` (and `clarification`) next to `error` when present.

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
- `create_design_system`, `update_design_system`, `list_design_systems`, `apply_design_system`
- `get_project` (both versions); `delete_project`, `upload_design_md`, `create_design_system_from_design_md` (0.4.0 only)

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

## 0.3.x to 0.4.0 differences

Verified by diffing the published 0.3.5 and 0.4.0 packages and driving both against mocked tool responses; the service itself was not called.

- `project.generate`, `screen.edit`, `screen.variants` and `designSystem.apply` return a `Generation` (all screens, iterable, falls through to `.first`) instead of a `Screen` or `Screen[]`. Code that treats the result as a `Screen[]` (`.map`, `.length` on the array) needs `.screens`.
- `generate`, `edit` and `variants` accept `{ deviceType, modelId }` as the second argument; the positional `(deviceType, modelId)` form still works in both versions. `generate` sends `deviceType: "DESKTOP"` when none is given (0.3.5 sent nothing).
- `getHtmlUrl()` / `getImageUrl()` are the URL accessors; `getHtml()` / `getImage()` remain as deprecated aliases that return URLs. The 0.4.0 README describes `getHtml()` as returning content, but the shipped code returns the URL; use `readHtml()` for content.
- `Project`, `Screen` and `DesignSystem` constructors are `@deprecated`; use `stitch.project(id)`, `project.screen(id)`, `project.designSystem(id)`. `Project.data` is typed `ProjectData`.
- New: `readHtml()` / `readImage()`, `uploadDesignMd`, `createDesignSystemFromDesignMd`, tools `delete_project`, `upload_design_md`, `create_design_system_from_design_md`, the `@google/stitch-sdk/tools` entry, client options `retry` and `entityCache`, and `STITCH_BASE_URL` / `STITCH_PROJECT_ID` environment variables.
- `stitch.toolMap` no longer exists on the singleton; import `toolMap` instead.
- 0.4.0 declares `ai`, `@google/adk` and `@google/genai` as optional peer dependencies; importing `@google/stitch-sdk/ai` without `ai` throws, and `/adk` without `@google/adk` throws. The runner imports only the main entry.
- Removed exports: `buildFifeSuffix`, `StitchProxyConfigSchema`.
