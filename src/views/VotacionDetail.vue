<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, normalize, VOTO_LABELS, resultMarginText, subTipoLabel, subTipoBadgeClass, votoPillClass, getGroupInfo, buildAbsoluteAppUrl } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import ShareBar from '../components/ShareBar.vue'
import ViewState from '../components/ViewState.vue'
import GlossaryTooltip from '../components/GlossaryTooltip.vue'

const route = useRoute()
const { votaciones, votResults, votos, votosByVotacion, votsByExp, categorias, grupos, diputados, loadVotosForLeg, votosLoaded, votacionDetail, votIdById, loaded, currentScopeId, setScope, ambitos } = useData()

const idx = computed(() => votIdById.value?.[route.params.id])
const vot = computed(() => {
  const base = votaciones.value[idx.value]
  if (!base) return base
  const detail = votacionDetail.value[idx.value]
  return detail ? { ...base, ...detail } : base
})
const r = computed(() => votResults.value[idx.value])
const dipSearch = ref('')
const highlightedDip = ref('')
const highlightedGroup = ref('')
const showEmbed = ref(false)
const copiedEmbed = ref(false)

const embedCode = computed(() => {
  if (!vot.value) return ''
  const url = buildAbsoluteAppUrl(`widget/${encodeURIComponent(vot.value.id)}?embed=true`)
  return `<iframe src="${url}" width="100%" height="280" frameborder="0" style="border:1px solid #e2e8f0; border-radius:12px; max-width:550px;"></iframe>`
})

function toggleEmbed() {
  showEmbed.value = !showEmbed.value
}

function copyEmbed() {
  navigator.clipboard.writeText(embedCode.value)
  copiedEmbed.value = true
  setTimeout(() => {
    copiedEmbed.value = false
  }, 2000)
}

const votosReady = computed(() => {
  if (!vot.value?.legislatura) return false
  return votosLoaded.value.has(vot.value.legislatura)
})

const notFound = computed(() => loaded.value && !vot.value)

// Load votos for this votacion's legislatura
watch(vot, (v) => {
  if (v?.legislatura) loadVotosForLeg(v.legislatura)
}, { immediate: true })

// Handle ?dip= query param to pre-filter and highlight a specific diputado
watch(() => route.query.dip, (dip) => {
  if (dip) {
    const name = decodeURIComponent(dip)
    dipSearch.value = name.split(',')[0]  // Search by apellido
    highlightedDip.value = name
  } else {
    highlightedDip.value = ''
  }
}, { immediate: true })

watch(() => route.query.group, (group) => {
  if (group) {
    highlightedGroup.value = decodeURIComponent(group)
  } else {
    highlightedGroup.value = ''
  }
}, { immediate: true })

function applyScopeFromQuery(scope) {
  if (typeof scope !== 'string') return
  const target = scope.trim().toLowerCase()
  const knownScopes = new Set(['nacional', ...(ambitos.value || []).map(a => String(a.id || '').toLowerCase())])
  if (!knownScopes.has(target)) return
  if (!target || target === currentScopeId.value) return
  setScope(target)
}

watch([() => route.query.scope, () => ambitos.value.length], ([scope]) => {
  applyScopeFromQuery(scope)
}, { immediate: true })

// Group breakdown
const byGroup = computed(() => {
  if (!votosReady.value) return {}
  const result = {}
  const indices = votosByVotacion.value[idx.value] || []
  for (let j = 0; j < indices.length; j++) {
    const v = votos.value[indices[j]]
    const g = v[2]
    if (!result[g]) result[g] = { 1: 0, 2: 0, 3: 0, total: 0 }
    result[g][v[3]]++
    result[g].total++
  }
  return result
})

const sortedGroups = computed(() =>
  Object.keys(byGroup.value)
    .map(Number)
    .sort((a, b) => (grupos.value[a] || '').localeCompare(grupos.value[b] || ''))
)

// Individual votes sorted by name
const sortedVoteIndices = computed(() => {
  if (!votosReady.value) return []
  const indices = votosByVotacion.value[idx.value] || []
  return [...indices].sort((a, b) =>
    diputados.value[votos.value[a][1]].localeCompare(diputados.value[votos.value[b][1]])
  )
})

