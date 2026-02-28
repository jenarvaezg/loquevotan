<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, normalize, VOTO_LABELS, resultMarginText, subTipoLabel, subTipoBadgeClass, votoPillClass } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import ShareBar from '../components/ShareBar.vue'

const route = useRoute()
const { votaciones, votResults, votos, votosByVotacion, votsByExp, categorias, grupos, diputados, loadVotosForLeg, votosLoaded, votacionDetail } = useData()

const idx = computed(() => parseInt(route.params.idx, 10))
const vot = computed(() => {
  const base = votaciones.value[idx.value]
  if (!base) return base
  const detail = votacionDetail.value[idx.value]
  return detail ? { ...base, ...detail } : base
})
const r = computed(() => votResults.value[idx.value])
const dipSearch = ref('')
const highlightedDip = ref('')

const votosReady = computed(() => {
  if (!vot.value?.legislatura) return false
  return votosLoaded.value.has(vot.value.legislatura)
})

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
  }
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

const copiedVi = ref(null)

function shareVote(vi) {
  const v = votos.value[vi]
  const dipName = diputados.value[v[1]]
  const votoText = VOTO_LABELS[v[3]]
  const titulo = vot.value.titulo_ciudadano
  const url = window.location.origin + import.meta.env.BASE_URL + '#/votacion/' + idx.value + '?dip=' + encodeURIComponent(dipName)
  const text = `${dipName} voto ${votoText.toLowerCase()} en: "${titulo}" - ${url}`

  navigator.clipboard.writeText(text).then(() => {
    copiedVi.value = vi
    setTimeout(() => { copiedVi.value = null }, 2000)
  })
}

// All votaciones in same expediente (including current)
const expGroup = computed(() => {
  if (!vot.value?.exp) return []
  const indices = votsByExp.value[vot.value.exp] || []
  return indices.map(i => ({ idx: i, vot: votaciones.value[i], r: votResults.value[i] }))
})

