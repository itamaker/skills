# Stitch Skill Config

The bundled runner can read configuration from a JSON file so the caller does not need to repeat auth and default generation parameters on every invocation.

## Lookup order

The runner resolves config in this order:

1. `--config /abs/path/to/file.json`
2. `STITCH_SKILL_CONFIG=/abs/path/to/file.json`
3. `<cwd>/.stitch.json`
4. `<cwd>/stitch.json`

If no config file is found, the runner still works with CLI flags and environment variables alone.

To persist the resolved parameters back into a config file:

```bash
scripts/run.sh save-config --project-id 123 --device-type DESKTOP
```

Or add `--save-config` to another command to save after that command succeeds.

## Create a starter config

Copy the example file:

```bash
cp assets/stitch.example.json ./.stitch.json
```

Or use the bundled helper:

```bash
scripts/run.sh init-config --output ./.stitch.json
```

To update an existing config in place:

```bash
scripts/run.sh save-config --config ./.stitch.json --api-key "$STITCH_API_KEY"
```

## Schema

```json
{
  "auth": {
    "apiKey": "",
    "accessToken": "",
    "googleCloudProject": "",
    "baseUrl": "https://stitch.googleapis.com/mcp",
    "timeoutMs": 300000
  },
  "defaults": {
    "projectId": "",
    "deviceType": "DESKTOP",
    "modelId": "GEMINI_3_8_FLASH",
    "variantCount": 3,
    "creativeRange": "EXPLORE",
    "variantAspects": ["LAYOUT", "COLOR_SCHEME"]
  },
  "runtime": {
    "dir": "~/.cache/itamaker-skills/stitch-sdk",
    "sdkPackage": "@google/stitch-sdk@0.4.0"
  }
}
```

## Saving

- Precedence is CLI flag, environment variable, config value, built-in default.
- `save-config` and `--save-config` write the fully resolved result (secrets included) to the loaded config file, or to `<cwd>/.stitch.json` when none was loaded. `--save-config` works on `show-config` and the SDK-backed commands and saves after the command succeeds.
- A saved `runtime.sdkPackage` keeps its value: a config written under an earlier release still pins that release (for example `@google/stitch-sdk@0.3.5`) until you change it.

## Auth fields

- `auth.apiKey`: direct API key. Equivalent to `STITCH_API_KEY`.
- `auth.accessToken`: OAuth access token. Equivalent to `STITCH_ACCESS_TOKEN`.
- `auth.googleCloudProject`: required with OAuth. Equivalent to `GOOGLE_CLOUD_PROJECT`.
- `auth.baseUrl`: optional Stitch MCP endpoint override. Equivalent to `STITCH_BASE_URL` (or `STITCH_HOST`).
- `auth.timeoutMs`: request timeout in milliseconds.

## Default generation fields

- `defaults.projectId`: project to use when the command does not pass `--project-id`.
- `defaults.deviceType`: a device type (values: Enums in [mcp-sdk.md](mcp-sdk.md)).
- `defaults.modelId`: a model id (values: Enums in [mcp-sdk.md](mcp-sdk.md)). Defaults to `GEMINI_3_8_FLASH`, the newest id in the SDK 0.4.0 tool schema. A `modelId` already saved in a `.stitch.json` keeps its value (older `save-config` runs wrote `GEMINI_3_PRO`); `--model-id` overrides both. The runner passes the id through unchecked, and the SDK checks it only in TypeScript types, so the service decides what it accepts. SDK 0.3.5 types list only `GEMINI_3_PRO`, `GEMINI_3_FLASH` and `GEMINI_3_1_PRO` but also send any other id as is; whether the service accepts `GEMINI_3_8_FLASH` is not verified, so a user pinned to 0.3.5 who sees a model error sets `--model-id GEMINI_3_1_PRO` (or `defaults.modelId`) explicitly.
- `defaults.variantCount`: default number of variants.
- `defaults.creativeRange`: `REFINE`, `EXPLORE` or `REIMAGINE`.
- `defaults.variantAspects`: list of variant aspects (values: Enums in [mcp-sdk.md](mcp-sdk.md)).

## Runtime fields

- `runtime.dir`: cache root for SDK installs. Equivalent to `STITCH_SKILL_RUNTIME_DIR`. Each package spec installs into its own subfolder (for example `@google_stitch-sdk@0.4.0`), so pinning another version with a flag or a different project config never replaces the cache of the default. The install happens in a temporary folder that is renamed into place after npm succeeds, and a folder without the `.install-complete` marker is never used. `install-sdk --json` reports `runtimeDir`, `installDir` and `installedVersion`.
- `runtime.sdkPackage`: package spec to install on bootstrap. Defaults to `@google/stitch-sdk@0.4.0`. Equivalent to `STITCH_SKILL_SDK_PACKAGE`. Pin another version (for example `@google/stitch-sdk@0.3.5`, or `@google/stitch-sdk@next` to track previews) when the user asks. Exact versions are cached per version; a tag such as `@next` keeps its cached copy until `install-sdk --force-install` refreshes it (a failed refresh keeps the old copy and warns on stderr). A spec starting with `-` is rejected; npm runs with `--ignore-scripts`.

The config file chooses what npm installs (`runtime.sdkPackage`, `runtime.dir`), so a `.stitch.json` or `stitch.json` from an untrusted repository deserves the same care as an untrusted `package.json`.

## Secrets

Prefer env vars for secrets when the config file may be shared.