const filteredVotes = computed(() => {
  const q = normalize(dipSearch.value.trim())
  if (!q) return sortedVoteIndices.value
  return sortedVoteIndices.value.filter(vi => {
    const name = diputados.value[votos.value[vi][1]]
    return normalize(name).includes(q)
  })
})

const nominalVoteCount = computed(() => {
  if (!votosReady.value) return 0
  return (votosByVotacion.value[idx.value] || []).length
})

const hasNominalVotes = computed(() => nominalVoteCount.value > 0)

const noNominalVotesMessage = computed(() => {
  if (!votosReady.value || hasNominalVotes.value) return ''
  if ((r.value?.total || 0) <= 0) return 'No hay votos registrados para esta votación.'
  return 'Esta votación no incluye detalle nominal por representante en la fuente oficial. Solo hay resultado agregado.'
})

function groupMajorityCode(gIdx) {
  const c = byGroup.value[gIdx]
  if (!c) return null
  if (c[1] >= c[2] && c[1] >= c[3]) return 1
  if (c[2] >= c[3]) return 2
  return 3
}

function voteTokenFromCode(code) {
  if (code === 1) return 'si'
  if (code === 2) return 'no'
  if (code === 3) return 'abstencion'
  return 'no_vota'
}

function normalizeVoteToken(value) {
  if (typeof value !== 'string') return ''
  const normalized = value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
  if (normalized === 'si' || normalized === 'a_favor' || normalized === 'favor') return 'si'
  if (normalized === 'no' || normalized === 'en_contra' || normalized === 'contra') return 'no'
  if (normalized === 'abstencion' || normalized === 'abstenerse') return 'abstencion'
  if (normalized === 'no_vota' || normalized === 'ausente') return 'no_vota'
  return ''
}

function voteActionTextFromCode(code) {
  if (code === 1) return 'votó a favor'
  if (code === 2) return 'votó en contra'
  if (code === 3) return 'se abstuvo'
  if (code === 4) return 'no votó'
  return 'participó'
}

function shortDiputadoName(name) {
  if (!name) return ''
  return String(name).split(',')[0].trim() || String(name)
}

const highlightedVoteCode = computed(() => {
  if (!votosReady.value || !highlightedDip.value) return null
  const target = normalize(highlightedDip.value)
  const indices = votosByVotacion.value[idx.value] || []
  for (let j = 0; j < indices.length; j++) {
    const vi = indices[j]
    const dipName = diputados.value[votos.value[vi][1]]
    if (dipName === highlightedDip.value || normalize(dipName) === target) {
      return votos.value[vi][3]
    }
  }
  return null
})

const highlightedVoteSummary = computed(() => {
  if (!highlightedDip.value || !vot.value?.titulo_ciudadano) return ''
  const shortName = shortDiputadoName(highlightedDip.value)
  const code = highlightedVoteCode.value
  if (code == null) return ''
  return `${shortName} ${voteActionTextFromCode(code)} en "${vot.value.titulo_ciudadano}".`
})

const highlightedVoteToken = computed(() => {
  if (highlightedVoteCode.value != null) return voteTokenFromCode(highlightedVoteCode.value)
  const fromQuery = route.query.vote
  if (typeof fromQuery === 'string') return normalizeVoteToken(fromQuery)
  return ''
})

function findGroupIdxByName(groupName) {
  if (!groupName) return -1
  const target = normalize(groupName)
  for (let i = 0; i < grupos.value.length; i++) {
    if (normalize(grupos.value[i]) === target) return i
  }
  return -1
}

const highlightedGroupCode = computed(() => {
  if (highlightedGroup.value) {
    const gIdx = findGroupIdxByName(highlightedGroup.value)
    if (gIdx >= 0 && byGroup.value[gIdx]) return groupMajorityCode(gIdx)
  }
  return null
})

const highlightedGroupVoteToken = computed(() => {
  if (highlightedGroupCode.value != null) return voteTokenFromCode(highlightedGroupCode.value)
  const fromQuery = route.query.groupVote
  if (typeof fromQuery === 'string') return normalizeVoteToken(fromQuery)
  return ''
})

