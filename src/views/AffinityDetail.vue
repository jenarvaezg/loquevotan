<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, VOTO_LABELS, VOTES_PER_PAGE, votoPillClass, getGroupInfo } from '../utils'
import ResultBadge from '../components/ResultBadge.vue'
import Pagination from '../components/Pagination.vue'
import ViewState from '../components/ViewState.vue'

const route = useRoute()
const { grupos, votaciones, votos, votosByVotacion, votResults, categorias, loadVotosForLeg, votosLoaded } = useData()

const gaName = computed(() => route.query.ga ? decodeURIComponent(route.query.ga) : '')
const gbName = computed(() => route.query.gb ? decodeURIComponent(route.query.gb) : '')
const leg = computed(() => route.query.leg || '')

const gaIdx = computed(() => grupos.value.indexOf(gaName.value))
const gbIdx = computed(() => grupos.value.indexOf(gbName.value))

const gaInfo = computed(() => getGroupInfo(gaName.value))
const gbInfo = computed(() => getGroupInfo(gbName.value))

const valid = computed(() => gaIdx.value >= 0 && gbIdx.value >= 0 && leg.value)
const votosReady = computed(() => votosLoaded.value.has(leg.value))

watch(leg, (l) => { if (l) loadVotosForLeg(l) }, { immediate: true })

watch([gaName, gbName, leg], ([a, b, l]) => {
  if (a && b && l) {
    const labelA = getGroupInfo(a).label
    const labelB = getGroupInfo(b).label
    document.title = `${labelA} vs ${labelB} | Lo Que Votan`
  }
}, { immediate: true })

function groupMajority(votIndices, gIdx) {
  const counts = { 1: 0, 2: 0, 3: 0 }
  for (const vi of votIndices) {
    const v = votos.value[vi]
    if (v[2] === gIdx) counts[v[3]] = (counts[v[3]] || 0) + 1
  }
  const total = counts[1] + counts[2] + counts[3]
  if (total === 0) return null
  return Number(Object.entries(counts).reduce((a, b) => b[1] > a[1] ? b : a)[0])
}

// Each item: { votIdx, vot, result, majorityA, majorityB, coincide }
const classified = computed(() => {
  if (!valid.value || !votosReady.value) return []
  const result = []
  for (let i = 0; i < votaciones.value.length; i++) {
    const vot = votaciones.value[i]
    if (vot.legislatura !== leg.value) continue
    const indices = votosByVotacion.value[i] || []
    const majA = groupMajority(indices, gaIdx.value)
    const majB = groupMajority(indices, gbIdx.value)
    if (majA === null || majB === null) continue
    result.push({ votIdx: i, vot, result: votResults.value[i], majorityA: majA, majorityB: majB, coincide: majA === majB })
  }
  return result
})

const totalCount = computed(() => classified.value.length)
const coincidenCount = computed(() => classified.value.filter(x => x.coincide).length)
const diferencCount = computed(() => classified.value.filter(x => !x.coincide).length)

const activeTab = ref('todas')
const page = ref(1)

const filtered = computed(() => {
  if (activeTab.value === 'coinciden') return classified.value.filter(x => x.coincide)
  if (activeTab.value === 'difieren') return classified.value.filter(x => !x.coincide)
  return classified.value
})

watch(activeTab, () => { page.value = 1 })

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / VOTES_PER_PAGE)))

const pageItems = computed(() => {
  const p = Math.min(page.value, totalPages.value)
  const start = (p - 1) * VOTES_PER_PAGE
  return filtered.value.slice(start, start + VOTES_PER_PAGE)
})
</script>

