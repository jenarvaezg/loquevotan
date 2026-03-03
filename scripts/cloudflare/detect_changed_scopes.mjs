#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();
const AMBITOS_PATH = path.join(ROOT, "public", "data", "ambitos.json");
const OUTPUT_PATH = process.env.GITHUB_OUTPUT || "";

function readChangedFiles() {
  const trackedRaw = execFileSync("git", ["diff", "--name-only", "HEAD", "--", "public/data"], {
    cwd: ROOT,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
  });
  const untrackedRaw = execFileSync(
    "git",
    ["ls-files", "--others", "--exclude-standard", "--", "public/data"],
    {
      cwd: ROOT,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }
  );
  const tracked = trackedRaw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const untracked = untrackedRaw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return [...new Set([...tracked, ...untracked])];
}

async function readAllScopes() {
  const raw = await fs.readFile(AMBITOS_PATH, "utf8");
  const payload = JSON.parse(raw);
  return (Array.isArray(payload?.ambitos) ? payload.ambitos : [])
    .map((scope) => String(scope?.id || "").trim().toLowerCase())
    .filter(Boolean);
}

function scopesFromFiles(files, allScopes) {
  const byFile = new Set();
  const validScopes = new Set(allScopes);

  for (const file of files) {
    if (!file.startsWith("public/data/")) continue;
    const rel = file.slice("public/data/".length);
    if (!rel) continue;

    if (rel === "ambitos.json") {
      for (const scopeId of allScopes) byFile.add(scopeId);
      continue;
    }

    const [firstSegment] = rel.split("/");
    if (!firstSegment) continue;

    if (!rel.includes("/")) {
      // Files directly under public/data belong to nacional dataset.
      byFile.add("nacional");
      continue;
    }

    if (validScopes.has(firstSegment)) {
      byFile.add(firstSegment);
    }
  }

  return [...byFile].sort();
}

async function writeGithubOutput(payload) {
  if (!OUTPUT_PATH) return;
  const lines = [
    `scope_csv=${payload.scopeCsv}`,
    `scope_count=${payload.scopeCount}`,
    `has_scope_changes=${payload.hasScopeChanges}`,
    "",
  ].join("\n");
  await fs.appendFile(OUTPUT_PATH, lines, "utf8");
}

async function main() {
  const changedFiles = readChangedFiles();
  const allScopes = await readAllScopes();
  const scopeIds = scopesFromFiles(changedFiles, allScopes);
  const scopeCsv = scopeIds.join(",");
  const payload = {
    scopeCsv,
    scopeCount: String(scopeIds.length),
    hasScopeChanges: scopeIds.length > 0 ? "true" : "false",
  };

  console.log(`[cf-d1-scopes] changed files: ${changedFiles.length}`);
  console.log(`[cf-d1-scopes] scopes: ${scopeCsv || "(none)"}`);
  await writeGithubOutput(payload);
}

main().catch((error) => {
  console.error(`[cf-d1-scopes] ERROR: ${error?.message || error}`);
  process.exit(1);
});