const highlightedGroupSummary = computed(() => {
  if (!highlightedGroup.value || !vot.value?.titulo_ciudadano) return ''
  const gIdx = findGroupIdxByName(highlightedGroup.value)
  const label = gIdx >= 0 ? getGroupInfo(grupos.value[gIdx]).label : highlightedGroup.value
  if (highlightedGroupCode.value != null) {
    return `${label} ${voteActionTextFromCode(highlightedGroupCode.value)} en "${vot.value.titulo_ciudadano}".`
  }
  return `Como voto ${label} en "${vot.value.titulo_ciudadano}"?`
})

const shareText = computed(() => {
  if (!vot.value?.titulo_ciudadano) return ''
  if (highlightedDip.value) {
    const shortName = shortDiputadoName(highlightedDip.value)
    if (highlightedVoteCode.value != null) {
      return `${shortName} ${voteActionTextFromCode(highlightedVoteCode.value)} en "${vot.value.titulo_ciudadano}".`
    }
    return `Como voto ${shortName} en "${vot.value.titulo_ciudadano}"?`
  }
  if (highlightedGroup.value) return highlightedGroupSummary.value
  return ''
})

const copiedVi = ref(null)
function copyVoteLink(vi) {
  const dipName = diputados.value[votos.value[vi][1]]
  const voteToken = voteTokenFromCode(votos.value[vi][3])
  const scope = encodeURIComponent(currentScopeId.value || 'nacional')
  const voteId = encodeURIComponent(vot.value.id)
  const url = buildAbsoluteAppUrl(`share/votacion/${scope}/${voteId}?dip=${encodeURIComponent(dipName)}&vote=${encodeURIComponent(voteToken)}`)
  navigator.clipboard.writeText(url)
  copiedVi.value = vi
  setTimeout(() => { if (copiedVi.value === vi) copiedVi.value = null }, 2000)
}

const copiedGroup = ref(null)
function copyGroupLink(gIdx) {
  const groupName = grupos.value[gIdx]
  const groupVoteCode = groupMajorityCode(gIdx)
  const groupVoteToken = groupVoteCode != null ? voteTokenFromCode(groupVoteCode) : ''
  const scope = encodeURIComponent(currentScopeId.value || 'nacional')
  const voteId = encodeURIComponent(vot.value.id)
  let url = buildAbsoluteAppUrl(`share/votacion/${scope}/${voteId}?group=${encodeURIComponent(groupName)}`)
  if (groupVoteToken) {
    url += `&groupVote=${encodeURIComponent(groupVoteToken)}`
  }
  navigator.clipboard.writeText(url)
  copiedGroup.value = gIdx
  setTimeout(() => { if (copiedGroup.value === gIdx) copiedGroup.value = null }, 2000)
}

const shareUrl = computed(() => {
  if (!vot.value?.id) return ''
  const scopeId = currentScopeId.value || 'nacional'
  const voteId = encodeURIComponent(vot.value.id)
  let url = buildAbsoluteAppUrl(`share/votacion/${encodeURIComponent(scopeId)}/${voteId}`)
  if (highlightedDip.value) {
    url += `?dip=${encodeURIComponent(highlightedDip.value)}`
    if (highlightedVoteToken.value) {
      url += `&vote=${encodeURIComponent(highlightedVoteToken.value)}`
    }
    return url
  }
  if (highlightedGroup.value) {
    url += `?group=${encodeURIComponent(highlightedGroup.value)}`
    if (highlightedGroupVoteToken.value) {
      url += `&groupVote=${encodeURIComponent(highlightedGroupVoteToken.value)}`
    }
    return url
  }
  return url
})

const sourceLink = computed(() => {
  if (!vot.value) return null
  if (vot.value.urlCongreso) return { href: vot.value.urlCongreso, label: 'Ver en congreso.es' }
  if (vot.value.urlCyL) return { href: vot.value.urlCyL, label: 'Ver en ccyl.es' }
  if (vot.value.urlMadrid) return { href: vot.value.urlMadrid, label: 'Ver en asambleamadrid.es' }
  if (vot.value.urlCatalunya) return { href: vot.value.urlCatalunya, label: 'Ver en parlament.cat' }
  return null
})

