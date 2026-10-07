#!/usr/bin/env node
// Discards a scope's regenerated data when it would publish fewer votes per
// legislature than HEAD. Votes are never deleted upstream, so a drop means the
// inputs were incomplete (e.g. a lost raw cache), not a real change.
//
// Writes `shrunk_scopes=<csv>` to $GITHUB_OUTPUT so the workflow can fail.

import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'

const ROOT = process.cwd()
const AMBITOS = 'public/data/ambitos.json'

function git(args) {
  return execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', maxBuffer: 1024 * 1024 * 1024 })
}

function headJson(relPath) {
  try {
    return JSON.parse(git(['show', `HEAD:${relPath}`]))
  } catch {
    return null
  }
}

function workingJson(relPath) {
  try {
    return JSON.parse(fs.readFileSync(path.join(ROOT, relPath), 'utf8'))
  } catch {
    return null
  }
}

function countsByLeg(meta) {
  const counts = {}
  for (const vote of meta?.votaciones || []) {
    counts[vote.legislatura] = (counts[vote.legislatura] || 0) + 1
  }
  return counts
}

function scopeDir(scopeId) {
  return scopeId === 'nacional' ? 'public/data' : `public/data/${scopeId}`
}

function lines(output) {
  return output.split('\n').filter(Boolean)
}

function restoreScope(scopeId) {
  const dir = scopeDir(scopeId)
  if (scopeId !== 'nacional') {
    git(['checkout', 'HEAD', '--', dir])
    git(['clean', '-fdq', '--', dir])
    return
  }
  // National files sit at the top level next to the regional folders; the
  // glob magic keeps '*' from matching across '/'.
  const specs = [`:(glob)${dir}/votaciones_meta.json`, `:(glob)${dir}/manifest_home.json`, `:(glob)${dir}/votos_*.json`]
  const tracked = lines(git(['ls-files', '--', ...specs]))
  if (tracked.length) git(['checkout', 'HEAD', '--', ...tracked])
  for (const file of lines(git(['ls-files', '--others', '--exclude-standard', '--', ...specs]))) {
    fs.rmSync(path.join(ROOT, file))
  }
}

function restoreAmbitosEntries(scopeIds) {
  const head = headJson(AMBITOS)
  const working = workingJson(AMBITOS)
  if (!head || !working) return
  const headById = new Map((head.ambitos || []).map((a) => [a.id, a]))
  working.ambitos = (working.ambitos || []).map((a) => (scopeIds.includes(a.id) && headById.has(a.id) ? headById.get(a.id) : a))
  fs.writeFileSync(path.join(ROOT, AMBITOS), JSON.stringify(working, null, 2))
}

const shrunk = []
for (const scope of headJson(AMBITOS)?.ambitos || []) {
  const metaPath = `${scopeDir(scope.id)}/votaciones_meta.json`
  const before = countsByLeg(headJson(metaPath))
  const after = countsByLeg(workingJson(metaPath))
  const losses = Object.entries(before)
    .filter(([leg, count]) => (after[leg] || 0) < count)
    .map(([leg, count]) => `${leg}: ${count} -> ${after[leg] || 0}`)
  if (losses.length) shrunk.push({ id: scope.id, losses })
}

for (const { id, losses } of shrunk) {
  console.log(`::error title=${id}::Se descartan sus datos porque perdería votaciones (${losses.join(', ')}).`)
  restoreScope(id)
}
if (shrunk.length) restoreAmbitosEntries(shrunk.map((s) => s.id))
if (!shrunk.length) console.log('Ningún ámbito pierde votaciones respecto a HEAD.')

if (process.env.GITHUB_OUTPUT) {
  fs.appendFileSync(process.env.GITHUB_OUTPUT, `shrunk_scopes=${shrunk.map((s) => s.id).join(',')}\n`)
}
