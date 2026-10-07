import { describe, it, expect } from 'vitest';
import { TABLES, diffTable, renderUpserts, renderUpdates, renderDeletes, sqlLiteral } from '../../scripts/cloudflare/d1_diff.mjs';

const groups = TABLES.find((t) => t.name === 'groups');

const row = (scope_id, group_idx, group_name) => ({ scope_id, group_idx, group_name });

describe('d1_diff', () => {
  it('writes nothing when D1 already has the same rows', () => {
    const rows = [row('nacional', 0, 'GP'), row('nacional', 1, 'GS')];
    const { inserts, updates, deletes } = diffTable(groups, rows, rows.map((r) => ({ ...r })), ['nacional']);
    expect(inserts).toEqual([]);
    expect(updates).toEqual([]);
    expect(deletes).toEqual([]);
  });

  it('inserts new rows, updates only changed columns and deletes rows that disappeared', () => {
    const existing = [row('nacional', 0, 'GP'), row('nacional', 1, 'GS'), row('nacional', 2, 'GCs')];
    const desired = [row('nacional', 0, 'GP'), row('nacional', 1, 'GSOC'), row('nacional', 3, 'GSUMAR')];
    const { inserts, updates, deletes } = diffTable(groups, desired, existing, ['nacional']);
    expect(inserts).toEqual([row('nacional', 3, 'GSUMAR')]);
    expect(updates).toEqual([{ row: row('nacional', 1, 'GSOC'), columns: ['group_name'] }]);
    expect(deletes).toEqual([row('nacional', 2, 'GCs')]);
    expect(renderUpdates(groups, updates)).toEqual([
      "UPDATE groups SET group_name = 'GSOC' WHERE scope_id = 'nacional' AND group_idx = 1;",
    ]);
  });

  it('leaves other scopes alone in a scoped sync and prunes them in a full one', () => {
    const existing = [row('nacional', 0, 'GP'), row('cyl', 0, 'Popular')];
    const desired = [row('nacional', 0, 'GP')];
    expect(diffTable(groups, desired, existing, ['nacional']).deletes).toEqual([]);
    expect(diffTable(groups, desired, existing, ['nacional'], { pruneOtherScopes: true }).deletes).toEqual([
      row('cyl', 0, 'Popular'),
    ]);
  });

  it('treats undefined and null as the same value', () => {
    const diputados = TABLES.find((t) => t.name === 'diputados');
    const base = Object.fromEntries(diputados.columns.map((c) => [c, null]));
    const desired = [{ ...base, scope_id: 'nacional', dip_idx: 0, loyalty: undefined }];
    const existing = [{ ...base, scope_id: 'nacional', dip_idx: 0 }];
    expect(diffTable(diputados, desired, existing, ['nacional']).updates).toEqual([]);
  });

  it('renders upserts and deletes as SQL', () => {
    const [upsert] = renderUpserts(groups, [row('nacional', 1, "L'Hospitalet")]);
    expect(upsert).toContain("('nacional', 1, 'L''Hospitalet')");
    expect(upsert).toContain('ON CONFLICT(scope_id, group_idx) DO UPDATE SET group_name = excluded.group_name;');
    expect(renderDeletes(groups, [row('cyl', 2, 'x')])).toEqual([
      "DELETE FROM groups WHERE scope_id = 'cyl' AND group_idx = 2;",
    ]);
  });

  it('renders SQL literals', () => {
    expect(sqlLiteral(null)).toBe('NULL');
    expect(sqlLiteral(undefined)).toBe('NULL');
    expect(sqlLiteral(0.5)).toBe('0.5');
    expect(sqlLiteral(Number.NaN)).toBe('NULL');
    expect(sqlLiteral("O'Neil")).toBe("'O''Neil'");
  });
});