// Exp / Dossier logic
const expGroup = computed(() => {
  if (!votsByExp.value || !vot.value?.exp) return null
  const indices = votsByExp.value[vot.value.exp] || []
  if (indices.length <= 1) return null

  const group = indices.map(i => ({
    idx: i,
    vot: votaciones.value[i],
    res: votResults.value[i]
  }))

  // Sort by date then index
  group.sort((a, b) => a.vot.fecha.localeCompare(b.vot.fecha) || a.idx - b.idx)

  const total = group.length
  const aprobadas = group.filter(g => g.res.result === 'Aprobada').length
  const rechazadas = total - aprobadas

  // Group by tipo
  const byTipo = {}
  group.forEach(g => {
    const t = g.vot.subTipo || 'otro'
    if (!byTipo[t]) byTipo[t] = { label: subTipoLabel(t) || 'Otras votaciones', items: [] }
    byTipo[t].items.push(g)
  })

  const tipos = Object.keys(byTipo)
    .sort((a, b) => (a === 'final' ? -1 : b === 'final' ? 1 : 0))
    .map(t => ({
      id: t,
      label: byTipo[t].label,
      items: byTipo[t].items,
    }))

  // Find the final vote
  const finalItem = group.find(g =>
    g.vot.subTipo === 'final' || g.vot.subTipo === 'dictamen'
  )

  return { total, aprobadas, rechazadas, tipos, finalItem }
})

// Which tipo groups are expanded
const expandedTipos = ref({})
function toggleTipo(tipo) {
  expandedTipos.value = { ...expandedTipos.value, [tipo]: !expandedTipos.value[tipo] }
}

// Update document title
watch(vot, (v) => {
  if (v) document.title = v.titulo_ciudadano + ' | Lo Que Votan'
}, { immediate: true })
</script>

