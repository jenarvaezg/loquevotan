#!/usr/bin/env node
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..', '..')
const unknownGroupTokens = new Set(['', 'unknown', 'desconocido', 'null', 'none', 'n/a', 'na'])

const genericTitlePatterns = [
  /^asunto parlamentario sin clasificar$/i,
  /^votaci[oó]n(?:\s+desconocida|\s+sin\s+t[íi]tulo)?$/i,
  /^votaci[oó]n\s+sobre\s+un\s+asunto/i,
  /^votaci[oó]n\s+de\s+tr[aá]mite/i,
  /^votaci[oó]n\s+parlamentaria$/i,
  /^votaci[oó]n\s+ordinaria$/i,
  /^\(?pausa\.?\)?\s*el$/i,
  /^votaci[oó]n\s+de\s+la$/i,
]

const expedientePatterns = [
  /\b\d{1,2}-\d+\/[a-z]+-\d+\b/i,
  /\b(?:PNL|PNLP|PCOP|PL)\s*-?\s*\d+\/?\d*\b/i,
  /\bEXP\.?\s*\d+/i,
  /\b\d+\/\d{2,4}\b/,
]

function parseArgs() {
  const args = {
    markdownOut: process.env.DATA_AUDIT_MD || 'docs/data_audit.md',
    jsonOut: process.env.DATA_AUDIT_JSON || 'artifacts/data-audit.json',
  }
  const input = process.argv.slice(2)
  for (let i = 0; i < input.length; i += 1) {
    const token = input[i]
    if (token === '--markdown-out' && input[i + 1]) {
      args.markdownOut = input[i + 1]
      i += 1
    } else if (token === '--json-out' && input[i + 1]) {
      args.jsonOut = input[i + 1]
      i += 1
    }
  }
  return args
}

