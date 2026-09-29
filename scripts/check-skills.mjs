#!/usr/bin/env node
// Checks the invariants described in CLAUDE.md. No dependencies. Exit 1 on any error.
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const PROMOTED = ["agent-tooling", "web", "dev"];
const OTHER = ["in-progress", "misc", "deprecated"];
const MAX_DESCRIPTION = 300;

const errors = [];
const fail = (message) => errors.push(message);
const read = (path) => readFileSync(join(ROOT, path), "utf8");
const dirs = (path) =>
  existsSync(join(ROOT, path))
    ? readdirSync(join(ROOT, path)).filter((n) => statSync(join(ROOT, path, n)).isDirectory())
    : [];

function frontmatter(path) {
  const match = /^---\n([\s\S]*?)\n---/.exec(read(path));
  if (!match) return {};
  const fields = {};
  for (const line of match[1].split("\n")) {
    const m = /^([\w-]+):\s*(.*)$/.exec(line);
    if (m) fields[m[1]] = m[2].trim();
  }
  return fields;
}

// "- **[name](prefix/name/SKILL.md)**: text" lines, keyed by name
function readmeEntries(text) {
  const entries = new Map();
  for (const m of text.matchAll(/^- \*\*\[([^\]]+)\]\(([^)]+)\)\*\*: (.+)$/gm)) {
    entries.set(m[1], { path: m[2], text: m[3] });
  }
  return entries;
}

const plugin = JSON.parse(read(".claude-plugin/plugin.json"));
const pluginSkills = new Set(plugin.skills);
const topEntries = readmeEntries(read("README.md"));
const seen = new Set();

for (const bucket of [...PROMOTED, ...OTHER]) {
  const promoted = PROMOTED.includes(bucket);
  if (!existsSync(join(ROOT, "skills", bucket, "README.md"))) fail(`skills/${bucket}/README.md is missing`);
  const bucketEntries = existsSync(join(ROOT, "skills", bucket, "README.md"))
    ? readmeEntries(read(`skills/${bucket}/README.md`))
    : new Map();

  const names = dirs(`skills/${bucket}`);
  for (const name of names) {
    const dir = `skills/${bucket}/${name}`;
    if (!existsSync(join(ROOT, dir, "SKILL.md"))) {
      fail(`${dir}: no SKILL.md`);
      continue;
    }
    if (seen.has(name)) fail(`${name}: skill name is used in more than one bucket`);
    seen.add(name);

    const fm = frontmatter(`${dir}/SKILL.md`);
    if (fm.name !== name) fail(`${dir}/SKILL.md: frontmatter name "${fm.name}" must equal the folder name "${name}"`);
    if (!fm.description) fail(`${dir}/SKILL.md: missing description`);
    else if (fm.description.length > MAX_DESCRIPTION)
      fail(`${dir}/SKILL.md: description is ${fm.description.length} characters (max ${MAX_DESCRIPTION})`);
    if (!existsSync(join(ROOT, dir, "agents", "openai.yaml"))) fail(`${dir}: missing agents/openai.yaml`);

    const bucketEntry = bucketEntries.get(name);
    if (!bucketEntry) fail(`skills/${bucket}/README.md: no entry for ${name}`);
    else if (bucketEntry.path !== `./${name}/SKILL.md`) fail(`skills/${bucket}/README.md: wrong link for ${name}`);

    const inPlugin = pluginSkills.has(`./${dir}`);
    const topEntry = topEntries.get(name);
    if (promoted) {
      if (!inPlugin) fail(`.claude-plugin/plugin.json: missing ./${dir}`);
      if (!topEntry) fail(`README.md: no entry for ${name}`);
      else {
        if (topEntry.path !== `./${dir}/SKILL.md`) fail(`README.md: wrong link for ${name}`);
        if (bucketEntry && topEntry.text !== bucketEntry.text)
          fail(`README.md and skills/${bucket}/README.md describe ${name} differently`);
      }
    } else {
      if (inPlugin) fail(`.claude-plugin/plugin.json: ${dir} is not promoted and must not be listed`);
      if (topEntry) fail(`README.md: ${name} is not promoted and must not be listed`);
    }
  }
  for (const name of bucketEntries.keys())
    if (!names.includes(name)) fail(`skills/${bucket}/README.md: lists ${name}, which has no folder`);
}

for (const path of pluginSkills)
  if (!existsSync(join(ROOT, path, "SKILL.md"))) fail(`.claude-plugin/plugin.json: ${path} has no SKILL.md`);

// skills.sh.json groups the promoted skills for the skills.sh repo page: one group per bucket.
const groupsJson = JSON.parse(read("skills.sh.json"));
const grouped = new Map();
for (const g of groupsJson.groupings) for (const n of g.skills) grouped.set(n, (grouped.get(n) ?? 0) + 1);
for (const bucket of PROMOTED)
  for (const name of dirs(`skills/${bucket}`))
    if (grouped.get(name) !== 1) fail(`skills.sh.json: ${name} must be listed in exactly one group (found ${grouped.get(name) ?? 0})`);
for (const name of grouped.keys())
  if (!seen.has(name)) fail(`skills.sh.json: lists ${name}, which has no folder`);

if (errors.length) {
  console.error(errors.map((e) => `error: ${e}`).join("\n"));
  process.exit(1);
}
console.log(`ok: ${seen.size} skills, ${pluginSkills.size} in the plugin`);
