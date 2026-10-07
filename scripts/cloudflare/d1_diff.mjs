// Row-level diff between the rows we want in D1 and the rows already there.
//
// The D1 free tier allows 100k rows written per day and every index entry
// counts as a written row: re-seeding everything (~27k votes x 4 indexes) no
// longer fits. Writing only new/changed rows keeps a weekly update in the low
// thousands and a code-only deploy at zero.

export const TABLES = [
  {
    name: "scope_meta",
    key: ["scope_id"],
    columns: ["scope_id", "scope_name", "updated_at", "diputados_count", "votaciones_count", "votos_count"],
  },
  {
    name: "groups",
    key: ["scope_id", "group_idx"],
    columns: ["scope_id", "group_idx", "group_name"],
  },
  {
    name: "votaciones",
    key: ["scope_id", "id"],
    columns: [
      "scope_id",
      "vot_idx",
      "id",
      "legislatura",
      "fecha",
      "titulo_ciudadano",
      "categoria_idx",
      "categoria_label",
      "etiquetas_json",
      "proponente",
      "sub_tipo",
      "expediente",
      "result",
      "favor",
      "contra",
      "abstencion",
      "total",
      "search_text",
    ],
  },
  {
    name: "diputados",
    key: ["scope_id", "dip_idx"],
    columns: [
      "scope_id",
      "dip_idx",
      "nombre",
      "nombre_search",
      "main_grupo_idx",
      "main_grupo_name",
      "total",
      "favor",
      "contra",
      "abstencion",
      "no_vota",
      "loyalty",
      "foto_json",
      "provincia",
    ],
  },
];

export function sqlLiteral(value) {
  if (value === null || value === undefined) return "NULL";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "NULL";
  return `'${String(value).replaceAll("'", "''")}'`;
}

// D1 returns INTEGER/REAL as numbers, TEXT as strings and NULL as null; our
// rows use the same JS types, so values compare directly once normalized.
function normalize(value) {
  if (value === undefined) return null;
  return value;
}

function rowKey(table, row) {
  return JSON.stringify(table.key.map((column) => normalize(row[column])));
}

function sameRow(table, a, b) {
  return table.columns.every((column) => normalize(a[column]) === normalize(b[column]));
}

/**
 * @param table one of TABLES
 * @param desiredRows rows (objects keyed by column) for the scopes being synced
 * @param existingRows rows currently in D1 (objects keyed by column)
 * @param syncedScopes scope ids being synced; existing rows of other scopes are
 *   left alone unless `pruneOtherScopes` is set (full sync).
 */
export function diffTable(table, desiredRows, existingRows, syncedScopes, { pruneOtherScopes = false } = {}) {
  const scopes = new Set(syncedScopes);
  const existingByKey = new Map(existingRows.map((row) => [rowKey(table, row), row]));
  const desiredKeys = new Set();
  const upserts = [];

  for (const row of desiredRows) {
    const key = rowKey(table, row);
    desiredKeys.add(key);
    const current = existingByKey.get(key);
    if (!current || !sameRow(table, current, row)) upserts.push(row);
  }

  const deletes = existingRows.filter((row) => {
    if (desiredKeys.has(rowKey(table, row))) return false;
    return scopes.has(row.scope_id) || pruneOtherScopes;
  });

  return { upserts, deletes };
}

export function renderUpserts(table, rows, batchSize = 25) {
  const statements = [];
  const updates = table.columns
    .filter((column) => !table.key.includes(column))
    .map((column) => `${column} = excluded.${column}`)
    .join(", ");
  for (let i = 0; i < rows.length; i += batchSize) {
    const values = rows
      .slice(i, i + batchSize)
      .map((row) => `(${table.columns.map((column) => sqlLiteral(row[column])).join(", ")})`)
      .join(",\n");
    statements.push(
      `INSERT INTO ${table.name} (${table.columns.join(", ")}) VALUES\n${values}\n` +
        `ON CONFLICT(${table.key.join(", ")}) DO UPDATE SET ${updates};`
    );
  }
  return statements;
}

export function renderDeletes(table, rows) {
  return rows.map((row) => {
    const where = table.key.map((column) => `${column} = ${sqlLiteral(row[column])}`).join(" AND ");
    return `DELETE FROM ${table.name} WHERE ${where};`;
  });
}
