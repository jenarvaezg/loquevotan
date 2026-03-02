#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";

const DIST_DATA_DIR = path.resolve("dist", "data");
const MAX_ASSET_BYTES = 25 * 1024 * 1024;
const TARGET_PART_BYTES = 20 * 1024 * 1024;

function isVotesJsonFile(fileName) {
  return /^votos_.+\.json$/i.test(fileName);
}

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const out = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await walk(fullPath)));
    } else if (entry.isFile()) {
      out.push(fullPath);
    }
  }
  return out;
}

function toJsonBytes(value) {
  return Buffer.byteLength(JSON.stringify(value), "utf8");
}

async function splitVotesFile(filePath) {
  const originalText = await fs.readFile(filePath, "utf8");
  const originalBytes = Buffer.byteLength(originalText, "utf8");
  if (originalBytes <= MAX_ASSET_BYTES) return null;

  const payload = JSON.parse(originalText);
  const votos = Array.isArray(payload?.votos) ? payload.votos : null;
  const detail = payload?.detail && typeof payload.detail === "object" ? payload.detail : {};

  if (!votos) {
    throw new Error(`Invalid votos payload (missing votos array): ${filePath}`);
  }

  if (!votos.length) {
    throw new Error(`Cannot split oversized votos file without votes: ${filePath}`);
  }

  const estimatedBytesPerVote = Math.max(1, Math.floor(originalBytes / votos.length));
  const rowsPerPart = Math.max(1, Math.floor(TARGET_PART_BYTES / estimatedBytesPerVote));
  const partNames = [];
  const baseName = path.basename(filePath, ".json");
  const dirName = path.dirname(filePath);

  let partIdx = 0;
  for (let offset = 0; offset < votos.length; offset += rowsPerPart) {
    partIdx += 1;
    const partVotes = votos.slice(offset, offset + rowsPerPart);

    const voteIdsInPart = new Set();
    for (let i = 0; i < partVotes.length; i++) {
      voteIdsInPart.add(String(partVotes[i][0]));
    }

    const partDetail = {};
    for (const voteId of voteIdsInPart) {
      if (Object.prototype.hasOwnProperty.call(detail, voteId)) {
        partDetail[voteId] = detail[voteId];
      }
    }

    const partName = `${baseName}.part${partIdx}.json`;
    const partPath = path.join(dirName, partName);
    const partPayload = { votos: partVotes, detail: partDetail };

    await fs.writeFile(partPath, JSON.stringify(partPayload), "utf8");
    const partBytes = toJsonBytes(partPayload);
    if (partBytes > MAX_ASSET_BYTES) {
      throw new Error(
        `Split part still exceeds ${MAX_ASSET_BYTES} bytes (${partName}: ${partBytes} bytes)`
      );
    }

    partNames.push(partName);
  }

  const manifest = {
    split: true,
    version: 1,
    parts: partNames,
  };

  await fs.writeFile(filePath, JSON.stringify(manifest), "utf8");

  return {
    filePath,
    originalBytes,
    parts: partNames.length,
  };
}

async function main() {
  try {
    await fs.access(DIST_DATA_DIR);
  } catch {
    console.log(`[cf-split] ${DIST_DATA_DIR} no existe. Ejecuta primero "npm run build".`);
    process.exit(1);
  }

  const files = await walk(DIST_DATA_DIR);
  const votesFiles = files.filter((filePath) => isVotesJsonFile(path.basename(filePath)));

  if (!votesFiles.length) {
    console.log("[cf-split] No se encontraron archivos votos_*.json en dist/data.");
    return;
  }

  const results = [];
  for (const filePath of votesFiles) {
    const result = await splitVotesFile(filePath);
    if (result) results.push(result);
  }

  if (!results.length) {
    console.log("[cf-split] No hubo archivos por encima de 25 MiB. Sin cambios.");
    return;
  }

  for (const result of results) {
    console.log(
      `[cf-split] ${path.relative(process.cwd(), result.filePath)} -> ${result.parts} partes (antes ${(
        result.originalBytes /
        (1024 * 1024)
      ).toFixed(2)} MiB)`
    );
  }
}

main().catch((err) => {
  console.error(`[cf-split] ERROR: ${err?.message || err}`);
  process.exit(1);
});
