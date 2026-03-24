#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import fsp from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { parseArgs } from "node:util";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const skillDir = path.resolve(__dirname, "..");

const CONFIG_ENV_VAR = "STITCH_SKILL_CONFIG";
const DEFAULT_CONFIG_NAMES = [".stitch.json", "stitch.json"];
const DEFAULT_BASE_URL = "https://stitch.googleapis.com/mcp";
const DEFAULT_TIMEOUT_MS = 300000;
const DEFAULT_SDK_PACKAGE = "@google/stitch-sdk@0.0.3";
const DEFAULT_RUNTIME_DIR_TEMPLATE = "~/.cache/itamaker-skills/stitch-sdk";
const DEFAULT_RUNTIME_DIR = path.join(
  process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"),
  "itamaker-skills",
  "stitch-sdk",
);
const DEFAULT_CONFIG_TEMPLATE = {
  auth: {
    apiKey: "",
    accessToken: "",
    googleCloudProject: "",
    baseUrl: DEFAULT_BASE_URL,
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  defaults: {
    projectId: "",
    deviceType: "DESKTOP",
    modelId: "GEMINI_3_PRO",
    variantCount: 3,
    creativeRange: "EXPLORE",
    variantAspects: ["LAYOUT", "COLOR_SCHEME"],
  },
  runtime: {
    dir: DEFAULT_RUNTIME_DIR_TEMPLATE,
    sdkPackage: DEFAULT_SDK_PACKAGE,
  },
};

const HELP_TEXT = `Usage: stitch <command> [options]

Commands:
  init-config      Write an example config file
  show-config      Show the resolved config with secrets redacted
  save-config      Save resolved options into a config file
  install-sdk      Install @google/stitch-sdk into the runtime directory
  list-projects    List accessible Stitch projects
  create-project   Create a Stitch project
  list-screens     List screens in a project
  get-screen       Fetch a screen and optionally include export URLs
  generate         Generate a screen in a project
  edit             Edit an existing screen
  variants         Generate variants for a screen
  download-html    Download a screen's HTML artifact
  download-image   Download a screen's image artifact
  list-tools       List low-level Stitch tools exposed by the SDK client
  call-tool        Call a low-level Stitch tool by name

Use "stitch <command> --help" for command-specific options.
`;

function fail(message, exitCode = 1) {
  throw Object.assign(new Error(message), { exitCode });
}

function resolveUserPath(rawPath) {
  if (!rawPath) {
    return rawPath;
  }
  if (rawPath === "-") {
    return rawPath;
  }
  if (rawPath.startsWith("~/")) {
    return path.join(os.homedir(), rawPath.slice(2));
  }
  return path.resolve(rawPath);
}

function compactHomePath(rawPath) {
  if (!rawPath) {
    return rawPath;
  }
  const home = os.homedir();
  if (rawPath === home) {
    return "~";
  }
  if (rawPath.startsWith(`${home}${path.sep}`)) {
    return `~/${rawPath.slice(home.length + 1)}`;
  }
  return rawPath;
}

async function pathExists(targetPath) {
  try {
    await fsp.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

function coercePositiveInt(rawValue, label) {
  const value = Number.parseInt(String(rawValue), 10);
  if (!Number.isFinite(value) || value <= 0) {
    fail(`${label} must be a positive integer`);
  }
  return value;
}

function normalizeEnum(rawValue, label) {
  if (!rawValue) {
    return undefined;
  }
  return String(rawValue).trim().toUpperCase();
}

function parseAspects(rawValue) {
  if (!rawValue) {
    return undefined;
  }
  return String(rawValue)
    .split(",")
    .map(item => item.trim().toUpperCase())
    .filter(Boolean);
}

function baseOptions() {
  return {
    help: { type: "boolean", short: "h" },
    config: { type: "string" },
    json: { type: "boolean" },
    "save-config": { type: "boolean" },
    "api-key": { type: "string" },
    "access-token": { type: "string" },
    "google-cloud-project": { type: "string" },
    "base-url": { type: "string" },
    "timeout-ms": { type: "string" },
    "runtime-dir": { type: "string" },
    "sdk-package": { type: "string" },
    "force-install": { type: "boolean" },
  };
}

function parseCommandArgs(args, commandOptions = {}) {
  return parseArgs({
    args,
    allowPositionals: false,
    options: {
      ...baseOptions(),
      ...commandOptions,
    },
  }).values;
}

async function resolveConfigPath(explicitConfig, { allowMissing = false } = {}) {
  if (explicitConfig) {
    const candidate = resolveUserPath(explicitConfig);
    const exists = await pathExists(candidate);
    if (!exists && !allowMissing) {
      fail(`Config file not found: ${candidate}`);
    }
    return {
      path: candidate,
      exists,
    };
  }

  const envConfig = process.env[CONFIG_ENV_VAR];
  if (envConfig) {
    const candidate = resolveUserPath(envConfig);
    const exists = await pathExists(candidate);
    if (!exists && !allowMissing) {
      fail(`Config file from ${CONFIG_ENV_VAR} not found: ${candidate}`);
    }
    return {
      path: candidate,
      exists,
    };
  }

  for (const name of DEFAULT_CONFIG_NAMES) {
    const candidate = path.resolve(process.cwd(), name);
    if (await pathExists(candidate)) {
      return {
        path: candidate,
        exists: true,
      };
    }
  }

  return {
    path: null,
    exists: false,
  };
}

async function loadConfig(explicitConfig, { allowMissing = false } = {}) {
  const configSource = await resolveConfigPath(explicitConfig, { allowMissing });
  if (!configSource.path || !configSource.exists) {
    return {
      path: configSource.path,
      data: {},
    };
  }

  const raw = await fsp.readFile(configSource.path, "utf8");
  let data;
  try {
    data = JSON.parse(raw);
  } catch (error) {
    fail(`Invalid JSON in config file ${configSource.path}: ${error.message}`);
  }

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    fail(`Config file must contain a JSON object: ${configSource.path}`);
  }

  return {
    path: configSource.path,
    data,
  };
}

async function loadCommandConfig(values, { allowMissing = false } = {}) {
  return loadConfig(values.config, {
    allowMissing: Boolean(values["save-config"]) || allowMissing,
  });
}

function resolvedSettings(configData, cliValues) {
  const auth = configData.auth && typeof configData.auth === "object" ? configData.auth : {};
  const defaults =
    configData.defaults && typeof configData.defaults === "object" ? configData.defaults : {};
  const runtime =
    configData.runtime && typeof configData.runtime === "object" ? configData.runtime : {};

  return {
    auth: {
      apiKey:
        cliValues["api-key"] ||
        process.env.STITCH_API_KEY ||
        auth.apiKey ||
        undefined,
      accessToken:
        cliValues["access-token"] ||
        process.env.STITCH_ACCESS_TOKEN ||
        auth.accessToken ||
        undefined,
      googleCloudProject:
        cliValues["google-cloud-project"] ||
        process.env.GOOGLE_CLOUD_PROJECT ||
        auth.googleCloudProject ||
        undefined,
      baseUrl:
        cliValues["base-url"] ||
        process.env.STITCH_HOST ||
        auth.baseUrl ||
        DEFAULT_BASE_URL,
      timeoutMs: cliValues["timeout-ms"]
        ? coercePositiveInt(cliValues["timeout-ms"], "timeout-ms")
        : auth.timeoutMs
          ? coercePositiveInt(auth.timeoutMs, "auth.timeoutMs")
          : DEFAULT_TIMEOUT_MS,
    },
    defaults: {
      projectId: cliValues["project-id"] || defaults.projectId || undefined,
      deviceType:
        normalizeEnum(cliValues["device-type"], "deviceType") ||
        normalizeEnum(defaults.deviceType, "deviceType"),
      modelId:
        normalizeEnum(cliValues["model-id"], "modelId") ||
        normalizeEnum(defaults.modelId, "modelId"),
      variantCount: cliValues["variant-count"]
        ? coercePositiveInt(cliValues["variant-count"], "variant-count")
        : defaults.variantCount
          ? coercePositiveInt(defaults.variantCount, "defaults.variantCount")
          : 3,
      creativeRange:
        normalizeEnum(cliValues["creative-range"], "creativeRange") ||
        normalizeEnum(defaults.creativeRange, "creativeRange") ||
        "EXPLORE",
      variantAspects:
        parseAspects(cliValues.aspects) ||
        (Array.isArray(defaults.variantAspects)
          ? defaults.variantAspects.map(item => normalizeEnum(item))
          : undefined),
    },
    runtime: {
      dir: resolveUserPath(
        cliValues["runtime-dir"] ||
          process.env.STITCH_SKILL_RUNTIME_DIR ||
          runtime.dir ||
          DEFAULT_RUNTIME_DIR,
      ),
      sdkPackage:
        cliValues["sdk-package"] ||
        process.env.STITCH_SKILL_SDK_PACKAGE ||
        runtime.sdkPackage ||
        DEFAULT_SDK_PACKAGE,
    },
  };
}

function redactSecrets(settings, configPath) {
  return {
    configPath,
    auth: {
      apiKey: settings.auth.apiKey ? "<redacted>" : "",
      accessToken: settings.auth.accessToken ? "<redacted>" : "",
      googleCloudProject: settings.auth.googleCloudProject || "",
      baseUrl: settings.auth.baseUrl,
      timeoutMs: settings.auth.timeoutMs,
    },
    defaults: settings.defaults,
    runtime: settings.runtime,
  };
}

function buildPersistedConfig(baseData, settings) {
  const auth = baseData.auth && typeof baseData.auth === "object" ? baseData.auth : {};
  const defaults =
    baseData.defaults && typeof baseData.defaults === "object" ? baseData.defaults : {};
  const runtime =
    baseData.runtime && typeof baseData.runtime === "object" ? baseData.runtime : {};

  return {
    ...DEFAULT_CONFIG_TEMPLATE,
    ...baseData,
    auth: {
      ...DEFAULT_CONFIG_TEMPLATE.auth,
      ...auth,
      apiKey: settings.auth.apiKey || "",
      accessToken: settings.auth.accessToken || "",
      googleCloudProject: settings.auth.googleCloudProject || "",
      baseUrl: settings.auth.baseUrl || DEFAULT_BASE_URL,
      timeoutMs: settings.auth.timeoutMs ?? DEFAULT_TIMEOUT_MS,
    },
    defaults: {
      ...DEFAULT_CONFIG_TEMPLATE.defaults,
      ...defaults,
      projectId: settings.defaults.projectId || "",
      deviceType: settings.defaults.deviceType || DEFAULT_CONFIG_TEMPLATE.defaults.deviceType,
      modelId: settings.defaults.modelId || DEFAULT_CONFIG_TEMPLATE.defaults.modelId,
      variantCount:
        settings.defaults.variantCount ?? DEFAULT_CONFIG_TEMPLATE.defaults.variantCount,
      creativeRange:
        settings.defaults.creativeRange || DEFAULT_CONFIG_TEMPLATE.defaults.creativeRange,
      variantAspects:
        settings.defaults.variantAspects || DEFAULT_CONFIG_TEMPLATE.defaults.variantAspects,
    },
    runtime: {
      ...DEFAULT_CONFIG_TEMPLATE.runtime,
      ...runtime,
      dir: compactHomePath(settings.runtime.dir) || DEFAULT_CONFIG_TEMPLATE.runtime.dir,
      sdkPackage: settings.runtime.sdkPackage || DEFAULT_CONFIG_TEMPLATE.runtime.sdkPackage,
    },
  };
}

function configOutputPath(configPath) {
  return configPath || path.resolve(process.cwd(), ".stitch.json");
}

async function persistResolvedConfig(config, settings) {
  const targetPath = configOutputPath(config.path);
  const payload = buildPersistedConfig(config.data, settings);
  await writeJson(targetPath, payload, { force: true });
  return {
    outputPath: targetPath,
    payload,
  };
}

async function maybePersistResolvedConfig(values, config, settings) {
  if (!values["save-config"]) {
    return null;
  }
  return persistResolvedConfig(config, settings);
}

async function writeJson(filePath, data, { force = false } = {}) {
  const targetPath = resolveUserPath(filePath);
  if ((await pathExists(targetPath)) && !force) {
    fail(`File already exists: ${targetPath}. Re-run with --force to overwrite.`);
  }
  await fsp.mkdir(path.dirname(targetPath), { recursive: true });
  await fsp.writeFile(targetPath, JSON.stringify(data, null, 2) + "\n");
  return targetPath;
}

async function readPrompt(values) {
  if (values.prompt && values["prompt-file"]) {
    fail("Use either --prompt or --prompt-file, not both.");
  }
  if (values.prompt) {
    return values.prompt;
  }
  if (values["prompt-file"]) {
    const promptFile = values["prompt-file"];
    if (promptFile === "-") {
      return await new Promise((resolve, reject) => {
        let body = "";
        process.stdin.setEncoding("utf8");
        process.stdin.on("data", chunk => {
          body += chunk;
        });
        process.stdin.on("end", () => resolve(body));
        process.stdin.on("error", reject);
      });
    }
    return await fsp.readFile(resolveUserPath(promptFile), "utf8");
  }
  fail("Missing prompt. Pass --prompt or --prompt-file.");
}

async function ensureSdkInstalled(settings, { forceInstall = false } = {}) {
  const runtimeDir = settings.runtime.dir;
  const packageJsonPath = path.join(runtimeDir, "node_modules", "@google", "stitch-sdk", "package.json");
  if (!forceInstall && (await pathExists(packageJsonPath))) {
    return packageJsonPath;
  }

  await fsp.mkdir(runtimeDir, { recursive: true });
  const installArgs = [
    "install",
    "--prefix",
    runtimeDir,
    settings.runtime.sdkPackage,
    "--package-lock=false",
    "--no-save",
  ];
  const install = spawnSync("npm", installArgs, {
    stdio: "inherit",
  });
  if (install.status !== 0) {
    fail(`Failed to install ${settings.runtime.sdkPackage} into ${runtimeDir}`);
  }
  return packageJsonPath;
}

async function loadSdkModules(settings) {
  const packageJsonPath = await ensureSdkInstalled(settings);
  const packageDir = path.dirname(packageJsonPath);
  const packageJson = JSON.parse(await fsp.readFile(packageJsonPath, "utf8"));

  const mainEntry = path.join(packageDir, packageJson.exports["."].import);
  const aiEntry = packageJson.exports["./ai"]
    ? path.join(packageDir, packageJson.exports["./ai"].import)
    : null;

  const sdk = await import(pathToFileURL(mainEntry).href);
  const ai = aiEntry ? await import(pathToFileURL(aiEntry).href) : {};
  return {
    ...sdk,
    ...ai,
  };
}

function createClientConfig(settings) {
  if (settings.auth.apiKey) {
    return {
      apiKey: settings.auth.apiKey,
      baseUrl: settings.auth.baseUrl,
      timeout: settings.auth.timeoutMs,
    };
  }

  if (settings.auth.accessToken && settings.auth.googleCloudProject) {
    return {
      accessToken: settings.auth.accessToken,
      projectId: settings.auth.googleCloudProject,
      baseUrl: settings.auth.baseUrl,
      timeout: settings.auth.timeoutMs,
    };
  }

  fail(
    "Missing Stitch authentication. Provide STITCH_API_KEY or both STITCH_ACCESS_TOKEN and GOOGLE_CLOUD_PROJECT.",
  );
}

async function createSdk(settings) {
  const sdkModule = await loadSdkModules(settings);
  const client = new sdkModule.StitchToolClient(createClientConfig(settings));
  const sdk = new sdkModule.Stitch(client);
  return {
    module: sdkModule,
    client,
    sdk,
  };
}

function requireProjectId(values, settings) {
  return values["project-id"] || settings.defaults.projectId || fail("Missing --project-id.");
}

function normalizeProject(project) {
  const data = project.data ?? null;
  return {
    id: project.id,
    projectId: project.projectId,
    title: data?.title || data?.displayName || null,
    data,
  };
}

function normalizeScreen(screen, extras = {}) {
  const data = screen.data ?? null;
  return {
    id: screen.id,
    screenId: screen.screenId,
    projectId: screen.projectId,
    title: data?.title || data?.displayName || null,
    data,
    ...extras,
  };
}

function printOutput(data, jsonMode) {
  if (jsonMode) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  if (Array.isArray(data)) {
    for (const item of data) {
      console.log(JSON.stringify(item, null, 2));
    }
    return;
  }

  console.log(JSON.stringify(data, null, 2));
}

async function downloadUrlToFile(url, outputPath) {
  const resolvedOutput = resolveUserPath(outputPath);
  await fsp.mkdir(path.dirname(resolvedOutput), { recursive: true });
  const response = await fetch(url);
  if (!response.ok) {
    fail(`Failed to download ${url}: ${response.status} ${response.statusText}`);
  }
  const buffer = Buffer.from(await response.arrayBuffer());
  await fsp.writeFile(resolvedOutput, buffer);
  return resolvedOutput;
}

async function getScreenWithExports(project, screenId) {
  const screen = await project.getScreen(screenId);
  const [htmlUrl, imageUrl] = await Promise.all([screen.getHtml(), screen.getImage()]);
  return normalizeScreen(screen, { htmlUrl, imageUrl });
}

async function commandInitConfig(values) {
  const examplePath = path.join(skillDir, "assets", "stitch.example.json");
  const example = JSON.parse(await fsp.readFile(examplePath, "utf8"));
  const outputPath = values.output || path.resolve(process.cwd(), ".stitch.json");
  const written = await writeJson(outputPath, example, { force: Boolean(values.force) });
  printOutput({ outputPath: written }, Boolean(values.json));
}

async function commandShowConfig(values, config) {
  const settings = resolvedSettings(config.data, values);
  const persisted = await maybePersistResolvedConfig(values, config, settings);
  printOutput(
    redactSecrets(settings, persisted?.outputPath || config.path),
    Boolean(values.json),
  );
}

async function commandSaveConfig(values, config) {
  const settings = resolvedSettings(config.data, values);
  const persisted = await persistResolvedConfig(config, settings);
  printOutput(
    {
      outputPath: persisted.outputPath,
      config: redactSecrets(persisted.payload, persisted.outputPath),
    },
    Boolean(values.json),
  );
}

async function commandInstallSdk(values, config) {
  const settings = resolvedSettings(config.data, values);
  const packageJsonPath = await ensureSdkInstalled(settings, {
    forceInstall: Boolean(values["force-install"]),
  });
  printOutput(
    {
      runtimeDir: settings.runtime.dir,
      sdkPackage: settings.runtime.sdkPackage,
      packageJsonPath,
    },
    Boolean(values.json),
  );
}

async function commandListProjects(values, config) {
  const settings = resolvedSettings(config.data, values);
  const { client, sdk } = await createSdk(settings);
  try {
    const projects = await sdk.projects();
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(projects.map(normalizeProject), Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandCreateProject(values, config) {
  if (!values.title) {
    fail("Missing --title.");
  }
  const settings = resolvedSettings(config.data, values);
  const { client, sdk } = await createSdk(settings);
  try {
    const project = await sdk.createProject(values.title);
    settings.defaults.projectId = project.id;
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(normalizeProject(project), Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandListScreens(values, config) {
  const settings = resolvedSettings(config.data, values);
  const projectId = requireProjectId(values, settings);
  const { client, sdk } = await createSdk(settings);
  try {
    const project = sdk.project(projectId);
    const screens = await project.screens();
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(screens.map(screen => normalizeScreen(screen)), Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandGetScreen(values, config) {
  const settings = resolvedSettings(config.data, values);
  const projectId = requireProjectId(values, settings);
  if (!values["screen-id"]) {
    fail("Missing --screen-id.");
  }
  const { client, sdk } = await createSdk(settings);
  try {
    const project = sdk.project(projectId);
    const payload = values["include-exports"]
      ? await getScreenWithExports(project, values["screen-id"])
      : normalizeScreen(await project.getScreen(values["screen-id"]));
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(payload, Boolean(values.json));
  } finally {
    await client.close();
  }
}

function generationArgs(values, settings) {
  return {
    deviceType:
      normalizeEnum(values["device-type"]) || settings.defaults.deviceType || undefined,
    modelId:
      normalizeEnum(values["model-id"]) || settings.defaults.modelId || undefined,
  };
}

async function hydrateScreenResult(screen, values) {
  const [htmlUrl, imageUrl] = await Promise.all([screen.getHtml(), screen.getImage()]);
  const result = normalizeScreen(screen, { htmlUrl, imageUrl });

  if (values["html-out"]) {
    result.htmlPath = await downloadUrlToFile(htmlUrl, values["html-out"]);
  }
  if (values["image-out"]) {
    result.imagePath = await downloadUrlToFile(imageUrl, values["image-out"]);
  }

  return result;
}

async function commandGenerate(values, config) {
  const settings = resolvedSettings(config.data, values);
  const prompt = await readPrompt(values);
  const { deviceType, modelId } = generationArgs(values, settings);
  const { client, sdk } = await createSdk(settings);
  try {
    let projectId = values["project-id"] || settings.defaults.projectId;
    let project;

    if (projectId) {
      project = sdk.project(projectId);
    } else if (values["create-project-title"]) {
      project = await sdk.createProject(values["create-project-title"]);
      projectId = project.id;
    } else {
      fail("Missing --project-id. Use --create-project-title to create a project on the fly.");
    }

    const screen = await project.generate(prompt, deviceType, modelId);
    const result = await hydrateScreenResult(screen, values);
    result.projectId = projectId;
    settings.defaults.projectId = projectId;
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(result, Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandEdit(values, config) {
  const settings = resolvedSettings(config.data, values);
  const projectId = requireProjectId(values, settings);
  if (!values["screen-id"]) {
    fail("Missing --screen-id.");
  }
  const prompt = await readPrompt(values);
  const { deviceType, modelId } = generationArgs(values, settings);
  const { client, sdk } = await createSdk(settings);
  try {
    const project = sdk.project(projectId);
    const screen = await project.getScreen(values["screen-id"]);
    const edited = await screen.edit(prompt, deviceType, modelId);
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(await hydrateScreenResult(edited, values), Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandVariants(values, config) {
  const settings = resolvedSettings(config.data, values);
  const projectId = requireProjectId(values, settings);
  if (!values["screen-id"]) {
    fail("Missing --screen-id.");
  }
  const prompt = await readPrompt(values);
  const { deviceType, modelId } = generationArgs(values, settings);
  const variantOptions = {
    variantCount: values["variant-count"]
      ? coercePositiveInt(values["variant-count"], "variant-count")
      : settings.defaults.variantCount,
    creativeRange:
      normalizeEnum(values["creative-range"]) || settings.defaults.creativeRange || "EXPLORE",
    aspects: parseAspects(values.aspects) || settings.defaults.variantAspects,
  };
  const { client, sdk } = await createSdk(settings);
  try {
    const project = sdk.project(projectId);
    const screen = await project.getScreen(values["screen-id"]);
    const variants = await screen.variants(prompt, variantOptions, deviceType, modelId);
    const hydrated = [];
    for (const variant of variants) {
      hydrated.push(await hydrateScreenResult(variant, values));
    }
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(hydrated, Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandDownloadArtifact(values, config, kind) {
  const settings = resolvedSettings(config.data, values);
  const projectId = requireProjectId(values, settings);
  if (!values["screen-id"]) {
    fail("Missing --screen-id.");
  }
  if (!values.out) {
    fail("Missing --out.");
  }
  const { client, sdk } = await createSdk(settings);
  try {
    const project = sdk.project(projectId);
    const screen = await project.getScreen(values["screen-id"]);
    const url = kind === "html" ? await screen.getHtml() : await screen.getImage();
    const outputPath = await downloadUrlToFile(url, values.out);
    await maybePersistResolvedConfig(values, config, settings);
    printOutput({ url, outputPath }, Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandListTools(values, config) {
  const settings = resolvedSettings(config.data, values);
  const { client } = await createSdk(settings);
  try {
    const result = await client.listTools();
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(result.tools, Boolean(values.json));
  } finally {
    await client.close();
  }
}

async function commandCallTool(values, config) {
  if (!values["tool-name"]) {
    fail("Missing --tool-name.");
  }
  const settings = resolvedSettings(config.data, values);
  let parsedArgs = {};
  if (values["args-json"] && values["args-file"]) {
    fail("Use either --args-json or --args-file, not both.");
  }
  if (values["args-json"]) {
    parsedArgs = JSON.parse(values["args-json"]);
  } else if (values["args-file"]) {
    parsedArgs = JSON.parse(
      await fsp.readFile(resolveUserPath(values["args-file"]), "utf8"),
    );
  }

  const { client } = await createSdk(settings);
  try {
    const result = await client.callTool(values["tool-name"], parsedArgs);
    await maybePersistResolvedConfig(values, config, settings);
    printOutput(result, Boolean(values.json));
  } finally {
    await client.close();
  }
}

function commandUsage(command) {
  const usages = {
    "init-config": "stitch init-config [--output path] [--force] [--json]",
    "show-config": "stitch show-config [--config path] [--json]",
    "save-config":
      "stitch save-config [--config path] [--api-key ...] [--access-token ...] [--google-cloud-project ...] [--project-id ...] [--device-type ...] [--model-id ...] [--variant-count n] [--creative-range ...] [--aspects a,b] [--runtime-dir path] [--sdk-package spec] [--json]",
    "install-sdk": "stitch install-sdk [--runtime-dir path] [--sdk-package spec] [--force-install] [--json]",
    "list-projects": "stitch list-projects [common-options]",
    "create-project": "stitch create-project --title <title> [common-options]",
    "list-screens": "stitch list-screens --project-id <id> [common-options]",
    "get-screen":
      "stitch get-screen --project-id <id> --screen-id <id> [--include-exports] [common-options]",
    "generate":
      "stitch generate (--project-id <id> | --create-project-title <title>) (--prompt <text> | --prompt-file <path>) [--device-type ...] [--model-id ...] [--html-out path] [--image-out path] [common-options]",
    "edit":
      "stitch edit --project-id <id> --screen-id <id> (--prompt <text> | --prompt-file <path>) [--device-type ...] [--model-id ...] [--html-out path] [--image-out path] [common-options]",
    "variants":
      "stitch variants --project-id <id> --screen-id <id> (--prompt <text> | --prompt-file <path>) [--variant-count n] [--creative-range ...] [--aspects a,b] [--device-type ...] [--model-id ...] [common-options]",
    "download-html":
      "stitch download-html --project-id <id> --screen-id <id> --out <path> [common-options]",
    "download-image":
      "stitch download-image --project-id <id> --screen-id <id> --out <path> [common-options]",
    "list-tools": "stitch list-tools [common-options]",
    "call-tool":
      "stitch call-tool --tool-name <name> [--args-json '{}'] [--args-file path] [common-options]",
  };
  const usage = usages[command];
  if (!usage) {
    fail(`Unknown command: ${command}`);
  }
  console.log(usage);
}

async function main() {
  const [, , rawCommand, ...rest] = process.argv;
  if (!rawCommand || rawCommand === "--help" || rawCommand === "-h") {
    console.log(HELP_TEXT);
    return;
  }

  const command = rawCommand.trim();

  if (rest.includes("--help") || rest.includes("-h")) {
    commandUsage(command);
    return;
  }

  switch (command) {
    case "init-config": {
      const values = parseCommandArgs(rest, {
        output: { type: "string" },
        force: { type: "boolean" },
      });
      await commandInitConfig(values);
      return;
    }
    case "show-config": {
      const values = parseCommandArgs(rest);
      const config = await loadCommandConfig(values);
      await commandShowConfig(values, config);
      return;
    }
    case "save-config": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
        "device-type": { type: "string" },
        "model-id": { type: "string" },
        "variant-count": { type: "string" },
        "creative-range": { type: "string" },
        aspects: { type: "string" },
      });
      const config = await loadCommandConfig(values, { allowMissing: true });
      await commandSaveConfig(values, config);
      return;
    }
    case "install-sdk": {
      const values = parseCommandArgs(rest);
      const config = await loadCommandConfig(values);
      await commandInstallSdk(values, config);
      return;
    }
    case "list-projects": {
      const values = parseCommandArgs(rest);
      const config = await loadCommandConfig(values);
      await commandListProjects(values, config);
      return;
    }
    case "create-project": {
      const values = parseCommandArgs(rest, {
        title: { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandCreateProject(values, config);
      return;
    }
    case "list-screens": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandListScreens(values, config);
      return;
    }
    case "get-screen": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
        "screen-id": { type: "string" },
        "include-exports": { type: "boolean" },
      });
      const config = await loadCommandConfig(values);
      await commandGetScreen(values, config);
      return;
    }
    case "generate": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
        "create-project-title": { type: "string" },
        prompt: { type: "string" },
        "prompt-file": { type: "string" },
        "device-type": { type: "string" },
        "model-id": { type: "string" },
        "html-out": { type: "string" },
        "image-out": { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandGenerate(values, config);
      return;
    }
    case "edit": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
        "screen-id": { type: "string" },
        prompt: { type: "string" },
        "prompt-file": { type: "string" },
        "device-type": { type: "string" },
        "model-id": { type: "string" },
        "html-out": { type: "string" },
        "image-out": { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandEdit(values, config);
      return;
    }
    case "variants": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
        "screen-id": { type: "string" },
        prompt: { type: "string" },
        "prompt-file": { type: "string" },
        "device-type": { type: "string" },
        "model-id": { type: "string" },
        "html-out": { type: "string" },
        "image-out": { type: "string" },
        "variant-count": { type: "string" },
        "creative-range": { type: "string" },
        aspects: { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandVariants(values, config);
      return;
    }
    case "download-html":
    case "download-image": {
      const values = parseCommandArgs(rest, {
        "project-id": { type: "string" },
        "screen-id": { type: "string" },
        out: { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandDownloadArtifact(values, config, command === "download-html" ? "html" : "image");
      return;
    }
    case "list-tools": {
      const values = parseCommandArgs(rest);
      const config = await loadCommandConfig(values);
      await commandListTools(values, config);
      return;
    }
    case "call-tool": {
      const values = parseCommandArgs(rest, {
        "tool-name": { type: "string" },
        "args-json": { type: "string" },
        "args-file": { type: "string" },
      });
      const config = await loadCommandConfig(values);
      await commandCallTool(values, config);
      return;
    }
    default:
      fail(`Unknown command: ${command}`);
  }
}

try {
  await main();
} catch (error) {
  const exitCode = error?.exitCode || 1;
  const payload = {
    error: error?.message || String(error),
  };
  console.error(JSON.stringify(payload, null, 2));
  process.exit(exitCode);
}
