#!/usr/bin/env node
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..', '..')

function parseArgs() {
  const args = {
    auditPath: process.env.DATA_AUDIT_JSON || 'artifacts/data-audit.json',
    outDir: process.env.DATA_QUALITY_OUT_DIR || 'public/data',
    scopes: process.env.DATA_AUDIT_SCOPES || '',
  }
  const input = process.argv.slice(2)
  for (let i = 0; i < input.length; i += 1) {
    const token = input[i]
    if (token === '--audit' && input[i + 1]) {
      args.auditPath = input[i + 1]
      i += 1
    } else if (token === '--out-dir' && input[i + 1]) {
      args.outDir = input[i + 1]
      i += 1
    } else if (token === '--scopes' && input[i + 1]) {
      args.scopes = input[i + 1]
      i += 1
    }
  }
  return args
}

function parseScopeFilter(scopesArg) {
  const values = String(scopesArg || '')
    .split(',')
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean)
  if (!values.length) return null
  return new Set(values)
}

function round(value, digits = 2) {
  return Number(Number(value || 0).toFixed(digits))
}

function normalizeMetricPercent(metric) {
  return Number(metric?.percent || 0)
}

function buildIncidents(scope) {
  const m = scope.metrics || {}
  const incidents = []

  const genericTitlesPct = normalizeMetricPercent(m.genericTitles)
  const unknownGroupsPct = Math.max(
    normalizeMetricPercent(m.unknownGroupsMeta),
    normalizeMetricPercent(m.unknownGroupsGroupMajority),
  )
  const dateAnomaliesPct = normalizeMetricPercent(m.dateAnomalies)
  const rawMismatchPct = normalizeMetricPercent(m.rawTotalsMismatch)
  const emptySummaryPct = normalizeMetricPercent(m.emptySummary)
  const withoutNominalPct = normalizeMetricPercent(m.votesWithoutNominalDetail)
  const nominalCoveragePct = normalizeMetricPercent(m.votesWithAnyTuples)

  if (dateAnomaliesPct > 0) {
    incidents.push({
      id: 'date_anomalies',
      severity: 'high',
      message: `${m.dateAnomalies.count} votaciones con fecha anómala.`,
    })
  }

  if (unknownGroupsPct > 0.5) {
    incidents.push({
      id: 'unknown_groups',
      severity: unknownGroupsPct > 2 ? 'high' : 'medium',
      message: `Grupos desconocidos por encima del umbral (${round(unknownGroupsPct)}%).`,
    })
  }

  if (rawMismatchPct > 1.5) {
    incidents.push({
      id: 'raw_totals_mismatch',
      severity: rawMismatchPct > 4 ? 'high' : 'medium',
      message: `Diferencias entre totales raw y frontend (${round(rawMismatchPct)}%).`,
    })
  }

  if (genericTitlesPct > 8) {
    incidents.push({
      id: 'generic_titles',
      severity: genericTitlesPct > 15 ? 'high' : 'medium',
      message: `Títulos genéricos elevados (${round(genericTitlesPct)}%).`,
    })
  }

  if (emptySummaryPct > 2) {
    incidents.push({
      id: 'empty_summary',
      severity: emptySummaryPct > 8 ? 'high' : 'medium',
      message: `Resúmenes vacíos por encima del umbral (${round(emptySummaryPct)}%).`,
    })
  }

  if (withoutNominalPct > 80) {
    incidents.push({
      id: 'limited_nominal_coverage',
      severity: 'info',
      message: `Cobertura nominal limitada (${round(nominalCoveragePct)}% con detalle nominal).`,
    })
  }

  return incidents
}

function computeScore(scope) {
  const m = scope.metrics || {}
  const penalties = [
    normalizeMetricPercent(m.genericTitles) * 1.2,
    normalizeMetricPercent(m.dateAnomalies) * 5,
    normalizeMetricPercent(m.rawTotalsMismatch) * 2.2,
    Math.max(
      normalizeMetricPercent(m.unknownGroupsMeta),
      normalizeMetricPercent(m.unknownGroupsGroupMajority),
    ) * 3.2,
    normalizeMetricPercent(m.emptySummary) * 0.8,
  ]
  const score = 100 - penalties.reduce((sum, value) => sum + value, 0)
  return Math.max(0, Math.min(100, round(score, 1)))
}

function computeStatus(score, incidents) {
  const hasHigh = incidents.some((incident) => incident.severity === 'high')
  const hasMedium = incidents.some((incident) => incident.severity === 'medium')
  if (hasHigh || score < 70) return 'critical'
  if (hasMedium || score < 85) return 'warn'
  return 'ok'
}

function summaryLabel(status) {
  if (status === 'ok') return 'Calidad de datos estable'
  if (status === 'warn') return 'Calidad de datos con incidencias menores'
  return 'Calidad de datos con incidencias relevantes'
}

function scopeFileDir(baseOutDir, scopeId) {
  return scopeId === 'nacional' ? baseOutDir : path.join(baseOutDir, scopeId)
}

async function writeJson(filePath, payload) {
  await fs.mkdir(path.dirname(filePath), { recursive: true })
  await fs.writeFile(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
}

async function main() {
  const args = parseArgs()
  const scopeFilter = parseScopeFilter(args.scopes)
  const auditPath = path.isAbsolute(args.auditPath) ? args.auditPath : path.join(projectRoot, args.auditPath)
  const outDir = path.isAbsolute(args.outDir) ? args.outDir : path.join(projectRoot, args.outDir)

  const audit = JSON.parse(await fs.readFile(auditPath, 'utf8'))
  const scopes = Array.isArray(audit?.scopes) ? audit.scopes : []

  const output = {
    generatedAt: new Date().toISOString(),
    scopes: [],
  }

  for (const scope of scopes) {
    const scopeId = String(scope?.scope || '').toLowerCase()
    if (!scopeId) continue
    if (scopeFilter && !scopeFilter.has(scopeId)) continue
    if (scope.error) continue

    const incidents = buildIncidents(scope)
    const score = computeScore(scope)
    const status = computeStatus(score, incidents)
    const payload = {
      scope: scopeId,
      generatedAt: output.generatedAt,
      status,
      score,
      summary: summaryLabel(status),
      votes: Number(scope.votes || 0),
      metrics: {
        genericTitlesPct: round(scope.metrics?.genericTitles?.percent),
        unknownGroupsPct: round(
          Math.max(
            Number(scope.metrics?.unknownGroupsMeta?.percent || 0),
            Number(scope.metrics?.unknownGroupsGroupMajority?.percent || 0),
          ),
        ),
        dateAnomaliesPct: round(scope.metrics?.dateAnomalies?.percent),
        rawTotalsMismatchPct: round(scope.metrics?.rawTotalsMismatch?.percent),
        emptySummaryPct: round(scope.metrics?.emptySummary?.percent),
        nominalCoveragePct: round(scope.metrics?.votesWithAnyTuples?.percent),
        votesWithoutNominalDetailPct: round(scope.metrics?.votesWithoutNominalDetail?.percent),
      },
      incidents,
    }

    const filePath = path.join(scopeFileDir(outDir, scopeId), 'quality_status.json')
    await writeJson(filePath, payload)
    output.scopes.push({
      scope: scopeId,
      status: payload.status,
      score: payload.score,
      incidents: incidents.length,
      file: path.relative(projectRoot, filePath),
    })
  }

  const indexPath = path.join(outDir, 'quality_status_index.json')
  await writeJson(indexPath, output)
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`)
}

await main()
