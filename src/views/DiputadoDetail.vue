<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, pct, debounce, normalize, dipPhotoUrl, avatarInitials, avatarStyle, VOTO_LABELS, VOTES_PER_PAGE, LEGISLATURAS, subTipoLabel, subTipoBadgeClass, votoPillClass, getGroupInfo, buildAbsoluteAppUrl } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import ShareBar from '../components/ShareBar.vue'
import Pagination from '../components/Pagination.vue'
import AccountabilityCard from '../components/AccountabilityCard.vue'
import GlossaryTooltip from '../components/GlossaryTooltip.vue'

const route = useRoute()
const router = useRouter()
const { diputados, grupos, dipStats, dipFotos, votos, votaciones, votResults, votosByDiputado, categorias, loadVotosForLeg, votosLoaded, votsByExp, globalDiputados, ambitos, currentScopeId, setScope, votacionDetail } = useData()

const dipIdx = computed(() => diputados.value.indexOf(decodeURIComponent(route.params.name)))
const name = computed(() => diputados.value[dipIdx.value])
const ds = computed(() => dipStats.value[dipIdx.value])
const groupInfo = computed(() => {
  const gName = ds.value?.mainGrupo >= 0 ? grupos.value[ds.value.mainGrupo] : 'Sin grupo'
  return getGroupInfo(gName)
})
const photoUrl = computed(() => dipPhotoUrl(dipFotos.value[dipIdx.value]))

const otherScopes = computed(() => {
  if (!name.value || !globalDiputados.value[name.value]) return [];
  const scopesForDip = globalDiputados.value[name.value];
  return ambitos.value.filter(a => a.id !== currentScopeId.value && scopesForDip.includes(a.id));
})

function navigateToScope(scopeId) {
  setScope(scopeId).then(() => {
    // Re-trigger navigation to same route but it will now render in the context of the new scope
    router.replace(`/diputado/${encodeURIComponent(name.value)}`)
  })
}

watch(() => route.query.scope, (scope) => {
  if (typeof scope !== 'string') return
  const target = scope.trim().toLowerCase()
  const knownScopes = new Set(['nacional', ...(ambitos.value || []).map(a => String(a.id || '').toLowerCase())])
  if (!knownScopes.has(target)) return
  if (!target || target === currentScopeId.value) return
  setScope(target)
}, { immediate: true })

// History filters
const histSearch = ref('')
const histVoto = ref('')
const histLeg = ref('')
const histPage = ref(1)
const activeTag = ref('')
const showAccCard = ref(false)
const accTag = ref('')
const groupByExp = ref(true)
const expandedExps = ref({})

const baseUrl = import.meta.env.BASE_URL

const shareUrl = computed(() => {
  if (!name.value) return ''
  const scopeId = encodeURIComponent(currentScopeId.value || 'nacional')
  const dipName = encodeURIComponent(name.value)
  return buildAbsoluteAppUrl(`share/diputado/${scopeId}/${dipName}`)
})

// Track if votos for current filter legislatura (or latest) are loaded
const votosReady = computed(() => {
  if (!ds.value?.legislaturas?.length) return false
  const target = histLeg.value || ds.value.legislaturas[0]
  return votosLoaded.value.has(target)
})

// Track if ALL legislaturas are loaded (for full stats)
const allVotosReady = computed(() => {
  if (!ds.value?.legislaturas?.length) return false
  return ds.value.legislaturas.every(leg => votosLoaded.value.has(leg))
})

// Load only latest legislatura initially, then lazy-load rest
watch(ds, (stats) => {
  if (stats?.legislaturas?.length) {
    loadVotosForLeg(stats.legislaturas[0])
  }
}, { immediate: true })

// When user changes leg filter, load that legislatura on demand
watch(histLeg, (leg) => {
  if (leg) loadVotosForLeg(leg)
})

// Background-load remaining legislaturas after the first one is ready
watch(votosReady, (ready) => {
  if (ready && ds.value?.legislaturas?.length > 1) {
    ds.value.legislaturas.slice(1).forEach(leg => loadVotosForLeg(leg))
  }
})