<template>
  <section v-if="vot">
    <div class="container" style="padding-top:1.5rem">
      <router-link to="/votaciones" class="back-link">&larr; Votaciones</router-link>

      <div class="detail-header">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem">
          <h1 style="flex:1; margin:0">{{ vot.titulo_ciudadano }}</h1>
          <button class="btn btn--sm btn--outline" @click="toggleEmbed">
            &#128187; Insertar en web
          </button>
        </div>

        <div v-if="showEmbed" class="embed-box">
          <p class="small mb-1">Copia este código para insertar el gráfico en tu web o blog:</p>
          <div class="embed-code-wrap">
            <textarea readonly class="embed-code" @click="$event.target.select()">{{ embedCode }}</textarea>
            <button class="btn btn--primary btn--sm" @click="copyEmbed">
              {{ copiedEmbed ? '¡Copiado!' : 'Copiar código' }}
            </button>
          </div>
        </div>

        <p v-if="vot.resumen" class="detail-summary" style="margin-top:0.5rem">{{ vot.resumen }}</p>
        <p v-if="highlightedVoteSummary" class="detail-highlight-vote">{{ highlightedVoteSummary }}</p>
        <p v-if="!highlightedVoteSummary && highlightedGroupSummary" class="detail-highlight-vote">{{ highlightedGroupSummary }}</p>
        
        <!-- Nota explicativa para votos deducidos -->
        <div v-if="vot.metadatos?.tipo === 'deduccion_grupal'" class="deduced-note">
          <span class="deduced-icon">ℹ️</span>
          <p>{{ vot.metadatos.nota }}</p>
        </div>

        <p v-if="vot.subgrupo" class="detail-subgrupo">{{ vot.subgrupo }}</p>
        <div class="detail-meta" style="margin-top:0.75rem">
          <ResultBadge :result="r.result" large />
          <span class="result-margin">{{ resultMarginText(r) }}</span>
          <GlossaryTooltip v-if="vot.subTipo" :term="vot.subTipo">
            <span class="badge" :class="subTipoBadgeClass(vot.subTipo)">{{ subTipoLabel(vot.subTipo) }}</span>
          </GlossaryTooltip>
          <span class="detail-meta-item">{{ vot.fecha }}</span>
          <span v-if="vot.legislatura" class="badge badge--leg">{{ vot.legislatura }}</span>
          <span v-if="vot.proponente" class="badge badge--proponente">{{ vot.proponente }}</span>
          <span class="badge badge--cat">{{ fmt(categorias[vot.categoria]) }}</span>
          <span v-for="tag in (vot.etiquetas || [])" :key="tag" class="chip">{{ fmt(tag) }}</span>
        </div>
      </div>

      <!-- Official text and source -->
      <div v-if="vot.textoOficial" class="detail-section detail-oficial">
        <h2>Texto oficial del expediente</h2>
        <blockquote class="texto-oficial">{{ vot.textoOficial }}</blockquote>
        <a v-if="sourceLink" :href="sourceLink.href" target="_blank" rel="noopener" class="link-external">
          {{ sourceLink.label }} &nearr;
        </a>
      </div>

      <div class="vote-detail-grid">
        <div class="vote-results-main">
          <!-- Main results -->
          <div class="detail-section">
            <h2>Resultado de la votación</h2>
            <VoteBar :favor="r.favor" :contra="r.contra" :abstencion="r.abstencion" :total="r.total" large show-labels />
            
            <div class="vote-totals">
              <span class="vote-total-item vote-total-item--favor">{{ r.favor }} a favor</span>
              <span class="vote-total-item vote-total-item--contra">{{ r.contra }} en contra</span>
              <span class="vote-total-item vote-total-item--abstencion">{{ r.abstencion }} abstenciones</span>
              <span class="vote-total-item vote-total-item--total">Total: {{ r.total }} votos</span>
            </div>
          </div>

          <!-- Group breakdown -->
          <div class="detail-section">
            <h2>Por grupos parlamentarios</h2>
            <p v-if="votosReady && !hasNominalVotes" class="empty-state-text" style="padding:0.75rem 0 0.25rem">
              {{ noNominalVotesMessage }}
            </p>
            <div v-else-if="votosReady" class="groups-grid">
              <div
                v-for="gIdx in sortedGroups"
                :key="gIdx"
                class="group-result-card"
                :class="{ 'tr--highlighted': normalize(grupos[gIdx]) === normalize(highlightedGroup) }"
              >
                <div class="group-result-header">
                  <router-link :to="'/grupo/' + encodeURIComponent(grupos[gIdx])" class="group-name">
                    {{ getGroupInfo(grupos[gIdx]).label }}
                  </router-link>
                  <div style="display:flex;align-items:center;gap:0.45rem">
                    <span v-if="groupMajorityCode(gIdx) != null" class="voto-pill" :class="votoPillClass(groupMajorityCode(gIdx))">
                      {{ VOTO_LABELS[groupMajorityCode(gIdx)] }}
                    </span>
                    <span class="group-total">{{ byGroup[gIdx].total }} diputados</span>
                    <button
                      class="btn-share-vote"
                      title="Copiar enlace del voto de este partido"
                      @click="copyGroupLink(gIdx)"
                    >
                      {{ copiedGroup === gIdx ? '✅' : '🔗' }}
                    </button>
                  </div>
                </div>
                <VoteBar 
                  :favor="byGroup[gIdx][1]" 
                  :contra="byGroup[gIdx][2]" 
                  :abstencion="byGroup[gIdx][3]" 
                  :total="byGroup[gIdx].total" 
                  small 
                />
              </div>
            </div>
            <div v-else class="loading-wrap"><div class="loading-spinner"></div></div>
          </div>

          <!-- Individual votes -->
          <div class="detail-section">
            <div class="votes-header">
              <h2>Votos individuales</h2>
              <div class="votes-search-wrap">
                <input 
                  v-if="hasNominalVotes"
                  v-model="dipSearch" 
                  type="search" 
                  class="filter-input" 
                  placeholder="Buscar diputado..."
                >
              </div>
            </div>

            <p v-if="votosReady && !hasNominalVotes" class="empty-state-text" style="padding:0.75rem 0 0.25rem">
              {{ noNominalVotesMessage }}
            </p>
            <div v-else-if="votosReady" class="table-wrap">
              <table class="responsive-table">
                <thead>
                  <tr>
                    <th>Representante</th>
                    <th>Grupo</th>
                    <th>Voto</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="vi in filteredVotes" 
                    :key="vi"
                    :class="{ 'tr--highlighted': diputados[votos[vi][1]] === highlightedDip }"
                  >
                    <td data-label="Representante">
                      <router-link :to="'/diputado/' + encodeURIComponent(diputados[votos[vi][1]])">
                        {{ diputados[votos[vi][1]] }}
                      </router-link>
                    </td>
                    <td data-label="Grupo">
                      {{ getGroupInfo(grupos[votos[vi][2]]).label }}
                    </td>
                    <td data-label="Voto">
                      <span class="voto-pill" :class="votoPillClass(votos[vi][3])">
                        {{ VOTO_LABELS[votos[vi][3]] }}
                      </span>
                    </td>
                    <td class="text-right">
                      <button 
                        class="btn-share-vote" 
                        title="Copiar enlace a este voto"
                        @click="copyVoteLink(vi)"
                      >
                        {{ copiedVi === vi ? '✅' : '🔗' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-if="filteredVotes.length === 0" class="empty-state-text" style="padding:2rem">
                No se encontraron representantes con ese nombre.
              </p>
            </div>
            <div v-else class="loading-wrap"><div class="loading-spinner"></div></div>
          </div>
        </div>

        <aside class="vote-sidebar">
          <!-- Expediente / Dossier Summary -->
          <div v-if="expGroup" class="exp-summary-card">
            <h3 class="mb-2">Dossier Legislativo</h3>
            <p class="exp-summary-intro">
              Esta votación forma parte de un expediente con <strong>{{ expGroup.total }}</strong> votaciones.
            </p>

            <div v-if="expGroup.finalItem" class="exp-final-result">
              <div class="exp-final-info">
                <span class="exp-final-label">Resultado Final:</span>
                <ResultBadge :result="expGroup.finalItem.res.result" size="sm" />
              </div>
              <router-link :to="'/votacion/' + expGroup.finalItem.vot.id" class="exp-final-link">
                Ver ley final &rarr;
              </router-link>
            </div>
            <div v-else class="exp-no-final">
              Todavía no hay una votación final registrada para este expediente.
            </div>

            <div class="exp-ratio">
              <div class="exp-ratio-bar">
                <div class="exp-ratio-seg exp-ratio-seg--aprobada" :style="{ width: (expGroup.aprobadas / expGroup.total * 100) + '%' }"></div>
              </div>
              <div class="exp-ratio-text">
                {{ expGroup.aprobadas }} aprobadas, {{ expGroup.rechazadas }} rechazadas
              </div>
            </div>

            <div class="exp-tipos">
              <div v-for="t in expGroup.tipos" :key="t.id" class="exp-tipo-group">
                <button class="exp-tipo-header" @click="toggleTipo(t.id)">
                  <span class="exp-tipo-arrow">{{ expandedTipos[t.id] ? '▼' : '▶' }}</span>
                  <span class="exp-tipo-label">{{ t.label }}</span>
                  <span class="exp-tipo-count">({{ t.items.length }})</span>
                </button>
                <div v-if="expandedTipos[t.id]" class="exp-tipo-items">
                  <router-link 
                    v-for="item in t.items" 
                    :key="item.idx"
                    :to="'/votacion/' + item.vot.id"
                    class="exp-tipo-item"
                    :class="{ 'exp-tipo-item--current': item.idx === idx }"
                  >
                    <span class="exp-tipo-item-text" :title="item.vot.titulo_ciudadano">
                      {{ item.vot.titulo_ciudadano }}
                    </span>
                    <span class="exp-tipo-result">
                      {{ item.res.result === 'Aprobada' ? '✅' : '❌' }}
                    </span>
                  </router-link>
                </div>
              </div>
            </div>
          </div>

          <div class="detail-section sticky-sidebar">
            <h3>Compartir</h3>
            <p class="small text-muted mb-3">Ayuda a difundir la actividad parlamentaria compartiendo esta votación.</p>
            <ShareBar
              :title="vot.titulo_ciudadano"
              :result="r?.result || null"
              :share-url="shareUrl"
              :share-text="shareText"
            />
          </div>
        </aside>
      </div>
    </div>
  </section>
  <ViewState v-else-if="notFound" type="404" />
  <ViewState v-else type="loading" />
</template>

<style scoped>
.detail-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.embed-box {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.embed-code-wrap {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

.embed-code {
  flex: 1;
  font-family: monospace;
  font-size: 0.75rem;
  padding: 0.5rem;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  resize: none;
  height: 60px;
}

.embed-code:focus {
  outline: none;
  border-color: var(--color-primary);
}

.detail-summary {
  font-size: 1rem;
  color: var(--color-muted);
  line-height: 1.5;
}

.detail-highlight-vote {
  margin: 0.5rem 0 0;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  font-size: 0.9rem;
  color: var(--color-text);
}

.deduced-note {
  margin-top: 0.75rem;
  padding: 0.6rem 0.85rem;
  background: var(--color-primary-lighter);
  border-radius: var(--radius-sm);
  display: flex;
  gap: 0.6rem;
  align-items: flex-start;
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-primary-light);
}

.deduced-note p { margin: 0; line-height: 1.4; }
.deduced-icon { font-size: 1rem; flex-shrink: 0; }

.detail-subgrupo {
  margin: 0.25rem 0 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  font-style: italic;
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

.detail-section h2 {
  font-size: 1.15rem;
  margin-bottom: 0.75rem;
}

.detail-oficial {
  margin-top: 0.5rem;
}

.texto-oficial {
  margin: 0 0 0.75rem;
  padding: 0.85rem 1rem;
  background: var(--color-primary-lighter);
  border-left: 3px solid var(--color-primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 0.88rem;
  line-height: 1.6;
}

.link-external {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
  font-style: italic;
}

.link-external:hover { text-decoration: underline; }

.vote-totals {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-top: 0.5rem;
  font-size: 0.85rem;
}

.vote-total-item { font-weight: 600; }
.vote-total-item--favor { color: var(--color-favor); }
.vote-total-item--contra { color: var(--color-contra); }
.vote-total-item--abstencion { color: var(--color-abstencion); }
.vote-total-item--total { color: var(--color-muted); font-weight: 400; }

.exp-summary-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.25rem;
}

.exp-summary-intro {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.exp-final-result {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  background: #f0fdf4;
  border-radius: var(--radius-sm);
  margin-bottom: 1rem;
}

[data-theme="dark"] .exp-final-result {
  background: #022c22;
}

.exp-final-label {
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--color-text);
}

.exp-final-link {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
  margin-left: auto;
}

.exp-final-link:hover { text-decoration: underline; }

.exp-no-final {
  padding: 0.6rem 0.85rem;
  background: var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  color: var(--color-muted);
  margin-bottom: 1rem;
}

.exp-ratio { margin-bottom: 1rem; }

.exp-ratio-bar {
  height: 8px;
  background: var(--color-contra-light);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.35rem;
}

.exp-ratio-seg { height: 100%; }
.exp-ratio-seg--aprobada { background: var(--color-favor); }

.exp-ratio-text {
  font-size: 0.8rem;
  color: var(--color-muted);
}

.exp-tipos {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.exp-tipo-group {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.exp-tipo-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--color-text);
  text-align: left;
  transition: background 0.1s;
}

.exp-tipo-header:hover {
  background: var(--color-primary-lighter);
}

.exp-tipo-arrow {
  font-size: 0.65rem;
  color: var(--color-muted);
  width: 1em;
}

.exp-tipo-count {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
}

.exp-tipo-result {
  margin-left: auto;
  font-size: 0.78rem;
  color: var(--color-favor);
  font-weight: 600;
}

.exp-tipo-items {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--color-border);
}

.exp-tipo-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.75rem 0.4rem 2rem;
  text-decoration: none;
  color: var(--color-text);
  font-size: 0.82rem;
  border-bottom: 1px solid var(--color-border);
  transition: background 0.1s;
}

.exp-tipo-item:last-child { border-bottom: none; }
.exp-tipo-item:hover { background: var(--color-primary-lighter); }

.exp-tipo-item--current {
  background: var(--color-primary-light);
  font-weight: 600;
}

.exp-tipo-item-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-share-vote {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0.2rem 0.4rem;
  border-radius: var(--radius-sm);
  opacity: 0.5;
  transition: opacity 0.15s;
}

.btn-share-vote:hover {
  opacity: 1;
  background: var(--color-primary-light);
}

.tr--highlighted {
  background: var(--color-primary-light) !important;
  animation: highlight-fade 3s ease-out;
}

@keyframes highlight-fade {
  0% { background: var(--color-primary-light); }
  70% { background: var(--color-primary-light); }
  100% { background: transparent; }
}

.result-margin {
  font-size: 0.95rem;
  color: var(--color-muted);
  margin-left: 0.75rem;
}

@media (max-width: 768px) {
  .detail-meta { flex-direction: column; align-items: flex-start; }
  .exp-final-result { flex-wrap: wrap; }
  .exp-tipo-item-text { white-space: normal; }
  .exp-tipo-item { padding-left: 1.5rem; }
}
</style>
