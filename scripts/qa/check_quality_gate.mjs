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
    scope: process.env.DATA_AUDIT_SCOPE || 'cyl',
    maxGenericTitlesPct: Number(process.env.QUALITY_MAX_GENERIC_TITLES_PCT || 12),
    maxUnknownGroupsPct: Number(process.env.QUALITY_MAX_UNKNOWN_GROUPS_PCT || 1),
    maxRawMismatchPct: Number(process.env.QUALITY_MAX_RAW_MISMATCH_PCT || 3),
    maxEmptySummaryPct: Number(process.env.QUALITY_MAX_EMPTY_SUMMARY_PCT || 3),
    maxDateAnomaliesPct: Number(process.env.QUALITY_MAX_DATE_ANOMALIES_PCT || 0),
  }

  const input = process.argv.slice(2)
  for (let i = 0; i < input.length; i += 1) {
    const token = input[i]
    if (token === '--audit' && input[i + 1]) {
      args.auditPath = input[i + 1]
      i += 1
    } else if (token === '--scope' && input[i + 1]) {
      args.scope = input[i + 1]
      i += 1
    } else if (token === '--max-generic' && input[i + 1]) {
      args.maxGenericTitlesPct = Number(input[i + 1])
      i += 1
    } else if (token === '--max-unknown' && input[i + 1]) {
      args.maxUnknownGroupsPct = Number(input[i + 1])
      i += 1
    } else if (token === '--max-raw-mismatch' && input[i + 1]) {
      args.maxRawMismatchPct = Number(input[i + 1])
      i += 1
    } else if (token === '--max-empty-summary' && input[i + 1]) {
      args.maxEmptySummaryPct = Number(input[i + 1])
      i += 1
    } else if (token === '--max-date-anomalies' && input[i + 1]) {
      args.maxDateAnomaliesPct = Number(input[i + 1])
      i += 1
    }
  }

  return args
}

function percent(metric) {
  return Number(metric?.percent || 0)
}

function checkThreshold({ name, value, max, failures }) {
  const ok = Number(value) <= Number(max)
  const detail = `${name}: ${value.toFixed(2)}% (max ${max.toFixed(2)}%)`
  if (ok) {
    console.log(`OK    ${detail}`)
  } else {
    console.error(`FAIL  ${detail}`)
    failures.push(detail)
  }
}

async function main() {
  const args = parseArgs()
  const auditPath = path.isAbsolute(args.auditPath) ? args.auditPath : path.join(projectRoot, args.auditPath)
  const raw = await fs.readFile(auditPath, 'utf8')
  const report = JSON.parse(raw)
  const scopeId = String(args.scope || '').trim().toLowerCase()
  const scope = (report.scopes || []).find((entry) => String(entry.scope || '').toLowerCase() === scopeId)

  if (!scope) {
    throw new Error(`Scope no encontrado en auditoría: ${scopeId}`)
  }
  if (scope.error) {
    throw new Error(`Scope ${scopeId} con error de auditoría: ${scope.error}`)
  }

  const m = scope.metrics || {}
  const unknownGroupsPct = Math.max(percent(m.unknownGroupsMeta), percent(m.unknownGroupsGroupMajority))
  const failures = []

  console.log(`Quality gate para scope="${scopeId}"`)
  console.log(`Votes: ${scope.votes}`)
  checkThreshold({
    name: 'generic_titles',
    value: percent(m.genericTitles),
    max: args.maxGenericTitlesPct,
    failures,
  })
  checkThreshold({
    name: 'unknown_groups',
    value: unknownGroupsPct,
    max: args.maxUnknownGroupsPct,
    failures,
  })
  checkThreshold({
    name: 'raw_totals_mismatch',
    value: percent(m.rawTotalsMismatch),
    max: args.maxRawMismatchPct,
    failures,
  })
  checkThreshold({
    name: 'empty_summary',
    value: percent(m.emptySummary),
    max: args.maxEmptySummaryPct,
    failures,
  })
  checkThreshold({
    name: 'date_anomalies',
    value: percent(m.dateAnomalies),
    max: args.maxDateAnomaliesPct,
    failures,
  })

  if (failures.length > 0) {
    console.error(`\nQuality gate FAILED (${failures.length} umbrales superados).`)
    process.exit(1)
  }

  console.log('\nQuality gate OK.')
}

await main()
