#!/usr/bin/env node
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..', '..')
const rawRoot = path.join(projectRoot, 'data', 'madrid')
const publicRoot = path.join(projectRoot, 'public', 'data', 'madrid')
const legs = ['XIII', 'XII', 'XI', 'X']
const unknownGroupTokens = new Set(['', 'unknown', 'desconocido', 'null', 'none', 'n/a', 'na'])

function parseArgs() {
  const args = {
    markdownOut: process.env.MADRID_QA_REPORT_MD || '',
    jsonOut: process.env.MADRID_QA_REPORT_JSON || '',
    failOnThresholds: String(process.env.MADRID_QA_FAIL_ON_THRESHOLDS || '').toLowerCase() === 'true',
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
    } else if (token === '--fail-on-thresholds') {
      args.failOnThresholds = true
    }
  }
  return args
}

async function readJson(filePath, fallback) {
  try {
    const raw = await fs.readFile(filePath, 'utf8')
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function toInt(value) {
  const parsed = Number.parseInt(String(value ?? 0), 10)
  return Number.isFinite(parsed) ? parsed : 0
}

function isUnknownGroup(groupName) {
  return unknownGroupTokens.has(String(groupName ?? '').trim().toLowerCase())
}

function isGenericTitle(title) {
  const value = String(title || '').trim().toLowerCase()
  if (!value) return true
  if (value === 'asunto parlamentario sin clasificar') return true
  if (/^votaci[oó]n(?:\s+desconocida|\s+sin\s+t[íi]tulo)?$/i.test(value)) return true
  if (/^votaci[oó]n\s+sobre\s+un\s+asunto\s+parlamentario/i.test(value)) return true
  if (/^votaci[oó]n\s+de\s+tr[aá]mite(?:\s+parlamentario)?$/i.test(value)) return true
  if (/^votaci[oó]n\s+parlamentaria$/i.test(value)) return true
  if (/^votaci[oó]n\s+ordinaria$/i.test(value)) return true
  return false
}

function percent(value, total) {
  if (!total) return 0
  return Number(((value / total) * 100).toFixed(2))
}

function toMarkdown(report) {
  const lines = []
  lines.push('## Madrid data quality report')
  lines.push('')
  lines.push(`- Generated at: ${new Date().toISOString()}`)
  lines.push(`- Votes analysed: ${report.totalVotes}`)
  lines.push('')
  lines.push('| Metric | Value |')
  lines.push('|---|---:|')
  lines.push(`| Generic titles | ${report.genericTitles.count} (${report.genericTitles.percent}%) |`)
  lines.push(`| Votes without nominal assignment | ${report.votesWithoutNominal.count} (${report.votesWithoutNominal.percent}%) |`)
  lines.push(`| Votes with group inference only | ${report.groupInferenceOnly.count} (${report.groupInferenceOnly.percent}%) |`)
  lines.push(`| Unknown groups in meta | ${report.unknownGroupsMeta.count}/${report.unknownGroupsMeta.total} (${report.unknownGroupsMeta.percent}%) |`)
  lines.push(`| Unknown groups in group_majority | ${report.unknownGroupsGroupMajority.count}/${report.unknownGroupsGroupMajority.total} (${report.unknownGroupsGroupMajority.percent}%) |`)
  lines.push(`| Raw totals vs transformed mismatch | ${report.rawTotalsMismatch.count}/${report.rawTotalsMismatch.total} (${report.rawTotalsMismatch.percent}%) |`)
  if (report.rawTotalsMismatch.missingRaw > 0) {
    lines.push(`| Votes missing raw reference | ${report.rawTotalsMismatch.missingRaw} |`)
  }
  lines.push('')
  lines.push('Thresholds:')
  lines.push('- Generic titles target: < 2%')
  lines.push('- Unknown groups target: < 1%')
  lines.push('')
  return lines.join('\n')
}

async function buildReport() {
  const rawVotesById = new Map()
  for (const leg of legs) {
    const rawVotes = await readJson(path.join(rawRoot, `votos_${leg}_raw.json`), [])
    for (const vote of rawVotes) {
      if (vote?.id) rawVotesById.set(vote.id, vote)
    }
  }

  const meta = await readJson(path.join(publicRoot, 'votaciones_meta.json'), null)
  if (!meta || !Array.isArray(meta.votaciones) || !Array.isArray(meta.votResults)) {
    throw new Error('public/data/madrid/votaciones_meta.json no tiene formato válido.')
  }

  const tuplesByVote = new Map()
  const detailsByLeg = {}
  for (const leg of legs) {
    const payload = await readJson(path.join(publicRoot, `votos_${leg}.json`), { votos: [], detail: {} })
    detailsByLeg[leg] = payload?.detail || {}
    for (const tuple of payload?.votos || []) {
      if (!Array.isArray(tuple) || tuple.length < 4) continue
      const voteIdx = Number(tuple[0])
      const code = Number(tuple[3])
      if (!Number.isInteger(voteIdx)) continue
      if (!tuplesByVote.has(voteIdx)) {
        tuplesByVote.set(voteIdx, { nominal: 0, any: 0 })
      }
      const entry = tuplesByVote.get(voteIdx)
      entry.any += 1
      if ([1, 2, 3].includes(code)) entry.nominal += 1
    }
  }

  const totalVotes = meta.votaciones.length
  let genericTitles = 0
  let votesWithoutNominal = 0
  let groupInferenceOnly = 0
  let totalsMismatch = 0
  let missingRaw = 0
  let unknownGroupMajority = 0
  let totalGroupMajority = 0

  for (let idx = 0; idx < meta.votaciones.length; idx += 1) {
    const vote = meta.votaciones[idx]
    const voteId = vote?.id
    const leg = vote?.legislatura
    if (isGenericTitle(vote?.titulo_ciudadano)) genericTitles += 1

    const tupleInfo = tuplesByVote.get(idx) || { nominal: 0, any: 0 }
    if (tupleInfo.nominal === 0) votesWithoutNominal += 1

    const rawVote = voteId ? rawVotesById.get(voteId) : null
    if (rawVote?.group_votes && Object.keys(rawVote.group_votes).length > 0 && tupleInfo.nominal === 0) {
      groupInferenceOnly += 1
    }

    const detail = detailsByLeg[leg]?.[String(idx)] || {}
    const groupMajority = detail.group_majority || {}
    for (const groupName of Object.keys(groupMajority)) {
      totalGroupMajority += 1
      if (isUnknownGroup(groupName)) unknownGroupMajority += 1
    }

    if (!rawVote) {
      missingRaw += 1
      continue
    }
    const rawTotals = rawVote.totales || {}
    const transformed = meta.votResults[idx] || {}
    const mismatch =
      toInt(rawTotals.favor) !== toInt(transformed.favor) ||
      toInt(rawTotals.contra) !== toInt(transformed.contra) ||
      toInt(rawTotals.abstencion) !== toInt(transformed.abstencion) ||
      toInt(rawTotals.total) !== toInt(transformed.total)
    if (mismatch) totalsMismatch += 1
  }

  const unknownGroupsMetaCount = (meta.grupos || []).filter((group) => isUnknownGroup(group)).length
  const unknownGroupsMetaTotal = Array.isArray(meta.grupos) ? meta.grupos.length : 0

  return {
    totalVotes,
    genericTitles: {
      count: genericTitles,
      percent: percent(genericTitles, totalVotes),
    },
    votesWithoutNominal: {
      count: votesWithoutNominal,
      percent: percent(votesWithoutNominal, totalVotes),
    },
    groupInferenceOnly: {
      count: groupInferenceOnly,
      percent: percent(groupInferenceOnly, totalVotes),
    },
    unknownGroupsMeta: {
      count: unknownGroupsMetaCount,
      total: unknownGroupsMetaTotal,
      percent: percent(unknownGroupsMetaCount, unknownGroupsMetaTotal),
    },
    unknownGroupsGroupMajority: {
      count: unknownGroupMajority,
      total: totalGroupMajority,
      percent: percent(unknownGroupMajority, totalGroupMajority),
    },
    rawTotalsMismatch: {
      count: totalsMismatch,
      total: totalVotes - missingRaw,
      missingRaw,
      percent: percent(totalsMismatch, totalVotes - missingRaw),
    },
  }
}

async function writeOutput(filePath, content) {
  if (!filePath) return
  const absolute = path.isAbsolute(filePath) ? filePath : path.join(projectRoot, filePath)
  await fs.mkdir(path.dirname(absolute), { recursive: true })
  await fs.writeFile(absolute, content, 'utf8')
}

async function main() {
  const args = parseArgs()
  const report = await buildReport()
  const markdown = toMarkdown(report)

  await writeOutput(args.markdownOut, `${markdown}\n`)
  await writeOutput(args.jsonOut, `${JSON.stringify(report, null, 2)}\n`)

  process.stdout.write(`${markdown}\n`)

  if (process.env.GITHUB_STEP_SUMMARY) {
    await fs.appendFile(process.env.GITHUB_STEP_SUMMARY, `${markdown}\n\n`, 'utf8')
  }

  if (!args.failOnThresholds) return

  const fails = []
  if (report.genericTitles.percent >= 2) {
    fails.push(`Generic titles ${report.genericTitles.percent}% >= 2%`)
  }
  if (report.unknownGroupsGroupMajority.percent >= 1) {
    fails.push(`Unknown groups in group_majority ${report.unknownGroupsGroupMajority.percent}% >= 1%`)
  }
  if (report.rawTotalsMismatch.count > 0) {
    fails.push(`Raw totals mismatch count ${report.rawTotalsMismatch.count} > 0`)
  }
  if (fails.length > 0) {
    throw new Error(`Madrid QA thresholds failed: ${fails.join('; ')}`)
  }
}

await main()