// Monthly activity sparkline
const monthlyActivity = computed(() => {
  if (!allVotosReady.value) return []
  const indices = votosByDiputado.value[dipIdx.value] || []
  const months = {}
  for (let j = 0; j < indices.length; j++) {
    const votIdx = votos.value[indices[j]][0]
    const fecha = votaciones.value[votIdx].fecha
    const month = fecha.slice(0, 7) // YYYY-MM
    if (!months[month]) months[month] = { month, favor: 0, contra: 0, abst: 0, total: 0 }
    const code = votos.value[indices[j]][3]
    if (code === 1) months[month].favor++
    else if (code === 2) months[month].contra++
    else months[month].abst++
    months[month].total++
  }
  return Object.values(months).sort((a, b) => a.month.localeCompare(b.month))
})

const sparklineMax = computed(() => {
  let max = 0
  for (const m of monthlyActivity.value) {
    if (m.total > max) max = m.total
  }
  return max || 1
})

// Category profile
const catBreakdown = computed(() => {
  if (!allVotosReady.value) return []
  const indices = votosByDiputado.value[dipIdx.value] || []
  const result = {}
  for (let j = 0; j < indices.length; j++) {
    const v = votos.value[indices[j]]
    const votIdx = v[0]
    const code = v[3]
    const cat = votaciones.value[votIdx].categoria
    if (!result[cat]) result[cat] = { 1: 0, 2: 0, 3: 0, total: 0 }
    result[cat][code]++
    result[cat].total++
  }
  return Object.entries(result)
    .sort((a, b) => b[1].total - a[1].total)
    .slice(0, 10)
})

// Top tags
const dipTopTags = computed(() => {
  if (!allVotosReady.value) return []
  const indices = votosByDiputado.value[dipIdx.value] || []
  const counts = {}
  for (let j = 0; j < indices.length; j++) {
    const vi = votos.value[indices[j]][0]
    const tags = votaciones.value[vi].etiquetas
    if (tags) {
      for (let k = 0; k < tags.length; k++) {
        counts[tags[k]] = (counts[tags[k]] || 0) + 1
      }
    }
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 20)
})

// Vote history records sorted by date desc
const dipRecords = computed(() => {
  if (!votosReady.value) return []
  const indices = votosByDiputado.value[dipIdx.value] || []
  return indices
    .map(vi => {
      const v = votos.value[vi]
      return { votIdx: v[0], code: v[3], grpIdx: v[2] }
    })
    .sort((a, b) => votaciones.value[b.votIdx].fecha.localeCompare(votaciones.value[a.votIdx].fecha))
})

const rebelRecords = computed(() => {
  return dipRecords.value.filter(r => isRebel(r.votIdx, r.code, r.grpIdx))
})

const filteredHistory = computed(() => {
  const q = normalize(histSearch.value.trim())
  const votoFilter = histVoto.value
  const legFilter = histLeg.value
  const tag = activeTag.value

  return dipRecords.value.filter(r => {
    if (q && !normalize(votaciones.value[r.votIdx].titulo_ciudadano).includes(q)) return false
    if (votoFilter && r.code !== Number(votoFilter)) return false
    if (legFilter && votaciones.value[r.votIdx].legislatura !== legFilter) return false
    if (tag && !(votaciones.value[r.votIdx].etiquetas || []).includes(tag)) return false
    return true
  })
})

const histTotalPages = computed(() => Math.max(1, Math.ceil(filteredHistory.value.length / VOTES_PER_PAGE)))

const histPageItems = computed(() => {
  const p = Math.min(histPage.value, histTotalPages.value)
  const start = (p - 1) * VOTES_PER_PAGE
  return filteredHistory.value.slice(start, start + VOTES_PER_PAGE)
})

const filteredHistoryIdsSet = computed(() => {
  const set = new Set()
  for (const record of filteredHistory.value) set.add(record.votIdx)
  return set
})

const filteredHistoryMapByVotIdx = computed(() => {
  const map = new Map()
  for (const record of filteredHistory.value) map.set(record.votIdx, record)
  return map
})

// Group page items by expediente
const groupedHistoryItems = computed(() => {
  if (!groupByExp.value) return histPageItems.value.map(r => ({ type: 'single', record: r }))

  const items = []
  const seen = new Set()
  const filteredIdsSet = filteredHistoryIdsSet.value
  const recordsByVotIdx = filteredHistoryMapByVotIdx.value
  for (const record of histPageItems.value) {
    const vot = votaciones.value[record.votIdx]
    const exp = vot.exp
    if (!exp || !votsByExp.value[exp] || votsByExp.value[exp].length <= 1) {
      items.push({ type: 'single', record })
      continue
    }
    if (seen.has(exp)) continue
    seen.add(exp)
    // Find all votaciones in this exp that are also in the current filtered set
    const expIndices = votsByExp.value[exp].filter(i => filteredIdsSet.has(i))
    if (expIndices.length <= 1) {
      items.push({ type: 'single', record })
      continue
    }
    // Need to find the records for these indices to get the votes
    const expRecords = expIndices.map(i => recordsByVotIdx.get(i))
    items.push({ type: 'group', exp, records: expRecords, primary: record })
  }
  return items
})

