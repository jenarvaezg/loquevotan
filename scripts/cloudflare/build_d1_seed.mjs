#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { TABLES, diffTable, renderDeletes, renderUpdates, renderUpserts, sqlLiteral } from "./d1_diff.mjs";

const ROOT = process.cwd();
const DATA_DIR = path.join(ROOT, "public", "data");
const DEFAULT_OUT = path.join(ROOT, "tmp", "cloudflare-d1-seed.sql");
const D1_SQL_BATCH_SIZE = Number.parseInt(process.env.D1_SQL_BATCH_SIZE || "25", 10);
const TABLE_BY_NAME = Object.fromEntries(TABLES.map((t) => [t.name, t]));

function toNumberOrNull(value) {
  // Number(null) is 0: keep missing values as NULL (e.g. loyalty of Mixto members).
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

const ROMAN_VALUES = { I: 1, V: 5, X: 10, L: 50, C: 100 };

function romanToInt(roman) {
  let total = 0;
  let prev = 0;
  for (const ch of String(roman || "").toUpperCase().split("").reverse()) {
    const value = ROMAN_VALUES[ch] || 0;
    total = value < prev ? total - value : total + value;
    prev = Math.max(prev, value);
  }
  return total;
}

// National provinces come per legislature ({"XIV": "Madrid", "XV": "Segovia"});
// the column holds the most recent one (it used to store "[object Object]").
function latestProvince(value) {
  if (!value || typeof value !== "object") return value || null;
  const legs = Object.keys(value).sort((a, b) => romanToInt(b) - romanToInt(a));
  return legs.length ? value[legs[0]] || null : null;
}

function toJsonText(value) {
  try {
    return JSON.stringify(value ?? null);
  } catch {
    return null;
  }
}

function normalizeSearchToken(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

// Regional metadata uses dd/mm/yyyy; D1 sorts and filters dates as text.
function toIsoDate(value) {
  const text = String(value || "").trim();
  const match = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return text || null;
  const [, day, month, year] = match;
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function parseArgs(argv) {
  const valueOf = (flag) => {
    const index = argv.findIndex((a) => a === flag);
    return index >= 0 && argv[index + 1] ? String(argv[index + 1]) : "";
  };
  const out = valueOf("--out");
  const diffAgainst = valueOf("--diff-against");
  const scopes = valueOf("--scopes")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return {
    outFile: out ? path.resolve(ROOT, out) : DEFAULT_OUT,
    scopes,
    diffDir: diffAgainst ? path.resolve(ROOT, diffAgainst) : "",
  };
}

function parseScopeFilter(scopesArg, allScopes) {
  if (!Array.isArray(scopesArg) || !scopesArg.length) return allScopes;
  const available = new Set(allScopes.map((s) => String(s?.id || "").trim().toLowerCase()).filter(Boolean));
  const selected = [];
  const unknown = [];
  for (const scopeId of scopesArg) {
    if (available.has(scopeId)) selected.push(scopeId);
    else unknown.push(scopeId);
  }
  if (unknown.length) {
    throw new Error(`Scopes desconocidos en --scopes: ${unknown.join(", ")}`);
  }
  return allScopes.filter((scope) => selected.includes(String(scope?.id || "").trim().toLowerCase()));
}

async function readJson(filePath) {
  const raw = await fs.readFile(filePath, "utf8");
  return JSON.parse(raw);
}

function renderInserts(table, rows, batchSize = D1_SQL_BATCH_SIZE) {
  const statements = [];
  for (let i = 0; i < rows.length; i += batchSize) {
    const values = rows
      .slice(i, i + batchSize)
      .map((row) => `(${table.columns.map((column) => sqlLiteral(row[column])).join(", ")})`)
      .join(",\n");
    statements.push(`INSERT OR REPLACE INTO ${table.name} (${table.columns.join(", ")}) VALUES\n${values};`);
  }
  return statements;
}

async function readExistingRows(diffDir, tableName) {
  // Written by scripts/cloudflare/export_d1_tables.mjs
  return readJson(path.join(diffDir, `${tableName}.json`));
}

function scopeDataPaths(scopeId) {
  if (scopeId === "nacional") {
    return {
      manifest: path.join(DATA_DIR, "manifest_home.json"),
      meta: path.join(DATA_DIR, "votaciones_meta.json"),
    };
  }
  return {
    manifest: path.join(DATA_DIR, scopeId, "manifest_home.json"),
    meta: path.join(DATA_DIR, scopeId, "votaciones_meta.json"),
  };
}

function buildScopeRows(scopeId, scope, manifest, meta) {
  const rows = { scope_meta: [], groups: [], votaciones: [], diputados: [] };

  rows.scope_meta.push({
    scope_id: scopeId,
    scope_name: String(scope?.nombre || scopeId),
    updated_at: manifest?.updatedAt || null,
    diputados_count: Number(manifest?.stats?.diputados || 0),
    votaciones_count: Number(manifest?.stats?.votaciones || 0),
    votos_count: Number(manifest?.stats?.votos || 0),
  });

  const grupos = Array.isArray(meta?.grupos) ? meta.grupos : [];
  grupos.forEach((name, g) => rows.groups.push({ scope_id: scopeId, group_idx: g, group_name: name || "" }));

  const votaciones = Array.isArray(meta?.votaciones) ? meta.votaciones : [];
  const votResults = Array.isArray(meta?.votResults) ? meta.votResults : [];
  const categorias = Array.isArray(meta?.categorias) ? meta.categorias : [];
  votaciones.forEach((vote = {}, i) => {
    const result = votResults[i] || {};
    const categoriaIdx = Number.isInteger(vote.categoria) ? vote.categoria : null;
    rows.votaciones.push({
      scope_id: scopeId,
      vot_idx: i,
      id: vote.id || "",
      legislatura: vote.legislatura || null,
      fecha: toIsoDate(vote.fecha),
      titulo_ciudadano: vote.titulo_ciudadano || "",
      categoria_idx: categoriaIdx,
      categoria_label: categoriaIdx !== null ? categorias[categoriaIdx] || null : null,
      etiquetas_json: toJsonText(Array.isArray(vote.etiquetas) ? vote.etiquetas : []),
      proponente: vote.proponente || "",
      sub_tipo: vote.subTipo || null,
      expediente: vote.exp || null,
      result: result.result || null,
      favor: toNumberOrNull(result.favor),
      contra: toNumberOrNull(result.contra),
      abstencion: toNumberOrNull(result.abstencion),
      total: toNumberOrNull(result.total),
      search_text: normalizeSearchToken(`${vote.titulo_ciudadano || ""} ${vote.proponente || ""} ${vote.id || ""}`),
    });
  });

  const diputados = Array.isArray(meta?.diputados) ? meta.diputados : [];
  const dipStats = Array.isArray(meta?.dipStats) ? meta.dipStats : [];
  const dipFotos = Array.isArray(meta?.dipFotos) ? meta.dipFotos : [];
  const dipProvincias = Array.isArray(meta?.dipProvincias) ? meta.dipProvincias : [];
  diputados.forEach((rawName, i) => {
    const nombre = String(rawName || "");
    const stats = dipStats[i] || {};
    const groupIdx = Number.isInteger(stats?.mainGrupo) ? stats.mainGrupo : null;
    rows.diputados.push({
      scope_id: scopeId,
      dip_idx: i,
      nombre,
      nombre_search: normalizeSearchToken(nombre),
      main_grupo_idx: groupIdx,
      main_grupo_name: groupIdx !== null ? grupos[groupIdx] || null : null,
      total: toNumberOrNull(stats.total),
      favor: toNumberOrNull(stats.favor),
      contra: toNumberOrNull(stats.contra),
      abstencion: toNumberOrNull(stats.abstencion),
      no_vota: toNumberOrNull(stats.no_vota),
      loyalty: toNumberOrNull(stats.loyalty),
      foto_json: toJsonText(dipFotos[i] ?? null),
      provincia: latestProvince(dipProvincias[i]),
    });
  });

  return rows;
}

async function main() {
  const { outFile, scopes: scopeFilterArg, diffDir } = parseArgs(process.argv.slice(2));
  await fs.mkdir(path.dirname(outFile), { recursive: true });

  const ambitos = await readJson(path.join(DATA_DIR, "ambitos.json"));
  const allScopes = Array.isArray(ambitos?.ambitos) ? ambitos.ambitos : [];
  const scopes = parseScopeFilter(scopeFilterArg, allScopes);
  if (!scopes.length) {
    throw new Error("No hay ámbitos para procesar.");
  }
  const scopedMode = scopeFilterArg.length > 0;
  const scopeIds = scopes.map((scope) => String(scope?.id || "").trim().toLowerCase()).filter(Boolean);

  const desired = { scope_meta: [], groups: [], votaciones: [], diputados: [] };
  const summary = [];
  for (const scope of scopes) {
    const scopeId = String(scope?.id || "").trim().toLowerCase();
    if (!scopeId) continue;
    const paths = scopeDataPaths(scopeId);
    const [manifest, meta] = await Promise.all([readJson(paths.manifest), readJson(paths.meta)]);
    const rows = buildScopeRows(scopeId, scope, manifest, meta);
    for (const table of TABLES) desired[table.name].push(...rows[table.name]);
    summary.push({
      scope: scopeId,
      votaciones: rows.votaciones.length,
      diputados: rows.diputados.length,
      grupos: rows.groups.length,
    });
  }

  const statements = ["-- Generated by scripts/cloudflare/build_d1_seed.mjs"];
  let rowsToWrite = 0;

  if (diffDir) {
    // Only rows that changed; nothing is dropped or re-inserted wholesale.
    for (const table of TABLES) {
      const existing = await readExistingRows(diffDir, table.name);
      const { inserts, updates, deletes } = diffTable(table, desired[table.name], existing, scopeIds, {
        pruneOtherScopes: !scopedMode,
      });
      statements.push(
        ...renderDeletes(table, deletes),
        ...renderUpdates(table, updates),
        ...renderUpserts(table, inserts, D1_SQL_BATCH_SIZE)
      );
      rowsToWrite += inserts.length + updates.length + deletes.length;
      console.log(
        `[cf-d1-seed] ${table.name}: ${inserts.length} altas, ${updates.length} cambios, ${deletes.length} bajas`
      );
    }
  } else {
    for (const scopeId of scopedMode ? scopeIds : []) {
      for (const table of [...TABLES].reverse()) {
        statements.push(`DELETE FROM ${table.name} WHERE scope_id = ${sqlLiteral(scopeId)};`);
      }
    }
    if (!scopedMode) {
      for (const table of [...TABLES].reverse()) statements.push(`DELETE FROM ${table.name};`);
    }
    for (const table of TABLES) {
      statements.push(...renderInserts(TABLE_BY_NAME[table.name], desired[table.name]));
      rowsToWrite += desired[table.name].length;
    }
  }

  await fs.writeFile(outFile, `${statements.join("\n")}\n`, "utf8");

  const stats = await fs.stat(outFile);
  console.log(`[cf-d1-seed] SQL generado: ${outFile}`);
  console.log(
    `[cf-d1-seed] modo: ${diffDir ? "diff" : "completo"}${scopedMode ? ` · scopes(${scopeIds.join(",")})` : ""}`
  );
  console.log(`[cf-d1-seed] tamaño: ${(stats.size / 1024 / 1024).toFixed(2)} MiB · filas a escribir: ${rowsToWrite}`);
  for (const row of summary) {
    console.log(
      `[cf-d1-seed] ${row.scope}: ${row.votaciones} votaciones, ${row.diputados} diputados, ${row.grupos} grupos`
    );
  }
  if (process.env.GITHUB_OUTPUT) {
    await fs.appendFile(process.env.GITHUB_OUTPUT, `rows_to_write=${rowsToWrite}\n`, "utf8");
  }
}

main().catch((err) => {
  console.error(`[cf-d1-seed] ERROR: ${err?.message || err}`);
  process.exit(1);
});
