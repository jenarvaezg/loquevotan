#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const rootDir = process.cwd();
const dataRoot = path.join(rootDir, 'public', 'data');
const requiredMetaKeys = [
  'diputados',
  'grupos',
  'categorias',
  'votaciones',
  'votResults',
  'dipStats',
  'groupAffinityByLeg',
  'votsByExp',
  'votIdById',
  'sortedVotIdxByDate',
];

const failures = [];
let overflowFailures = 0;
const MAX_REPORTED_FAILURES = 250;

function fail(scope, message) {
  const entry = `[${scope}] ${message}`;
  if (failures.length < MAX_REPORTED_FAILURES) failures.push(entry);
  else overflowFailures += 1;
}

function readJson(filePath, scope) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (err) {
    fail(scope, `No se pudo leer ${path.relative(rootDir, filePath)}: ${err.message}`);
    return null;
  }
}

function validateMeta(scope, meta) {
  for (const key of requiredMetaKeys) {
    if (!(key in meta)) fail(scope, `Falta clave requerida en votaciones_meta.json: ${key}`);
  }

  const diputados = Array.isArray(meta.diputados) ? meta.diputados : [];
  const grupos = Array.isArray(meta.grupos) ? meta.grupos : [];
  const votaciones = Array.isArray(meta.votaciones) ? meta.votaciones : [];
  const votResults = Array.isArray(meta.votResults) ? meta.votResults : [];
  const dipStats = Array.isArray(meta.dipStats) ? meta.dipStats : [];
  const sorted = Array.isArray(meta.sortedVotIdxByDate) ? meta.sortedVotIdxByDate : [];

  if (votaciones.length !== votResults.length) {
    fail(scope, `Longitud votaciones (${votaciones.length}) != votResults (${votResults.length})`);
  }
  if (diputados.length !== dipStats.length) {
    fail(scope, `Longitud diputados (${diputados.length}) != dipStats (${dipStats.length})`);
  }

  const seenSorted = new Set();
  for (const idx of sorted) {
    if (!Number.isInteger(idx) || idx < 0 || idx >= votaciones.length) {
      fail(scope, `sortedVotIdxByDate contiene índice inválido: ${idx}`);
      continue;
    }
    if (seenSorted.has(idx)) fail(scope, `sortedVotIdxByDate contiene duplicado: ${idx}`);
    seenSorted.add(idx);
  }

  const uniqueIds = new Set();
  for (let i = 0; i < votaciones.length; i++) {
    const id = votaciones[i]?.id;
    if (!id) fail(scope, `Votación sin id estable en índice ${i}`);
    else uniqueIds.add(id);
  }

  for (const id of uniqueIds) {
    if (!(id in (meta.votIdById || {}))) {
      fail(scope, `votIdById no contiene id existente en votaciones: ${id}`);
      continue;
    }
    const idx = Number(meta.votIdById[id]);
    if (!Number.isInteger(idx) || idx < 0 || idx >= votaciones.length) {
      fail(scope, `votIdById apunta fuera de rango para id ${id}: ${meta.votIdById[id]}`);
      continue;
    }
    if (votaciones[idx]?.id !== id) {
      fail(scope, `votIdById apunta a una votación con id distinto para ${id} (idx=${idx})`);
    }
  }

  for (const [exp, indices] of Object.entries(meta.votsByExp || {})) {
    if (!Array.isArray(indices)) {
      fail(scope, `votsByExp[${exp}] no es array`);
      continue;
    }
    for (const idx of indices) {
      if (!Number.isInteger(idx) || idx < 0 || idx >= votaciones.length) {
        fail(scope, `votsByExp[${exp}] contiene índice inválido: ${idx}`);
        continue;
      }
      if (votaciones[idx]?.exp !== exp) {
        fail(scope, `votsByExp[${exp}] incluye votación ${idx} con exp=${votaciones[idx]?.exp}`);
      }
    }
  }

  for (const [leg, affinity] of Object.entries(meta.groupAffinityByLeg || {})) {
    if (typeof affinity !== 'object' || affinity === null) {
      fail(scope, `groupAffinityByLeg[${leg}] no es objeto`);
      continue;
    }
    for (const [pair, stats] of Object.entries(affinity)) {
      const parts = pair.split(',');
      if (parts.length !== 2 || !Number.isFinite(Number(parts[0])) || !Number.isFinite(Number(parts[1]))) {
        fail(scope, `Clave inválida en groupAffinityByLeg[${leg}]: ${pair}`);
      }
      const same = Number(stats?.same);
      const total = Number(stats?.total);
      if (!Number.isFinite(same) || !Number.isFinite(total) || same < 0 || total < 0 || same > total) {
        fail(scope, `Par inválido en groupAffinityByLeg[${leg}][${pair}] (same=${same}, total=${total})`);
      }
    }
  }
}