async function readJson(filePath, fallback = null) {
  try {
    const raw = await fs.readFile(filePath, 'utf8')
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

async function ensureDir(filePath) {
  const absolute = path.isAbsolute(filePath) ? filePath : path.join(projectRoot, filePath)
  await fs.mkdir(path.dirname(absolute), { recursive: true })
  return absolute
}

function words(text) {
  return String(text || '').trim().split(/\s+/).filter(Boolean).length
}

function toPercent(count, total) {
  if (!total) return 0
  return Number(((count / total) * 100).toFixed(2))
}

function isUnknownGroup(groupName) {
  return unknownGroupTokens.has(String(groupName || '').trim().toLowerCase())
}

function isGenericTitle(title) {
  const normalized = String(title || '').trim()
  if (!normalized) return true
  return genericTitlePatterns.some((pattern) => pattern.test(normalized))
}

function isExpedienteLike(title) {
  const normalized = String(title || '').trim()
  if (!normalized) return false
  return expedientePatterns.some((pattern) => pattern.test(normalized))
}

function isGenericSummary(summary) {
  const normalized = String(summary || '').trim()
  if (!normalized) return true
  return /^votaci[oó]n\s+(?:nominal|en|de)/i.test(normalized) || /^asunto parlamentario/i.test(normalized)
}

function defaultScopePaths(scopeId) {
  if (scopeId === 'nacional') {
    return {
      publicBase: path.join(projectRoot, 'public', 'data'),
      rawBase: path.join(projectRoot, 'data'),
      cachePath: path.join(projectRoot, 'data', 'cache_categorias.json'),
    }
  }
  return {
    publicBase: path.join(projectRoot, 'public', 'data', scopeId),
    rawBase: path.join(projectRoot, 'data', scopeId),
    cachePath: path.join(projectRoot, 'data', scopeId, 'cache_categorias.json'),
  }
}

async function loadRawVotes(scopeId, legislaturas) {
  if (scopeId === 'nacional') return new Map()

  const rawById = new Map()
  for (const leg of legislaturas || []) {
    const rawFile = path.join(projectRoot, 'data', scopeId, `votos_${leg}_raw.json`)
    const payload = await readJson(rawFile, [])
    for (const vote of payload || []) {
      if (vote?.id) rawById.set(vote.id, vote)
    }
  }
  return rawById
}

async function auditScope(scope) {
  const scopeId = scope.id
  const { publicBase, cachePath } = defaultScopePaths(scopeId)
  const meta = await readJson(path.join(publicBase, 'votaciones_meta.json'), null)
  if (!meta) {
    return {
      scope: scopeId,
      error: 'missing_votaciones_meta',
    }
  }

  const rawVotesById = await loadRawVotes(scopeId, scope.legislaturas || [])
  const cache = await readJson(cachePath, {})
  const cacheKeys = new Set(Object.keys(cache || {}))

  const votes = Array.isArray(meta.votaciones) ? meta.votaciones : []
  const results = Array.isArray(meta.votResults) ? meta.votResults : []
  const categories = Array.isArray(meta.categorias) ? meta.categorias : []
  const otrosIdx = categories.indexOf('Otros')
  const groups = Array.isArray(meta.grupos) ? meta.grupos : []

  const detailsByLeg = {}
  for (const leg of scope.legislaturas || []) {
    const payload = await readJson(path.join(publicBase, `votos_${leg}.json`), { votos: [], detail: {} })
    detailsByLeg[leg] = payload?.detail || {}
  }

  const tupleNominalByVote = new Map()
  const tupleAnyByVote = new Map()
  let detailMissingEntries = 0
  let groupMajorityUnknown = 0
  let groupMajorityTotal = 0

  for (const leg of scope.legislaturas || []) {
    const payload = await readJson(path.join(publicBase, `votos_${leg}.json`), { votos: [], detail: {} })
    const tuples = payload?.votos || []
    const detail = payload?.detail || {}

    for (const tuple of tuples) {
      if (!Array.isArray(tuple) || tuple.length < 4) continue
      const voteIdx = Number(tuple[0])
      const code = Number(tuple[3])
      tupleAnyByVote.set(voteIdx, (tupleAnyByVote.get(voteIdx) || 0) + 1)
      if ([1, 2, 3].includes(code)) {
        tupleNominalByVote.set(voteIdx, (tupleNominalByVote.get(voteIdx) || 0) + 1)
      }
    }

    for (let idx = 0; idx < votes.length; idx += 1) {
      if (votes[idx]?.legislatura !== leg) continue
      const entry = detail[String(idx)]
      if (!entry) {
        detailMissingEntries += 1
        continue
      }
      const gm = entry.group_majority || {}
      for (const groupName of Object.keys(gm)) {
        groupMajorityTotal += 1
        if (isUnknownGroup(groupName)) groupMajorityUnknown += 1
      }
    }
  }

  let genericTitles = 0
  let expedienteTitles = 0
  let shortTitles = 0
  let titlesOver12Words = 0
  let othersCategory = 0
  let noProponente = 0
  let emptySummary = 0
  let genericSummary = 0
  let totalsMismatch = 0
  let totalsMissingRaw = 0

  const aiRecatCandidates = []
  const aiRetitleCandidates = []
  const aiSummaryCandidates = []
  const genericTitleExamples = []
  const longTitleExamples = []

  for (let idx = 0; idx < votes.length; idx += 1) {
    const vote = votes[idx] || {}
    const title = String(vote.titulo_ciudadano || '').trim()
    const titleWords = words(title)
    const isGeneric = isGenericTitle(title)
    const isInformative = !isGeneric && titleWords >= 4

    if (isGeneric) {
      genericTitles += 1
      if (genericTitleExamples.length < 12) genericTitleExamples.push({ id: vote.id, title })
    }
    if (isExpedienteLike(title)) expedienteTitles += 1
    if (titleWords <= 3) shortTitles += 1
    if (titleWords > 12) {
      titlesOver12Words += 1
      if (longTitleExamples.length < 12) longTitleExamples.push({ id: vote.id, title })
    }
    if (vote.categoria === otrosIdx) othersCategory += 1

    if ('proponente' in vote) {
      const prop = String(vote.proponente || '').trim()
      if (!prop || /^desconocido$/i.test(prop)) noProponente += 1
    }

    const detail = (detailsByLeg[vote.legislatura] || {})[String(idx)] || {}
    const summary = String(detail.resumen || '').trim()
    if (!summary) emptySummary += 1
    if (isGenericSummary(summary)) genericSummary += 1

    const result = results[idx] || {}
    if (scopeId !== 'nacional') {
      const raw = rawVotesById.get(vote.id)
      if (!raw?.totales) {
        totalsMissingRaw += 1
      } else {
        const mismatch =
          Number(raw.totales.favor || 0) !== Number(result.favor || 0) ||
          Number(raw.totales.contra || 0) !== Number(result.contra || 0) ||
          Number(raw.totales.abstencion || 0) !== Number(result.abstencion || 0)
        if (mismatch) totalsMismatch += 1
      }
    }

    if (vote.categoria === otrosIdx && isInformative) {
      aiRecatCandidates.push({ id: vote.id, title })
    }
    if (isGeneric || titleWords > 26) {
      aiRetitleCandidates.push({ id: vote.id, title })
    }
    if (isGenericSummary(summary)) {
      aiSummaryCandidates.push({ id: vote.id, title, summary })
    }
  }

  const uniqueVoteTitles = new Set(votes.map((vote) => String(vote.titulo_ciudadano || '').trim()).filter(Boolean))
  const unknownGroupsMeta = groups.filter((groupName) => isUnknownGroup(groupName)).length

  let uncachedRawTitles = []
  if (scopeId !== 'nacional' && rawVotesById.size > 0) {
    uncachedRawTitles = [...rawVotesById.values()]
      .map((vote) => String(vote.titulo || '').trim())
      .filter((title) => title && !cacheKeys.has(title))
  }
  const uniqueUncachedRawTitles = [...new Set(uncachedRawTitles)]

  return {
    scope: scopeId,
    votes: votes.length,
    diputados: Array.isArray(meta.diputados) ? meta.diputados.length : 0,
    grupos: groups.length,
    uniqueVoteTitles: uniqueVoteTitles.size,
    cacheEntries: Object.keys(cache || {}).length,
    uncachedRawTitles: uniqueUncachedRawTitles.length,
    metrics: {
      genericTitles: { count: genericTitles, percent: toPercent(genericTitles, votes.length) },
      expedienteTitles: { count: expedienteTitles, percent: toPercent(expedienteTitles, votes.length) },
      shortTitles: { count: shortTitles, percent: toPercent(shortTitles, votes.length) },
      titlesOver12Words: { count: titlesOver12Words, percent: toPercent(titlesOver12Words, votes.length) },
      categoryOtros: { count: othersCategory, percent: toPercent(othersCategory, votes.length) },
      votesWithNominal: { count: [...tupleNominalByVote.keys()].length, percent: toPercent([...tupleNominalByVote.keys()].length, votes.length) },
      votesWithAnyTuples: { count: [...tupleAnyByVote.keys()].length, percent: toPercent([...tupleAnyByVote.keys()].length, votes.length) },
      unknownGroupsMeta: { count: unknownGroupsMeta, total: groups.length, percent: toPercent(unknownGroupsMeta, groups.length) },
      unknownGroupsGroupMajority: {
        count: groupMajorityUnknown,
        total: groupMajorityTotal,
        percent: toPercent(groupMajorityUnknown, groupMajorityTotal),
      },
      detailMissingEntries: { count: detailMissingEntries, percent: toPercent(detailMissingEntries, votes.length) },
      emptySummary: { count: emptySummary, percent: toPercent(emptySummary, votes.length) },
      genericSummary: { count: genericSummary, percent: toPercent(genericSummary, votes.length) },
      noProponente: { count: noProponente, percent: toPercent(noProponente, votes.length) },
      rawTotalsMismatch: {
        count: totalsMismatch,
        total: votes.length - totalsMissingRaw,
        missingRaw: totalsMissingRaw,
        percent: toPercent(totalsMismatch, votes.length - totalsMissingRaw),
      },
    },
    aiCandidates: {
      recategorize: { count: aiRecatCandidates.length, sample: aiRecatCandidates.slice(0, 12) },
      retitle: { count: aiRetitleCandidates.length, sample: aiRetitleCandidates.slice(0, 12) },
      summary: { count: aiSummaryCandidates.length, sample: aiSummaryCandidates.slice(0, 12) },
    },
    examples: {
      genericTitles: genericTitleExamples,
      longTitles: longTitleExamples,
    },
  }
}

function markdownRow(scope, m) {
  return `| ${scope.scope} | ${scope.votes} | ${m.genericTitles.percent}% | ${m.categoryOtros.percent}% | ${m.votesWithNominal.percent}% | ${m.emptySummary.percent}% | ${m.rawTotalsMismatch.percent}% | ${scope.aiCandidates.retitle.count} | ${scope.aiCandidates.recategorize.count} | ${scope.aiCandidates.summary.count} |`
}

function buildMarkdown(report) {
  const lines = []
  lines.push('# Data Quality Audit')
  lines.push('')
  lines.push(`Generated: ${new Date().toISOString()}`)
  lines.push('')
  lines.push('## Scope Summary')
  lines.push('')
  lines.push('| Scope | Votes | Generic titles | Categoria Otros | Nominal coverage | Empty summary | Raw totals mismatch | AI retitle | AI recategorize | AI summary |')
  lines.push('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
  for (const scope of report.scopes) {
    if (scope.error) continue
    lines.push(markdownRow(scope, scope.metrics))
  }
  lines.push('')

  lines.push('## Findings')
  lines.push('')
  for (const scope of report.scopes) {
    if (scope.error) {
      lines.push(`- \`${scope.scope}\`: error -> ${scope.error}`)
      continue
    }
    const m = scope.metrics
    lines.push(`### ${scope.scope}`)
    lines.push(`- votes: ${scope.votes}, diputados: ${scope.diputados}, grupos: ${scope.grupos}, unique_titles: ${scope.uniqueVoteTitles}`)
    lines.push(`- generic titles: ${m.genericTitles.count} (${m.genericTitles.percent}%)`)
    lines.push(`- categoria Otros: ${m.categoryOtros.count} (${m.categoryOtros.percent}%)`)
    lines.push(`- nominal coverage: ${m.votesWithNominal.count}/${scope.votes} (${m.votesWithNominal.percent}%)`)
    lines.push(`- empty summary: ${m.emptySummary.count} (${m.emptySummary.percent}%)`)
    lines.push(`- unknown proponente: ${m.noProponente.count} (${m.noProponente.percent}%)`)
    lines.push(`- raw totals mismatch: ${m.rawTotalsMismatch.count}/${m.rawTotalsMismatch.total} (${m.rawTotalsMismatch.percent}%)`)
    lines.push(`- AI candidates -> retitle: ${scope.aiCandidates.retitle.count}, recategorize: ${scope.aiCandidates.recategorize.count}, summary: ${scope.aiCandidates.summary.count}`)
    if (scope.examples.genericTitles.length > 0) {
      lines.push('- generic title examples:')
      for (const example of scope.examples.genericTitles.slice(0, 6)) {
        lines.push(`  - ${example.id}: ${example.title}`)
      }
    }
    if (scope.examples.longTitles.length > 0) {
      lines.push('- long title examples:')
      for (const example of scope.examples.longTitles.slice(0, 4)) {
        lines.push(`  - ${example.id}: ${example.title}`)
      }
    }
    lines.push('')
  }

  return lines.join('\n')
}

async function main() {
  const args = parseArgs()
  const ambitos = await readJson(path.join(projectRoot, 'public', 'data', 'ambitos.json'), { ambitos: [] })
  const scopes = []
  for (const scope of ambitos.ambitos || []) {
    scopes.push(await auditScope(scope))
  }

  const report = {
    generatedAt: new Date().toISOString(),
    scopes,
  }

  const markdown = buildMarkdown(report)
  const markdownPath = await ensureDir(args.markdownOut)
  const jsonPath = await ensureDir(args.jsonOut)
  await fs.writeFile(markdownPath, `${markdown}\n`, 'utf8')
  await fs.writeFile(jsonPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')

  process.stdout.write(`${markdown}\n`)
}

await main()
