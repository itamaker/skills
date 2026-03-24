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
skills/stitch/scripts/run.sh save-config --project-id 123 --device-type DESKTOP
```

Or add `--save-config` to another command to save after that command succeeds.

## Create a starter config

Copy the example file:

```bash
cp skills/stitch/assets/stitch.example.json ./.stitch.json
```

Or use the bundled helper:

```bash
skills/stitch/scripts/run.sh init-config --output ./.stitch.json
```

To update an existing config in place:

```bash
skills/stitch/scripts/run.sh save-config --config ./.stitch.json --api-key "$STITCH_API_KEY"
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
    "modelId": "GEMINI_3_PRO",
    "variantCount": 3,
    "creativeRange": "EXPLORE",
    "variantAspects": ["LAYOUT", "COLOR_SCHEME"]
  },
  "runtime": {
    "dir": "~/.cache/itamaker-skills/stitch-sdk",
    "sdkPackage": "@google/stitch-sdk@0.0.3"
  }
}
```

## Precedence rules

- CLI flags override environment variables.
- Environment variables override config values.
- Config values override built-in defaults.
- `save-config` and `--save-config` write the fully resolved result back to the target file.

## Auth fields

- `auth.apiKey`: direct API key. Equivalent to `STITCH_API_KEY`.
- `auth.accessToken`: OAuth access token. Equivalent to `STITCH_ACCESS_TOKEN`.
- `auth.googleCloudProject`: required with OAuth. Equivalent to `GOOGLE_CLOUD_PROJECT`.
- `auth.baseUrl`: optional Stitch MCP endpoint override.
- `auth.timeoutMs`: request timeout in milliseconds.

## Default generation fields

- `defaults.projectId`: project to use when the command does not pass `--project-id`.
- `defaults.deviceType`: one of `MOBILE`, `DESKTOP`, `TABLET`, `AGNOSTIC`.
- `defaults.modelId`: one of `GEMINI_3_PRO`, `GEMINI_3_FLASH`.
- `defaults.variantCount`: default number of variants.
- `defaults.creativeRange`: one of `REFINE`, `EXPLORE`, `REIMAGINE`.
- `defaults.variantAspects`: list of variant aspects such as `LAYOUT`, `COLOR_SCHEME`, `IMAGES`, `TEXT_FONT`, `TEXT_CONTENT`.

## Runtime fields

- `runtime.dir`: where the runner installs `@google/stitch-sdk`.
- `runtime.sdkPackage`: package spec to install on bootstrap. Defaults to `@google/stitch-sdk@0.0.3`.

## Operational advice

- Prefer env vars for secrets if the config file may be shared.
- Keep config files out of version control when they contain secrets.
- Use `show-config` to inspect the resolved configuration. Secrets are redacted by default.
- If you intentionally want local persistence, `save-config` writes secrets too; treat `.stitch.json` as sensitive.