function toggleExp(exp) {
  expandedExps.value = { ...expandedExps.value, [exp]: !expandedExps.value[exp] }
}

const onHistSearch = debounce(() => { histPage.value = 1 }, 250)

function resultClass(result) {
  return result === 'Aprobada' ? 'aprobada' : result === 'Rechazada' ? 'rechazada' : 'empate'
}

function catPcts(counts) {
  const total = counts.total
  const favorPct = Math.round((counts[1] / total) * 100)
  const contraPct = Math.round((counts[2] / total) * 100)
  const abstPct = 100 - favorPct - contraPct
  return { favorPct, contraPct, abstPct }
}

function toggleTag(tag) {
  if (activeTag.value === tag) {
    activeTag.value = ''
  } else {
    activeTag.value = tag
    showAccCard.value = true
    accTag.value = tag
  }
  histPage.value = 1
}

function closeAccCard() {
  showAccCard.value = false
}

function isRebel(votIdx, code, grpIdx) {
  const detail = votacionDetail.value[votIdx]
  if (!detail || !detail.group_majority) return false
  const groupName = grupos.value[grpIdx]
  const maj = detail.group_majority[groupName]
  // maj is 1 (favor), 2 (contra), 3 (abstencion)
  return maj && maj !== code && code !== 4 // 4 is no_vota
}

// Handle tag from URL query
watch(() => route.query.tag, (tag) => {
  if (tag) {
    activeTag.value = tag
    showAccCard.value = true
    accTag.value = tag
  }
}, { immediate: true })

// Update document title
watch(name, (n) => {
  if (n) document.title = n + ' | Lo Que Votan'
}, { immediate: true })
</script>