// Summary stats for the expediente
const expSummary = computed(() => {
  const group = expGroup.value
  if (group.length <= 1) return null

  const total = group.length
  const aprobadas = group.filter(g => g.r.result === 'Aprobada').length
  const rechazadas = total - aprobadas

  // Group by subTipo
  const byTipo = {}
  const TIPO_ORDER = ['final', 'dictamen', 'totalidad', 'enmienda', 'transaccional', 'particular', 'separada', 'propuesta', 'otro', '']
  for (const g of group) {
    const tipo = g.vot.subTipo || ''
    if (!byTipo[tipo]) byTipo[tipo] = { items: [], aprobadas: 0 }
    byTipo[tipo].items.push(g)
    if (g.r.result === 'Aprobada') byTipo[tipo].aprobadas++
  }

  const tipos = TIPO_ORDER
    .filter(t => byTipo[t])
    .map(t => ({
      tipo: t,
      label: subTipoLabel(t) || 'Otras votaciones',
      total: byTipo[t].items.length,
      aprobadas: byTipo[t].aprobadas,
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
        <h1>{{ vot.titulo_ciudadano }}</h1>
        <p v-if="vot.resumen" class="detail-summary">{{ vot.resumen }}</p>
        <p v-if="vot.subgrupo" class="detail-subgrupo">{{ vot.subgrupo }}</p>
        <div class="detail-meta" style="margin-top:0.75rem">
          <ResultBadge :result="r.result" large />
          <span class="result-margin">{{ resultMarginText(r) }}</span>
          <span v-if="vot.subTipo" class="badge" :class="subTipoBadgeClass(vot.subTipo)">{{ subTipoLabel(vot.subTipo) }}</span>
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
        <a v-if="vot.urlCongreso" :href="vot.urlCongreso" target="_blank" rel="noopener" class="link-congreso">
          Ver en congreso.es &nearr;
        </a>
      </div>

      <ShareBar :title="vot.titulo_ciudadano" :result="r.result" />

      <div class="detail-section">
        <h2>Resultado</h2>
        <VoteBar :favor="r.favor" :contra="r.contra" :abstencion="r.abstencion" :total="r.total" />
        <div class="vote-totals">
          <span class="vote-total-item vote-total-item--favor">{{ r.favor }} a favor</span>
          <span class="vote-total-item vote-total-item--contra">{{ r.contra }} en contra</span>
          <span class="vote-total-item vote-total-item--abstencion">{{ r.abstencion }} abstenciones</span>
          <span class="vote-total-item vote-total-item--total">{{ r.total }} votos totales</span>
        </div>
      </div>

      <template v-if="votosReady">
        <div class="detail-section">
          <h2>Votos por grupo parlamentario</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Grupo</th>
                  <th>A favor</th>
                  <th>En contra</th>
                  <th>Abstenciones</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="gIdx in sortedGroups" :key="gIdx">
                  <td><router-link :to="{ path: '/diputados', query: { grupo: grupos[gIdx] } }" class="badge badge--grupo">{{ grupos[gIdx] }}</router-link></td>
                  <td>{{ byGroup[gIdx][1] }}</td>
                  <td>{{ byGroup[gIdx][2] }}</td>
                  <td>{{ byGroup[gIdx][3] }}</td>
                  <td>{{ byGroup[gIdx].total }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
      <div v-else class="detail-section">
        <h2>Votos por grupo parlamentario</h2>
        <div class="loading-wrap" style="padding:2rem"><div class="loading-spinner"></div></div>
      </div>

      <!-- Expediente summary -->
      <div v-if="expSummary" class="detail-section">
        <h2>Contexto del expediente</h2>
        <div class="exp-summary-card">
          <p class="exp-summary-intro">
            Este asunto se tramitó con <strong>{{ expSummary.total }} votaciones</strong> separadas (enmiendas de cada grupo, votos particulares, etc.).
            Esta es una de ellas.
          </p>

          <!-- Final vote highlight -->
          <div v-if="expSummary.finalItem" class="exp-final-result">
            <span class="exp-final-label">Resultado final:</span>
            <ResultBadge :result="expSummary.finalItem.r.result" large />
            <router-link v-if="expSummary.finalItem.idx !== idx" :to="'/votacion/' + expSummary.finalItem.idx" class="exp-final-link">
              Ver votacion final &rarr;
            </router-link>
            <span v-else class="badge badge--final">Estás viéndola</span>
          </div>
          <div v-else class="exp-no-final">
            No se registró votación final en el pleno (pudo aprobarse por asentimiento o en otra sesión).
          </div>

          <!-- Approval ratio bar -->
          <div class="exp-ratio">
            <div class="exp-ratio-bar">
              <div class="exp-ratio-seg exp-ratio-seg--aprobada" :style="{ width: (expSummary.aprobadas / expSummary.total * 100) + '%' }"></div>
            </div>
            <span class="exp-ratio-text">{{ expSummary.aprobadas }} aprobadas / {{ expSummary.rechazadas }} rechazadas</span>
          </div>

          <!-- Grouped by tipo -->
          <div class="exp-tipos">
            <div v-for="t in expSummary.tipos" :key="t.tipo" class="exp-tipo-group">
              <button class="exp-tipo-header" @click="toggleTipo(t.tipo)">
                <span class="exp-tipo-arrow">{{ expandedTipos[t.tipo] ? '&#9660;' : '&#9654;' }}</span>
                <span class="badge badge--sm" :class="subTipoBadgeClass(t.tipo)">{{ t.label }}</span>
                <span class="exp-tipo-count">{{ t.total }} votaciones</span>
                <span class="exp-tipo-result">{{ t.aprobadas }} aprobadas</span>
              </button>
              <div v-if="expandedTipos[t.tipo]" class="exp-tipo-items">
                <router-link
                  v-for="item in t.items"
                  :key="item.idx"
                  :to="'/votacion/' + item.idx"
                  class="exp-tipo-item"
                  :class="{ 'exp-tipo-item--current': item.idx === idx }"
                >
                  <ResultBadge :result="item.r.result" />
                  <span class="exp-tipo-item-text">{{ item.vot.subgrupo || item.vot.titulo_ciudadano }}</span>
                </router-link>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template v-if="votosReady">
        <div class="detail-section">
          <h2>Votos individuales</h2>
          <input
            v-model="dipSearch"
            type="search"
            class="filter-input"
            placeholder="Buscar diputado/a..."
            style="max-width:350px;margin-bottom:0.75rem"
          >
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Diputado/a</th>
                  <th>Grupo</th>
                  <th>Voto</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="vi in filteredVotes" :key="vi" :class="{ 'tr--highlighted': highlightedDip && diputados[votos[vi][1]] === highlightedDip }">
                  <td>
                    <router-link :to="'/diputado/' + encodeURIComponent(diputados[votos[vi][1]])">
                      {{ diputados[votos[vi][1]] }}
                    </router-link>
                  </td>
                  <td><router-link :to="{ path: '/diputados', query: { grupo: grupos[votos[vi][2]] } }" class="badge badge--grupo">{{ grupos[votos[vi][2]] }}</router-link></td>
                  <td>
                    <span class="voto-pill" :class="votoPillClass(votos[vi][3])">
                      {{ VOTO_LABELS[votos[vi][3]] || '?' }}
                    </span>
                  </td>
                  <td>
                    <button class="btn-share-vote" :title="copiedVi === vi ? 'Copiado!' : 'Compartir voto'" @click.prevent="shareVote(vi)">
                      {{ copiedVi === vi ? '&#10003;' : '&#128279;' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="!filteredVotes.length">
                  <td colspan="4" class="text-center" style="padding:1.5rem;color:var(--color-muted)">
                    Sin resultados
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
      <div v-else class="detail-section">
        <h2>Votos individuales</h2>
        <div class="loading-wrap" style="padding:2rem"><div class="loading-spinner"></div></div>
      </div>
    </div>
  </section>
</template>