<template>
  <section v-if="valid && votosReady">
    <div class="container" style="padding-top:1.5rem">
      <router-link to="/grupos" class="back-link">&larr; Afinidad entre partidos</router-link>

      <div class="detail-header">
        <h1>
          <span :style="{ color: gaInfo.color }">{{ gaInfo.label }}</span>
          <span style="color:var(--color-muted);font-weight:400;margin:0 0.75rem">vs</span>
          <span :style="{ color: gbInfo.color }">{{ gbInfo.label }}</span>
        </h1>
        <div class="detail-meta" style="margin-top:0.5rem">
          <span class="badge badge--leg">{{ leg }}</span>
        </div>
      </div>

      <div class="stat-cards">
        <div class="stat-card">
          <span class="stat-card-value">{{ totalCount }}</span>
          <span class="stat-card-label">Votaciones</span>
        </div>
        <div class="stat-card stat-card--favor">
          <span class="stat-card-value">{{ coincidenCount }}</span>
          <span class="stat-card-label">Coinciden ({{ totalCount ? Math.round(coincidenCount / totalCount * 100) : 0 }}%)</span>
        </div>
        <div class="stat-card stat-card--contra">
          <span class="stat-card-value">{{ diferencCount }}</span>
          <span class="stat-card-label">Difieren ({{ totalCount ? Math.round(diferencCount / totalCount * 100) : 0 }}%)</span>
        </div>
      </div>

      <div class="detail-section">
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
          <button
            v-for="tab in [['todas','Todas'],['coinciden','Coinciden'],['difieren','Difieren']]"
            :key="tab[0]"
            class="chip chip--lg chip--clickable"
            :class="{ 'chip--active': activeTab === tab[0] }"
            @click="activeTab = tab[0]"
          >{{ tab[1] }}</button>
        </div>

        <ViewState
          v-if="filtered.length === 0"
          type="empty"
          icon="&#128202;"
          message="No hay votaciones para mostrar."
          :padded="false"
        />

        <div v-for="item in pageItems" :key="item.votIdx" class="vot-card">
          <div class="vot-card-header">
            <span class="badge badge--leg" style="margin-right:0.4rem">{{ item.vot.fecha }}</span>
            <span v-if="item.vot.categoria != null" class="badge badge--cat">{{ fmt(categorias[item.vot.categoria]) }}</span>
          </div>
          <router-link :to="'/votacion/' + item.vot.id" class="vot-card-title card-link">
            {{ item.vot.titulo_ciudadano }}
          </router-link>
          <div style="display:flex;gap:0.75rem;flex-wrap:wrap;align-items:center;margin-top:0.5rem">
            <span style="font-size:0.8rem;color:var(--color-muted);font-weight:600" :style="{ color: gaInfo.color }">{{ gaInfo.label }}:</span>
            <span class="voto-pill" :class="votoPillClass(item.majorityA)">{{ VOTO_LABELS[item.majorityA] }}</span>
            <span style="font-size:0.8rem;color:var(--color-muted);font-weight:600" :style="{ color: gbInfo.color }">{{ gbInfo.label }}:</span>
            <span class="voto-pill" :class="votoPillClass(item.majorityB)">{{ VOTO_LABELS[item.majorityB] }}</span>
            <ResultBadge v-if="item.result" :result="item.result.result" style="margin-left:auto" />
          </div>
        </div>

        <Pagination :total-pages="totalPages" :current="page" @page="p => page = p" />
      </div>
    </div>
  </section>

  <ViewState v-else-if="!votosReady && valid" type="loading" />

  <section v-else>
    <div class="container" style="padding-top:3rem">
      <ViewState
        type="empty"
        icon="&#128202;"
        title="Grupos no encontrados"
        message="Los grupos parlamentarios o la legislatura indicados no existen."
        action-label="Ver partidos"
        action-to="/grupos"
      />
    </div>
  </section>
</template>

<style scoped>
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

.detail-section {
  margin-top: 2rem;
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

.vot-card {
  padding: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 0.75rem;
}

.vot-card-header {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-bottom: 0.35rem;
}

.vot-card-title {
  font-weight: 600;
  font-size: 0.95rem;
  line-height: 1.4;
  display: block;
}

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .stat-card-value { font-size: 1.35rem; }
  .detail-meta { flex-direction: column; align-items: flex-start; }
}
</style>