<template>
  <section v-if="ds">
    <div class="container" style="padding-top:1.5rem">
      <router-link to="/diputados" class="back-link">&larr; Diputados</router-link>

      <div class="detail-header" style="display:flex;align-items:center;gap:1.25rem">
        <img v-if="photoUrl" :src="photoUrl" :alt="name" class="dip-detail-photo">
        <span v-else class="dip-detail-avatar" :style="avatarStyle(name)">{{ avatarInitials(name) }}</span>
        <div>
          <h1 style="margin:0">{{ name }}</h1>
          <div class="detail-meta" style="margin-top:0.5rem">
            <router-link :to="{ path: '/diputados', query: { grupo: groupInfo.value } }" class="badge" :style="{ backgroundColor: groupInfo.color, color: 'white' }">{{ groupInfo.label }}</router-link>
            <span class="detail-meta-item">{{ ds.total }} votaciones</span>
            <span class="detail-meta-item">Lealtad al grupo: {{ pct(ds.loyalty) }}</span>
            <span v-for="l in ds.legislaturas" :key="l" class="badge badge--leg">{{ l }}</span>
          </div>
          
          <div v-if="otherScopes.length > 0" style="margin-top: 0.75rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <span style="font-size: 0.85rem; color: var(--color-text-secondary); font-weight: 500;">También en:</span>
            <button 
              v-for="a in otherScopes" 
              :key="a.id"
              class="btn btn--sm btn--outline scope-cross-btn"
              @click="navigateToScope(a.id)"
            >
              <img :src="`${baseUrl}assets/flags/${a.id}.svg`" class="scope-flag-sm" :alt="a.nombre" />
              {{ a.nombre }} &rarr;
            </button>
          </div>
        </div>
      </div>

      <!-- Stat cards -->
      <div class="stat-cards">
        <div class="stat-card">
          <span class="stat-card-value">{{ ds.total }}</span>
          <span class="stat-card-label">Votaciones</span>
        </div>
        <div class="stat-card stat-card--favor">
          <span class="stat-card-value">{{ ds.favor }}</span>
          <span class="stat-card-label">A favor ({{ pct(ds.favor / ds.total) }})</span>
        </div>
        <div class="stat-card stat-card--contra">
          <span class="stat-card-value">{{ ds.contra }}</span>
          <span class="stat-card-label">En contra ({{ pct(ds.contra / ds.total) }})</span>
        </div>
        <div class="stat-card stat-card--abstencion">
          <span class="stat-card-value">{{ ds.abstencion }}</span>
          <span class="stat-card-label">Abstenciones ({{ pct(ds.abstencion / ds.total) }})</span>
        </div>
      </div>

      <VoteBar :favor="ds.favor" :contra="ds.contra" :abstencion="ds.abstencion" :total="ds.total" />

      <template v-if="allVotosReady">
        <!-- Activity timeline -->
        <div v-if="monthlyActivity.length > 1" class="detail-section">
          <h2>Actividad mensual</h2>
          <div class="sparkline-wrap">
            <svg :viewBox="'0 0 ' + monthlyActivity.length * 8 + ' 50'" preserveAspectRatio="none" class="sparkline-svg">
              <g v-for="(m, i) in monthlyActivity" :key="m.month">
                <rect
                  :x="i * 8" :y="50 - (m.favor / sparklineMax * 48)"
                  width="6" :height="m.favor / sparklineMax * 48"
                  fill="var(--color-favor)" opacity="0.85"
                >
                  <title>{{ m.month }}: {{ m.favor }} a favor, {{ m.contra }} en contra, {{ m.abst }} abstenciones</title>
                </rect>
                <rect
                  :x="i * 8" :y="50 - ((m.favor + m.contra) / sparklineMax * 48)"
                  width="6" :height="m.contra / sparklineMax * 48"
                  fill="var(--color-contra)" opacity="0.85"
                >
                  <title>{{ m.month }}: {{ m.favor }} a favor, {{ m.contra }} en contra, {{ m.abst }} abstenciones</title>
                </rect>
                <rect
                  :x="i * 8" :y="50 - (m.total / sparklineMax * 48)"
                  width="6" :height="m.abst / sparklineMax * 48"
                  fill="var(--color-abstencion)" opacity="0.85"
                >
                  <title>{{ m.month }}: {{ m.favor }} a favor, {{ m.contra }} en contra, {{ m.abst }} abstenciones</title>
                </rect>
              </g>
            </svg>
            <div class="sparkline-labels">
              <span>{{ monthlyActivity[0].month }}</span>
              <span>{{ monthlyActivity[monthlyActivity.length - 1].month }}</span>
            </div>
          </div>
        </div>

        <!-- Category profile -->
        <div v-if="catBreakdown.length" class="detail-section">
          <h2>Perfil temático</h2>
          <div class="cat-profile">
            <div v-for="[catIdx, counts] in catBreakdown" :key="catIdx" class="cat-profile-row">
              <span class="cat-profile-label" :title="fmt(categorias[catIdx] || catIdx)">
                {{ fmt(categorias[catIdx] || catIdx) }}
              </span>
              <div class="cat-profile-bar">
                <div
                  class="cat-profile-seg"
                  :style="{ width: catPcts(counts).favorPct + '%', background: 'var(--color-favor)' }"
                  :title="catPcts(counts).favorPct + '% A favor'"
                />
                <div
                  class="cat-profile-seg"
                  :style="{ width: catPcts(counts).contraPct + '%', background: 'var(--color-contra)' }"
                  :title="catPcts(counts).contraPct + '% En contra'"
                />
                <div
                  class="cat-profile-seg"
                  :style="{ width: catPcts(counts).abstPct + '%', background: 'var(--color-abstencion)' }"
                  :title="catPcts(counts).abstPct + '% Abstencion'"
                />
              </div>
              <span class="cat-profile-count">{{ counts.total }}</span>
            </div>
          </div>
        </div>

        <!-- Top tags -->
        <div v-if="dipTopTags.length" class="detail-section">
          <h2>Temas más votados</h2>
          <p class="hint-text">Haz clic en un tema para ver la ficha de rendición de cuentas</p>
          <div>
            <span
              v-for="[tag, count] in dipTopTags"
              :key="tag"
              class="chip chip--lg chip--clickable"
              :class="{ 'chip--active': activeTag === tag }"
              @click="toggleTag(tag)"
            >
              {{ fmt(tag) }} ({{ count }})
            </span>
          </div>
        </div>

      </template>
      <div v-else class="detail-section">
        <div class="loading-wrap" style="padding:2rem"><div class="loading-spinner"></div></div>
      </div>

      <!-- Rebel votes detail -->
      <template v-if="allVotosReady && rebelRecords.length > 0">
        <div class="detail-section rebel-section">
          <h2 style="color:var(--color-contra)">Votos discordantes ({{ rebelRecords.length }})</h2>
          <p class="hint-text">Votaciones donde este representante votó de forma distinta a la mayoría de su grupo parlamentario.</p>
          
          <div class="table-wrap">
            <table class="responsive-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Voto</th>
                  <th>Asunto</th>
                  <th>Mayoría Grupo</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rebelRecords" :key="r.votIdx">
                  <td data-label="Fecha">{{ votaciones[r.votIdx].fecha }}</td>
                  <td data-label="Voto">
                    <span class="voto-pill" :class="votoPillClass(r.code)">
                      {{ VOTO_LABELS[r.code] }}
                    </span>
                  </td>
                  <td data-label="Asunto">
                    <router-link :to="'/votacion/' + votaciones[r.votIdx].id">
                      {{ votaciones[r.votIdx].titulo_ciudadano }}
                    </router-link>
                  </td>
                  <td data-label="Mayoría Grupo">
                    <span class="voto-pill" :class="votoPillClass(votacionDetail[r.votIdx]?.group_majority[grupos[r.grpIdx]])">
                      {{ VOTO_LABELS[votacionDetail[r.votIdx]?.group_majority[grupos[r.grpIdx]]] }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- Vote history (works with partial votos) -->
      <template v-if="votosReady">
        <div class="detail-section">
          <h2>Historial de votos</h2>
          <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem">
            <input
              v-model="histSearch"
              type="search"
              class="filter-input"
              placeholder="Buscar asunto..."
              style="flex:1;min-width:200px"
              @input="onHistSearch"
            >
            <select v-model="histVoto" class="filter-select" style="width:auto;min-width:130px" @change="histPage = 1">
              <option value="">Todos los votos</option>
              <option value="1">A favor</option>
              <option value="2">En contra</option>
              <option value="3">Abstención</option>
            </select>
            <select v-model="histLeg" class="filter-select" style="width:auto;min-width:130px" @change="histPage = 1">
              <option value="">Todas las legislaturas</option>
              <option v-for="l in (ds.legislaturas || [])" :key="l" :value="l">{{ l }}</option>
            </select>
          </div>

          <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem">
            <p style="font-size:0.85rem;color:var(--color-muted);margin:0">
              {{ filteredHistory.length.toLocaleString('es-ES') }} votaciones
            </p>
            <label style="font-size:0.8rem;color:var(--color-muted);display:flex;align-items:center;gap:0.35rem;margin-left:auto;cursor:pointer">
              <input type="checkbox" v-model="groupByExp"> Agrupar por expediente
            </label>
          </div>

          <div class="table-wrap">
            <table class="responsive-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Voto</th>
                  <th>Asunto</th>
                  <th>Legislatura</th>
                  <th>Categoría</th>
                  <th>Resultado</th>
                </tr>
              </thead>
              <tbody>
                <template v-if="groupedHistoryItems.length">
                  <template v-for="item in groupedHistoryItems" :key="item.type === 'single' ? item.record.votIdx : item.exp">
                    <!-- Header row for a group -->
                    <tr v-if="item.type === 'group'" class="exp-row" @click="toggleExp(item.exp)">
                      <td colspan="6">
                        <div style="display:flex;align-items:center;gap:0.5rem;cursor:pointer">
                          <span style="font-size:0.7rem;color:var(--color-muted);width:12px">
                            {{ expandedExps[item.exp] ? '&#9660;' : '&#9654;' }}
                          </span>
                          <span style="font-weight:600;font-size:0.88rem;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                            {{ votaciones[item.primary.votIdx].titulo_ciudadano }}
                          </span>
                          <span class="badge badge--sm badge--leg">{{ item.records.length }} votaciones</span>
                        </div>
                      </td>
                    </tr>

                    <!-- Votes (either single or members of expanded group) -->
                    <template v-if="item.type === 'single'">
                      <tr>
                        <td data-label="Fecha">{{ votaciones[item.record.votIdx].fecha }}</td>
                        <td data-label="Voto">
                          <span class="voto-pill" :class="votoPillClass(item.record.code)">
                            {{ VOTO_LABELS[item.record.code] || '?' }}
                          </span>
                          <span v-if="isRebel(item.record.votIdx, item.record.code, item.record.grpIdx)" class="badge badge--contra badge--sm" style="margin-left:0.35rem" title="Voto diferente a la mayoría de su grupo">Rebelde</span>
                        </td>
                        <td data-label="Asunto">
                          <router-link :to="'/votacion/' + votaciones[item.record.votIdx].id">
                            {{ votaciones[item.record.votIdx].titulo_ciudadano }}
                          </router-link>
                          <GlossaryTooltip
                            v-if="votaciones[item.record.votIdx].subTipo"
                            :term="votaciones[item.record.votIdx].subTipo"
                          >
                            <span
                              class="badge badge--sm"
                              :class="subTipoBadgeClass(votaciones[item.record.votIdx].subTipo)"
                              style="margin-left:0.35rem"
                            >{{ subTipoLabel(votaciones[item.record.votIdx].subTipo) }}</span>
                          </GlossaryTooltip>
                        </td>
                        <td data-label="Legislatura">
                          <span v-if="votaciones[item.record.votIdx].legislatura" class="badge badge--leg">
                            {{ votaciones[item.record.votIdx].legislatura }}
                          </span>
                        </td>
                        <td data-label="Categoría">
                          <span class="badge badge--cat">
                            {{ fmt(categorias[votaciones[item.record.votIdx].categoria]) }}
                          </span>
                        </td>
                        <td data-label="Resultado">
                          <ResultBadge :result="votResults[item.record.votIdx].result" />
                        </td>
                      </tr>
                    </template>
                    <template v-else-if="expandedExps[item.exp]">
                      <tr v-for="rec in item.records" :key="rec.votIdx" class="exp-sub-row">
                        <td data-label="Fecha">{{ votaciones[rec.votIdx].fecha }}</td>
                        <td data-label="Voto">
                          <span class="voto-pill" :class="votoPillClass(rec.code)">
                            {{ VOTO_LABELS[rec.code] || '?' }}
                          </span>
                          <span v-if="isRebel(rec.votIdx, rec.code, rec.grpIdx)" class="badge badge--contra badge--sm" style="margin-left:0.35rem" title="Voto diferente a la mayoría de su grupo">Rebelde</span>
                        </td>
                        <td data-label="Asunto" style="padding-left:1.5rem">
                          <router-link :to="'/votacion/' + votaciones[rec.votIdx].id">
                            {{ votaciones[rec.votIdx].titulo_ciudadano }}
                          </router-link>
                          <GlossaryTooltip
                            v-if="votaciones[rec.votIdx].subTipo"
                            :term="votaciones[rec.votIdx].subTipo"
                          >
                            <span
                              class="badge badge--sm"
                              :class="subTipoBadgeClass(votaciones[rec.votIdx].subTipo)"
                              style="margin-left:0.35rem"
                            >{{ subTipoLabel(votaciones[rec.votIdx].subTipo) }}</span>
                          </GlossaryTooltip>
                        </td>
                        <td data-label="Legislatura">
                          <span v-if="votaciones[rec.votIdx].legislatura" class="badge badge--leg">
                            {{ votaciones[rec.votIdx].legislatura }}
                          </span>
                        </td>
                        <td data-label="Categoría">
                          <span class="badge badge--cat">
                            {{ fmt(categorias[votaciones[rec.votIdx].categoria]) }}
                          </span>
                        </td>
                        <td data-label="Resultado">
                          <ResultBadge :result="votResults[rec.votIdx].result" />
                        </td>
                      </tr>
                    </template>
                    <template v-else>
                      <tr>
                        <td data-label="Fecha">{{ votaciones[item.primary.votIdx].fecha }}</td>
                        <td data-label="Voto">
                          <span class="voto-pill" :class="votoPillClass(item.primary.code)">
                            {{ VOTO_LABELS[item.primary.code] || '?' }}
                          </span>
                          <span v-if="isRebel(item.primary.votIdx, item.primary.code, item.primary.grpIdx)" class="badge badge--contra badge--sm" style="margin-left:0.35rem" title="Voto diferente a la mayoría de su grupo">Rebelde</span>
                        </td>
                        <td data-label="Asunto">
                          <router-link :to="'/votacion/' + votaciones[item.primary.votIdx].id">
                            {{ votaciones[item.primary.votIdx].titulo_ciudadano }}
                          </router-link>
                          <GlossaryTooltip
                            v-if="votaciones[item.primary.votIdx].subTipo"
                            :term="votaciones[item.primary.votIdx].subTipo"
                          >
                            <span
                              class="badge badge--sm"
                              :class="subTipoBadgeClass(votaciones[item.primary.votIdx].subTipo)"
                              style="margin-left:0.35rem"
                            >{{ subTipoLabel(votaciones[item.primary.votIdx].subTipo) }}</span>
                          </GlossaryTooltip>
                        </td>
                        <td data-label="Legislatura">
                          <span v-if="votaciones[item.primary.votIdx].legislatura" class="badge badge--leg">
                            {{ votaciones[item.primary.votIdx].legislatura }}
                          </span>
                        </td>
                        <td data-label="Categoría">
                          <span class="badge badge--cat">
                            {{ fmt(categorias[votaciones[item.primary.votIdx].categoria]) }}
                          </span>
                        </td>
                        <td data-label="Resultado">
                          <ResultBadge :result="votResults[item.primary.votIdx].result" />
                        </td>
                      </tr>
                    </template>
                  </template>
                </template>
                <tr v-else>
                  <td colspan="6" class="text-center" style="padding:1.5rem;color:var(--color-muted)">
                    Sin resultados
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <Pagination :total-pages="histTotalPages" :current="histPage" @page="p => histPage = p" />
        </div>
      </template>
      <div v-else class="detail-section">
        <div class="loading-wrap" style="padding:2rem"><div class="loading-spinner"></div></div>
      </div>

      <ShareBar
        :title="name + ' - ' + (groupInfo?.label || 'Sin grupo')"
        :share-url="shareUrl"
      />

      <AccountabilityCard
        v-if="showAccCard && votosReady"
        :dip-idx="dipIdx"
        :tag="accTag"
        @close="closeAccCard"
      />
    </div>
  </section>
</template>

<style scoped>
.dip-detail-photo {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.dip-detail-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.scope-cross-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0.6rem;
}

.scope-flag-sm {
  width: 14px;
  height: 10px;
  object-fit: cover;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.1);
  display: block;
}

