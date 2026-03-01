<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, normalize, VOTO_LABELS, resultMarginText, subTipoLabel, subTipoBadgeClass, votoPillClass, getGroupInfo } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import ShareBar from '../components/ShareBar.vue'
import ViewState from '../components/ViewState.vue'

const route = useRoute()
const { votaciones, votResults, votos, votosByVotacion, votsByExp, categorias, grupos, diputados, loadVotosForLeg, votosLoaded, votacionDetail, votIdById, loaded } = useData()

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
const showEmbed = ref(false)

const embedCode = computed(() => {
  if (!vot.value) return ''
  const url = location.origin + location.pathname + `#/widget/${vot.value.id}`
  return `<iframe src="${url}" width="100%" height="250" frameborder="0" style="border:1px solid #e2e8f0; border-radius:8px;"></iframe>`
})

function toggleEmbed() {
  showEmbed.value = !showEmbed.value
}

function copyEmbed() {
  navigator.clipboard.writeText(embedCode.value)
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
  const url = window.location.origin + import.meta.env.BASE_URL + '#/votacion/' + vot.value.id + '?dip=' + encodeURIComponent(dipName)
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
            <button class="btn btn--primary btn--sm" @click="copyEmbed">Copiar código</button>
          </div>
        </div>

        <p v-if="vot.resumen" class="detail-summary" style="margin-top:0.5rem">{{ vot.resumen }}</p>
        
        <!-- Nota explicativa para votos deducidos -->
        <div v-if="vot.metadatos?.tipo === 'deduccion_grupal'" class="deduced-note">
          <span class="deduced-icon">ℹ️</span>
          <p>{{ vot.metadatos.nota }}</p>
        </div>

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
        <a v-if="vot.urlCongreso" :href="vot.urlCongreso" target="_blank" rel="noopener" class="link-external">
          Ver en congreso.es &nearr;
        </a>
        <a v-else-if="vot.urlAndalucia" :href="vot.urlAndalucia" target="_blank" rel="noopener" class="link-external">
          Ver en parlamentodeandalucia.es &nearr;
        </a>
        <a v-else-if="vot.urlCyL" :href="vot.urlCyL" target="_blank" rel="noopener" class="link-external">
          Ver en ccyl.es &nearr;
        </a>
        <a v-else-if="vot.urlMadrid" :href="vot.urlMadrid" target="_blank" rel="noopener" class="link-external">
          Ver en asambleamadrid.es &nearr;
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
                  <td>
                    <router-link :to="{ path: '/diputados', query: { grupo: grupos[gIdx] } }" class="badge" :style="{ backgroundColor: getGroupInfo(grupos[gIdx]).color, color: 'white' }">
                      {{ getGroupInfo(grupos[gIdx]).label }}
                    </router-link>
                  </td>
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
            <router-link v-if="expSummary.finalItem.idx !== idx" :to="'/votacion/' + expSummary.finalItem.vot.id" class="exp-final-link">
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
                  :to="'/votacion/' + item.vot.id"
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
            <table class="responsive-table">
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
                  <td data-label="Diputado/a">
                    <router-link :to="'/diputado/' + encodeURIComponent(diputados[votos[vi][1]])">
                      {{ diputados[votos[vi][1]] }}
                    </router-link>
                  </td>
                  <td data-label="Grupo">
                    <router-link :to="{ path: '/diputados', query: { grupo: grupos[votos[vi][2]] } }" class="badge" :style="{ backgroundColor: getGroupInfo(grupos[votos[vi][2]]).color, color: 'white' }">
                      {{ getGroupInfo(grupos[votos[vi][2]]).label }}
                    </router-link>
                  </td>
                  <td data-label="Voto">
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

  <section v-else-if="notFound">
    <div class="container" style="padding-top:2rem">
      <ViewState
        type="empty"
        icon="&#128269;"
        title="Votación no encontrada"
        message="El identificador no existe en el ámbito actual o la votación ya no está disponible."
        action-label="Ver listado de votaciones"
        action-to="/votaciones"
      />
    </div>
  </section>

  <ViewState v-else type="loading" />
</template>

<style scoped>
.detail-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.detail-header h1 { margin-bottom: 0.35rem; }

.detail-summary {
  font-size: 1rem;
  color: var(--color-muted);
  line-height: 1.5;
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

.embed-box {
  margin: 1rem 0;
  padding: 1rem;
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.embed-code-wrap {
  display: flex;
  gap: 0.5rem;
}

.embed-code {
  flex: 1;
  font-family: monospace;
  font-size: 0.75rem;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  height: 60px;
  resize: none;
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
