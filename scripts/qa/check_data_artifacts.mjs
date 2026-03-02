import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const PROJECT_ROOT = path.resolve(__dirname, '..', '..')
const DATA_ROOT = path.join(PROJECT_ROOT, 'public', 'data')

const SOFT_SIZE_LIMIT_BYTES = 25 * 1024 * 1024
const hardLimitMb = Number.parseInt(process.env.DATA_MAX_ARTIFACT_SIZE_MB ?? '40', 10)
const HARD_SIZE_LIMIT_BYTES = hardLimitMb * 1024 * 1024

const errors = []
const warnings = []

function pushError(message) {
  errors.push(message)
  console.error(`ERROR: ${message}`)
}

function pushWarning(message) {
  warnings.push(message)
  console.warn(`WARN: ${message}`)
}

async function readJson(filePath, required = true) {
  try {
    const raw = await fs.readFile(filePath, 'utf8')
    return JSON.parse(raw)
  } catch (error) {
    if (required) {
      pushError(`${path.relative(PROJECT_ROOT, filePath)} no se pudo leer/parsear (${error.message}).`)
    }
    return null
  }
}

async function ensureFile(filePath) {
  try {
    const stat = await fs.stat(filePath)
    if (!stat.isFile()) {
      pushError(`${path.relative(PROJECT_ROOT, filePath)} no es un fichero.`)
      return false
    }
    if (stat.size > HARD_SIZE_LIMIT_BYTES) {
      pushError(
        `${path.relative(PROJECT_ROOT, filePath)} pesa ${(stat.size / 1024 / 1024).toFixed(2)} MiB y supera el límite duro de ${hardLimitMb} MiB.`,
      )
    } else if (stat.size > SOFT_SIZE_LIMIT_BYTES) {
      pushWarning(
        `${path.relative(PROJECT_ROOT, filePath)} pesa ${(stat.size / 1024 / 1024).toFixed(2)} MiB (>25 MiB). Cloudflare Workers no acepta assets de ese tamaño.`,
      )
    }
    return true
  } catch (error) {
    pushError(`${path.relative(PROJECT_ROOT, filePath)} no existe (${error.message}).`)
    return false
  }
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function validateManifest(manifest, scopeId) {
  if (!isObject(manifest)) {
    pushError(`manifest_home.json (${scopeId}) debe ser un objeto JSON.`)
    return
  }

  if (!isObject(manifest.stats)) {
    pushError(`manifest_home.json (${scopeId}) no tiene "stats" válido.`)
  } else {
    for (const key of ['diputados', 'votaciones', 'votos']) {
      if (typeof manifest.stats[key] !== 'number') {
        pushError(`manifest_home.json (${scopeId}) stats.${key} debe ser numérico.`)
      }
    }
  }

  for (const key of ['heroExamples', 'topTags', 'latestVotes', 'tightVotes']) {
    if (!Array.isArray(manifest[key])) {
      pushError(`manifest_home.json (${scopeId}) "${key}" debe ser un array.`)
    }
  }

  if ('featuredVotes' in manifest && !Array.isArray(manifest.featuredVotes)) {
    pushError(`manifest_home.json (${scopeId}) "featuredVotes" debe ser array cuando existe.`)
  }

  if (!manifest.updatedAt) {
    pushWarning(`manifest_home.json (${scopeId}) no tiene updatedAt.`)
  }
}

function validateMeta(meta, scopeId) {
  if (!isObject(meta)) {
    pushError(`votaciones_meta.json (${scopeId}) debe ser un objeto JSON.`)
    return
  }

  if (!Array.isArray(meta.votaciones)) {
    pushError(`votaciones_meta.json (${scopeId}) "votaciones" debe ser array.`)
  }
  if (!Array.isArray(meta.votResults)) {
    pushError(`votaciones_meta.json (${scopeId}) "votResults" debe ser array.`)
  }
  if (!Array.isArray(meta.categorias)) {
    pushError(`votaciones_meta.json (${scopeId}) "categorias" debe ser array.`)
  }
  if (!isObject(meta.votIdById)) {
    pushError(`votaciones_meta.json (${scopeId}) "votIdById" debe ser objeto.`)
  }

  if (Array.isArray(meta.votaciones) && Array.isArray(meta.votResults) && meta.votaciones.length !== meta.votResults.length) {
    pushError(
      `votaciones_meta.json (${scopeId}) tiene longitudes distintas: votaciones=${meta.votaciones.length}, votResults=${meta.votResults.length}.`,
    )
  }

  if (Array.isArray(meta.votaciones) && isObject(meta.votIdById)) {
    const sample = meta.votaciones.slice(0, 250)
    for (const vote of sample) {
      if (!vote?.id) {
        pushError(`votaciones_meta.json (${scopeId}) tiene una votación sin id.`)
        break
      }
      if (!(vote.id in meta.votIdById)) {
        pushError(`votaciones_meta.json (${scopeId}) votIdById no contiene "${vote.id}".`)
        break
      }
    }
  }
}

async function validateScope(scopeId, legislaturas) {
  const baseDir = scopeId === 'nacional' ? DATA_ROOT : path.join(DATA_ROOT, scopeId)

  const manifestPath = path.join(baseDir, 'manifest_home.json')
  if (await ensureFile(manifestPath)) {
    const manifest = await readJson(manifestPath)
    if (manifest) validateManifest(manifest, scopeId)
  }

  const metaPath = path.join(baseDir, 'votaciones_meta.json')
  if (await ensureFile(metaPath)) {
    const meta = await readJson(metaPath)
    if (meta) validateMeta(meta, scopeId)
  }

  for (const leg of legislaturas) {
    const votesPath = path.join(baseDir, `votos_${leg}.json`)
    const exists = await ensureFile(votesPath)
    if (!exists) continue
    await readJson(votesPath)
  }
}

async function main() {
  const ambitosPath = path.join(DATA_ROOT, 'ambitos.json')
  const ambitos = await readJson(ambitosPath)
  if (!ambitos?.ambitos || !Array.isArray(ambitos.ambitos)) {
    pushError('public/data/ambitos.json no tiene la forma esperada { ambitos: [] }.')
  } else {
    for (const scope of ambitos.ambitos) {
      await validateScope(scope.id, scope.legislaturas ?? [])
    }
  }

  if (warnings.length > 0) {
    console.log(`\nAdvertencias: ${warnings.length}`)
  }

  if (errors.length > 0) {
    console.error(`\nFallos de calidad de artefactos: ${errors.length}`)
    process.exit(1)
  }

  console.log('\nOK: estructura y tamaños de artefactos validados.')
}

await main()
