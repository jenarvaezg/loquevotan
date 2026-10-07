#!/usr/bin/env node
// Dumps the rows currently in D1 (only the columns we sync) to
// <out-dir>/<table>.json, so build_d1_seed.mjs --diff-against can write just
// what changed. Reads are cheap on D1 (5M/day free); writes are not.
//
// Usage: node scripts/cloudflare/export_d1_tables.mjs --database <name> --out-dir <dir> [--local --persist-to <dir>]

import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { TABLES, sqlLiteral } from "./d1_diff.mjs";

const WRANGLER = process.env.WRANGLER || "wrangler@4.86.0";
const PAGE_SIZE = 5000;

function parseArgs(argv) {
  const valueOf = (flag) => {
    const index = argv.indexOf(flag);
    return index >= 0 ? argv[index + 1] : undefined;
  };
  const database = valueOf("--database") || process.env.CLOUDFLARE_D1_DATABASE_NAME;
  const outDir = valueOf("--out-dir");
  if (!database || !outDir) {
    throw new Error("Uso: export_d1_tables.mjs --database <nombre> --out-dir <dir> [--local --persist-to <dir>]");
  }
  const target = argv.includes("--local") ? ["--local"] : ["--remote"];
  const persistTo = valueOf("--persist-to");
  if (persistTo) target.push("--persist-to", persistTo);
  return { database, outDir: path.resolve(outDir), target };
}

function query(database, target, sql) {
  const output = execFileSync(
    "npx",
    ["--yes", WRANGLER, "d1", "execute", database, ...target, "--json", "--command", sql],
    { encoding: "utf8", maxBuffer: 1024 * 1024 * 1024, stdio: ["ignore", "pipe", "inherit"] }
  );
  const parsed = JSON.parse(output);
  const result = Array.isArray(parsed) ? parsed[0] : parsed;
  if (!result?.success) throw new Error(`Consulta D1 fallida: ${sql}`);
  return result.results || [];
}

async function main() {
  const { database, outDir, target } = parseArgs(process.argv.slice(2));
  await fs.mkdir(outDir, { recursive: true });

  // Per scope, to keep each response small (votaciones is the big one).
  const scopeIds = query(database, target, "SELECT DISTINCT scope_id FROM votaciones UNION SELECT scope_id FROM scope_meta")
    .map((row) => row.scope_id)
    .filter(Boolean);

  for (const table of TABLES) {
    const rows = [];
    // Keyset pagination on the last primary-key column (scope_id comes first).
    const pageKey = table.key[table.key.length - 1];
    for (const scopeId of scopeIds) {
      let after = null;
      for (;;) {
        const where = [`scope_id = ${sqlLiteral(scopeId)}`];
        if (after !== null && pageKey !== "scope_id") where.push(`${pageKey} > ${sqlLiteral(after)}`);
        const page = query(
          database,
          target,
          `SELECT ${table.columns.join(", ")} FROM ${table.name} WHERE ${where.join(" AND ")} ORDER BY ${pageKey} LIMIT ${PAGE_SIZE}`
        );
        rows.push(...page);
        if (page.length < PAGE_SIZE || pageKey === "scope_id") break;
        after = page[page.length - 1][pageKey];
      }
    }
    await fs.writeFile(path.join(outDir, `${table.name}.json`), JSON.stringify(rows), "utf8");
    console.log(`[cf-d1-export] ${table.name}: ${rows.length} filas`);
  }
}

main().catch((err) => {
  console.error(`[cf-d1-export] ERROR: ${err?.message || err}`);
  process.exit(1);
});