function validateVotesByLeg(scope, scopeDir, legs, meta) {
  const votaciones = meta.votaciones;
  const votResults = meta.votResults;
  const dipStats = meta.dipStats;
  const groupsLen = meta.grupos.length;
  const legsSet = new Set(legs);

  const nonNoVotaByVot = new Uint32Array(votaciones.length);
  const nonNoVotaByDip = new Uint32Array(dipStats.length);
  const noVotaByDip = new Uint32Array(dipStats.length);

  for (const leg of legs) {
    const votesFile = path.join(scopeDir, `votos_${leg}.json`);
    if (!fs.existsSync(votesFile)) {
      fail(scope, `Falta archivo requerido ${path.relative(rootDir, votesFile)}`);
      continue;
    }
    const payload = readJson(votesFile, scope);
    if (!payload) continue;
    if (!Array.isArray(payload.votos)) {
      fail(scope, `${path.relative(rootDir, votesFile)} no contiene array 'votos'`);
      continue;
    }

    for (let i = 0; i < payload.votos.length; i++) {
      const tuple = payload.votos[i];
      if (!Array.isArray(tuple) || tuple.length < 4) {
        fail(scope, `${path.relative(rootDir, votesFile)} voto inválido en posición ${i}`);
        continue;
      }

      const votIdx = Number(tuple[0]);
      const dipIdx = Number(tuple[1]);
      const grpIdx = Number(tuple[2]);
      const voteCode = Number(tuple[3]);

      if (!Number.isInteger(votIdx) || votIdx < 0 || votIdx >= votaciones.length) {
        fail(scope, `${path.relative(rootDir, votesFile)} votIdx fuera de rango (${votIdx})`);
        continue;
      }
      if (!Number.isInteger(dipIdx) || dipIdx < 0 || dipIdx >= dipStats.length) {
        fail(scope, `${path.relative(rootDir, votesFile)} dipIdx fuera de rango (${dipIdx})`);
        continue;
      }
      if (!Number.isInteger(grpIdx) || grpIdx < 0 || grpIdx >= groupsLen) {
        fail(scope, `${path.relative(rootDir, votesFile)} grpIdx fuera de rango (${grpIdx})`);
        continue;
      }
      if (![1, 2, 3, 4].includes(voteCode)) {
        fail(scope, `${path.relative(rootDir, votesFile)} código de voto inválido (${voteCode})`);
        continue;
      }

      if (voteCode === 4) noVotaByDip[dipIdx] += 1;
      else {
        nonNoVotaByVot[votIdx] += 1;
        nonNoVotaByDip[dipIdx] += 1;
      }
    }
  }

  for (let i = 0; i < votaciones.length; i++) {
    if (!legsSet.has(votaciones[i]?.legislatura)) continue;
    const expected = Number(votResults[i]?.total || 0);
    const actual = nonNoVotaByVot[i];
    // En algunos ámbitos hay votaciones sin detalle nominal completo.
    // Validamos solo coherencia cuando sí tenemos votos nominales.
    if (actual > 0 && actual !== expected) {
      fail(scope, `votResults[${i}].total=${expected} pero votos nominales no-no_vota=${actual}`);
    }
  }

  for (let i = 0; i < dipStats.length; i++) {
    const expectedTotal = Number(dipStats[i]?.total || 0);
    const expectedNoVota = Number(dipStats[i]?.no_vota || 0);
    // Verificación conservadora: nunca podemos exceder lo publicado en agregados.
    if (nonNoVotaByDip[i] > expectedTotal) {
      fail(scope, `dipStats[${i}].total=${expectedTotal} pero votos nominales no-no_vota=${nonNoVotaByDip[i]}`);
    }
    if (noVotaByDip[i] > expectedNoVota) {
      fail(scope, `dipStats[${i}].no_vota=${expectedNoVota} pero votos nominales no_vota=${noVotaByDip[i]}`);
    }
  }
}

function validateScope(scopeConfig) {
  const scopeId = scopeConfig.id;
  const scope = scopeId;
  const scopeDir = scopeId === 'nacional'
    ? dataRoot
    : path.join(dataRoot, scopeId);
  const metaPath = path.join(scopeDir, 'votaciones_meta.json');

  if (!fs.existsSync(metaPath)) {
    fail(scope, `Falta archivo ${path.relative(rootDir, metaPath)}`);
    return;
  }

  const meta = readJson(metaPath, scope);
  if (!meta) return;

  validateMeta(scope, meta);
  validateVotesByLeg(scope, scopeDir, scopeConfig.legislaturas || [], meta);
}

function run() {
  const ambitosPath = path.join(dataRoot, 'ambitos.json');
  const ambitosData = readJson(ambitosPath, 'global');
  if (!ambitosData || !Array.isArray(ambitosData.ambitos)) {
    fail('global', 'ambitos.json no contiene array ambitos');
  } else {
    for (const scope of ambitosData.ambitos) validateScope(scope);
  }

  if (failures.length) {
    console.error(`\nIntegridad de datos: ${failures.length + overflowFailures} fallo(s)\n`);
    for (const item of failures) console.error(`- ${item}`);
    if (overflowFailures > 0) {
      console.error(`- ... y ${overflowFailures} fallo(s) adicional(es) no mostrados`);
    }
    process.exit(1);
  }

  console.log('Integridad de datos OK para todos los ámbitos.');
}

run();
