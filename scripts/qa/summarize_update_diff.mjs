import fs from 'node:fs/promises'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const PROJECT_ROOT = path.resolve(__dirname, '..', '..')
const DATA_ROOT = path.join(PROJECT_ROOT, 'public', 'data')
const summaryPath = process.env.GITHUB_STEP_SUMMARY

function toSortedTagKey(tags) {
  return (Array.isArray(tags) ? [...tags] : []).sort().join('|')
}

function readJsonFromString(raw, fallback) {
  try {
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function readHeadJson(repoPath, fallback) {
  try {
    const raw = execFileSync('git', ['show', `HEAD:${repoPath}`], {
      cwd: PROJECT_ROOT,
      encoding: 'utf8',
      maxBuffer: 200 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'ignore'],
    })
    return readJsonFromString(raw, fallback)
  } catch {
    return fallback
  }
}

async function readCurrentJson(absPath, fallback) {
  try {
    const raw = await fs.readFile(absPath, 'utf8')
    return readJsonFromString(raw, fallback)
  } catch {
    return fallback
  }
}

function toVoteMap(meta) {
  const categories = Array.isArray(meta?.categorias) ? meta.categorias : []
  const votaciones = Array.isArray(meta?.votaciones) ? meta.votaciones : []
  const votResults = Array.isArray(meta?.votResults) ? meta.votResults : []
  const map = new Map()

  votaciones.forEach((vote, idx) => {
    if (!vote?.id) return
    const result = votResults[idx] ?? {}
    map.set(vote.id, {
      title: String(vote.titulo_ciudadano ?? '').trim(),
      categoryId: Number.isInteger(vote.categoria) ? vote.categoria : null,
      categoryLabel: Number.isInteger(vote.categoria) ? categories[vote.categoria] ?? null : null,
      tags: toSortedTagKey(vote.etiquetas),
      result: String(result.result ?? ''),
      favor: Number(result.favor ?? 0),
      contra: Number(result.contra ?? 0),
      abstencion: Number(result.abstencion ?? 0),
      total: Number(result.total ?? 0),
    })
  })

  return map
}

function compareMeta(previousMeta, currentMeta) {
  const previous = toVoteMap(previousMeta)
  const current = toVoteMap(currentMeta)

  let newVotes = 0
  let removedVotes = 0
  let recategorizations = 0
  let titleChanges = 0
  let sensitiveChanges = 0

  for (const [id, curr] of current.entries()) {
    const prev = previous.get(id)
    if (!prev) {
      newVotes += 1
      continue
    }

    if (prev.categoryId !== curr.categoryId || prev.tags !== curr.tags) {
      recategorizations += 1
    }
    if (prev.title !== curr.title) {
      titleChanges += 1
    }
    if (
      prev.result !== curr.result ||
      prev.favor !== curr.favor ||
      prev.contra !== curr.contra ||
      prev.abstencion !== curr.abstencion ||
      prev.total !== curr.total
    ) {
      sensitiveChanges += 1
    }
  }

  for (const id of previous.keys()) {
    if (!current.has(id)) removedVotes += 1
  }

  return { newVotes, removedVotes, recategorizations, titleChanges, sensitiveChanges }
}

async function getScopeDiff(scopeId) {
  const relativeBase = scopeId === 'nacional' ? 'public/data' : `public/data/${scopeId}`
  const relativeMetaPath = `${relativeBase}/votaciones_meta.json`
  const absoluteMetaPath = path.join(PROJECT_ROOT, relativeMetaPath)

  const previousMeta = readHeadJson(relativeMetaPath, {})
  const currentMeta = await readCurrentJson(absoluteMetaPath, {})

  return compareMeta(previousMeta, currentMeta)
}

function markdownTable(rows) {
  const header = '| Ámbito | Nuevas votaciones | Eliminadas | Recategorizadas | Título cambiado | Cambios sensibles |\n'
  const separator = '|---|---:|---:|---:|---:|---:|\n'
  const body = rows
    .map(
      (row) =>
        `| ${row.scope} | ${row.newVotes} | ${row.removedVotes} | ${row.recategorizations} | ${row.titleChanges} | ${row.sensitiveChanges} |`,
    )
    .join('\n')

  return `${header}${separator}${body}\n`
}

function aggregate(rows) {
  return rows.reduce(
    (acc, row) => ({
      newVotes: acc.newVotes + row.newVotes,
      removedVotes: acc.removedVotes + row.removedVotes,
      recategorizations: acc.recategorizations + row.recategorizations,
      titleChanges: acc.titleChanges + row.titleChanges,
      sensitiveChanges: acc.sensitiveChanges + row.sensitiveChanges,
    }),
    { newVotes: 0, removedVotes: 0, recategorizations: 0, titleChanges: 0, sensitiveChanges: 0 },
  )
}

async function main() {
  const ambitos = await readCurrentJson(path.join(DATA_ROOT, 'ambitos.json'), { ambitos: [] })
  const scopeIds = (ambitos.ambitos ?? []).map((scope) => scope.id).filter(Boolean)

  const rows = []
  for (const scopeId of scopeIds) {
    const diff = await getScopeDiff(scopeId)
    rows.push({ scope: scopeId, ...diff })
  }

  const totals = aggregate(rows)
  rows.push({ scope: '**TOTAL**', ...totals })

  let output = '## Data update diff\n\n'
  output += markdownTable(rows)
  output += '\n'

  if (totals.newVotes === 0 && totals.recategorizations === 0 && totals.titleChanges === 0 && totals.sensitiveChanges === 0 && totals.removedVotes === 0) {
    output += '_No se detectaron cambios en metadatos de votaciones._\n'
  } else {
    output += '_Resumen generado comparando `HEAD` vs árbol de trabajo antes del commit automático._\n'
  }

  process.stdout.write(output)

  if (summaryPath) {
    await fs.appendFile(summaryPath, `${output}\n`, 'utf8')
  }
}

await main()
