import { ref, shallowRef } from 'vue'
import { LEGISLATURAS, getLeg } from '../utils'

const loading = ref(true)
const error = ref(null)
const loaded = ref(false)

const diputados = shallowRef([])
const grupos = shallowRef([])
const categorias = shallowRef([])
const votaciones = shallowRef([])
const votos = shallowRef([])

const votosByVotacion = shallowRef({})
const votosByDiputado = shallowRef({})

const votResults = shallowRef([])
const dipStats = shallowRef([])
const tagCounts = shallowRef({})
const topTags = shallowRef([])
const sortedVotIdxByDate = shallowRef([])
const groupAffinity = shallowRef({})

let _loadPromise = null

async function _doLoad() {
  loading.value = true
  error.value = null

  try {
    const url = import.meta.env.BASE_URL + 'data/votaciones.json'
    const resp = await fetch(url)
    if (!resp.ok) throw new Error('HTTP ' + resp.status)
    const raw = await resp.json()

    const _dips = raw.diputados
    const _grupos = raw.grupos
    const _cats = raw.categorias
    const _vots = raw.votaciones
    const _v = raw.votos

    // ── Build indexes ──
    const _vbv = {}
    const _vbd = {}
    for (let i = 0; i < _v.length; i++) {
      const votIdx = _v[i][0]
      const dipIdx = _v[i][1]
      if (!_vbv[votIdx]) _vbv[votIdx] = []
      _vbv[votIdx].push(i)
      if (!_vbd[dipIdx]) _vbd[dipIdx] = []
      _vbd[dipIdx].push(i)
    }

    // ── Precompute votacion results + group majorities ──
    const groupMajority = {}
    const _votResults = new Array(_vots.length)

    for (let vi = 0; vi < _vots.length; vi++) {
      const indices = _vbv[vi] || []
      const t = { 1: 0, 2: 0, 3: 0 }
      const byGroup = {}

      for (let j = 0; j < indices.length; j++) {
        const v = _v[indices[j]]
        const code = v[3]
        const grp = v[2]
        t[code]++
        if (!byGroup[grp]) byGroup[grp] = { 1: 0, 2: 0, 3: 0 }
        byGroup[grp][code]++
      }

      const total = indices.length
      const favor = t[1]
      const contra = t[2]
      _votResults[vi] = {
        favor,
        contra,
        abstencion: t[3],
        total,
        result: favor > contra ? 'Aprobada' : contra > favor ? 'Rechazada' : 'Empate',
        margin: Math.abs(favor - contra),
      }

      groupMajority[vi] = {}
      for (const gIdx in byGroup) {
        const c = byGroup[gIdx]
        groupMajority[vi][gIdx] = c[1] >= c[2] && c[1] >= c[3] ? 1 : c[2] >= c[3] ? 2 : 3
      }

      _vots[vi] = { ..._vots[vi], legislatura: getLeg(_vots[vi].fecha) }
    }

    // ── Diputado stats + loyalty ──
    const _dipStats = new Array(_dips.length)
    for (let di = 0; di < _dips.length; di++) {
      const indices = _vbd[di] || []
      const t = { 1: 0, 2: 0, 3: 0 }
      const grupoCount = {}
      let loyal = 0

      for (let j = 0; j < indices.length; j++) {
        const v = _v[indices[j]]
        const code = v[3]
        const grp = v[2]
        t[code]++
        grupoCount[grp] = (grupoCount[grp] || 0) + 1
        const maj = groupMajority[v[0]]
        if (maj && maj[grp] === code) loyal++
      }

      const total = indices.length
      const mainGrpKeys = Object.keys(grupoCount)
      let mainGrupo = -1
      if (mainGrpKeys.length > 0) {
        mainGrupo = Number(mainGrpKeys.reduce((a, b) => grupoCount[a] >= grupoCount[b] ? a : b))
      }

      const legSet = {}
      for (let j = 0; j < indices.length; j++) {
        const leg = _vots[_v[indices[j]][0]].legislatura
        if (leg) legSet[leg] = true
      }

      _dipStats[di] = {
        favor: t[1],
        contra: t[2],
        abstencion: t[3],
        total,
        mainGrupo,
        loyalty: total > 0 ? loyal / total : 0,
        legislaturas: LEGISLATURAS.map(l => l.id).filter(id => legSet[id]),
      }
    }

    // ── Tag counts ──
    const _tagCounts = {}
    for (let i = 0; i < _vots.length; i++) {
      const tags = _vots[i].etiquetas
      if (tags) {
        for (let j = 0; j < tags.length; j++) {
          _tagCounts[tags[j]] = (_tagCounts[tags[j]] || 0) + 1
        }
      }
    }
    const _topTags = Object.entries(_tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 20)

    // ── Sorted votacion indices by date desc ──
    const _sorted = Array.from({ length: _vots.length }, (_, i) => i)
    _sorted.sort((a, b) => _vots[b].fecha.localeCompare(_vots[a].fecha))

    // ── Group affinity matrix ──
    const _ga = {}
    for (let vi = 0; vi < _vots.length; vi++) {
      const gm = groupMajority[vi]
      const gKeys = Object.keys(gm).map(Number)
      for (let a = 0; a < gKeys.length; a++) {
        for (let b = a + 1; b < gKeys.length; b++) {
          const ga = gKeys[a]
          const gb = gKeys[b]
          const key = ga < gb ? ga + ',' + gb : gb + ',' + ga
          if (!_ga[key]) _ga[key] = { same: 0, total: 0 }
          _ga[key].total++
          if (gm[ga] === gm[gb]) _ga[key].same++
        }
      }
    }

    // ── Assign all refs at once ──
    diputados.value = _dips
    grupos.value = _grupos
    categorias.value = _cats
    votaciones.value = _vots
    votos.value = _v
    votosByVotacion.value = _vbv
    votosByDiputado.value = _vbd
    votResults.value = _votResults
    dipStats.value = _dipStats
    tagCounts.value = _tagCounts
    topTags.value = _topTags
    sortedVotIdxByDate.value = _sorted
    groupAffinity.value = _ga

    loaded.value = true
  } catch (err) {
    error.value = 'Error cargando datos: ' + err.message
  } finally {
    loading.value = false
  }
}

function loadData() {
  if (!_loadPromise) _loadPromise = _doLoad()
  return _loadPromise
}

export function useData() {
  return {
    loading,
    error,
    loaded,
    loadData,
    diputados,
    grupos,
    categorias,
    votaciones,
    votos,
    votosByVotacion,
    votosByDiputado,
    votResults,
    dipStats,
    tagCounts,
    topTags,
    sortedVotIdxByDate,
    groupAffinity,
  }
}