.detail-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.detail-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--color-muted);
}

.detail-section {
  margin-top: 2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
}

.rebel-section {
  border-color: rgba(220, 38, 38, 0.3);
  background: rgba(220, 38, 38, 0.02);
}

.detail-section h2 {
  font-size: 1.15rem;
  margin-bottom: 0.75rem;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
  padding: 1rem;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.stat-card-value {
  display: block;
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1.2;
}

.stat-card-label {
  font-size: 0.8rem;
  color: var(--color-muted);
  font-weight: 500;
}

.stat-card--favor { border-left: 4px solid var(--color-favor); }
.stat-card--favor .stat-card-value { color: var(--color-favor); }
.stat-card--contra { border-left: 4px solid var(--color-contra); }
.stat-card--contra .stat-card-value { color: var(--color-contra); }
.stat-card--abstencion { border-left: 4px solid var(--color-abstencion); }
.stat-card--abstencion .stat-card-value { color: var(--color-abstencion); }

.sparkline-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.sparkline-svg {
  width: 100%;
  height: 80px;
  display: block;
}

.sparkline-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--color-muted);
  margin-top: 0.25rem;
}

.cat-profile { margin-top: 0.5rem; }

.cat-profile-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.4rem;
}

.cat-profile-label {
  width: 180px;
  min-width: 180px;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cat-profile-bar {
  flex: 1;
  height: 22px;
  border-radius: 4px;
  display: flex;
  overflow: hidden;
  background: var(--color-border);
}

.cat-profile-seg {
  height: 100%;
  min-width: 1px;
  transition: width 0.3s;
}

.cat-profile-count {
  width: 40px;
  font-size: 0.8rem;
  color: var(--color-muted);
  text-align: right;
}

.hint-text {
  font-size: 0.82rem;
  color: var(--color-muted);
  margin-bottom: 0.5rem;
  font-style: italic;
}

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .stat-card-value { font-size: 1.35rem; }
  .detail-meta { flex-direction: column; align-items: flex-start; }
  .cat-profile-label { width: 120px; min-width: 120px; font-size: 0.78rem; }
  .cat-profile-row { gap: 0.5rem; }
}

.exp-row {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.exp-row:hover {
  background: var(--color-primary-lighter);
}

.exp-sub-row {
  border-left: 3px solid var(--color-primary);
}

@media (max-width: 768px) {
  .exp-row td::before {
    display: none !important;
  }
  .exp-row td {
    padding-left: 1rem !important;
  }
}
</style>
