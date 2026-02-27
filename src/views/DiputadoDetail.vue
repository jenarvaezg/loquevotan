<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, pct, debounce, VOTO_LABELS, VOTES_PER_PAGE, LEGISLATURAS } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import ShareBar from '../components/ShareBar.vue'
import Pagination from '../components/Pagination.vue'
import AccountabilityCard from '../components/AccountabilityCard.vue'

const route = useRoute()
const router = useRouter()
const { diputados, grupos, dipStats, votos, votaciones, votResults, votosByDiputado, categorias } = useData()

const dipIdx = computed(() => diputados.value.indexOf(decodeURIComponent(route.params.name)))
const name = computed(() => diputados.value[dipIdx.value])
const ds = computed(() => dipStats.value[dipIdx.value])
const grupoName = computed(() =>
  ds.value?.mainGrupo >= 0 ? grupos.value[ds.value.mainGrupo] : 'Sin grupo'
)

// History filters
const histSearch = ref('')
const histVoto = ref('')
const histLeg = ref('')
const histPage = ref(1)
const activeTag = ref('')
const showAccCard = ref(false)
const accTag = ref('')

// Category profile
const catBreakdown = computed(() => {
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
  const indices = votosByDiputado.value[dipIdx.value] || []
  return indices
    .map(vi => {
      const v = votos.value[vi]
      return { votIdx: v[0], code: v[3] }
    })
    .sort((a, b) => votaciones.value[b.votIdx].fecha.localeCompare(votaciones.value[a.votIdx].fecha))
})

const filteredHistory = computed(() => {
  const q = histSearch.value.toLowerCase().trim()
  const votoFilter = histVoto.value
  const legFilter = histLeg.value
  const tag = activeTag.value

  return dipRecords.value.filter(r => {
    if (q && !votaciones.value[r.votIdx].titulo_ciudadano.toLowerCase().includes(q)) return false
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

const onHistSearch = debounce(() => { histPage.value = 1 }, 250)

function resultClass(result) {
  return result === 'Aprobada' ? 'aprobada' : result === 'Rechazada' ? 'rechazada' : 'empate'
}

function votoPillClass(code) {
  return code === 1 ? 'voto-pill--favor' : code === 2 ? 'voto-pill--contra' : 'voto-pill--abstencion'
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

      <div class="detail-header">
        <h1>{{ name }}</h1>
        <div class="detail-meta" style="margin-top:0.5rem">
          <span class="badge badge--grupo">{{ grupoName }}</span>
          <span class="detail-meta-item">{{ ds.total }} votaciones</span>
          <span class="detail-meta-item">Lealtad al grupo: {{ pct(ds.loyalty) }}</span>
          <span v-for="l in ds.legislaturas" :key="l" class="badge badge--leg">{{ l }}</span>
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

      <!-- Category profile -->
      <div v-if="catBreakdown.length" class="detail-section">
        <h2>Perfil tematico</h2>
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
        <h2>Temas mas votados</h2>
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

      <!-- Vote history -->
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
            <option value="3">Abstencion</option>
          </select>
          <select v-model="histLeg" class="filter-select" style="width:auto;min-width:130px" @change="histPage = 1">
            <option value="">Todas las legislaturas</option>
            <option v-for="l in (ds.legislaturas || [])" :key="l" :value="l">{{ l }}</option>
          </select>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Legislatura</th>
                <th>Asunto</th>
                <th>Categoria</th>
                <th>Resultado</th>
                <th>Voto</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in histPageItems" :key="rec.votIdx">
                <td>{{ votaciones[rec.votIdx].fecha }}</td>
                <td>
                  <span v-if="votaciones[rec.votIdx].legislatura" class="badge badge--leg">
                    {{ votaciones[rec.votIdx].legislatura }}
                  </span>
                </td>
                <td>
                  <router-link :to="'/votacion/' + rec.votIdx">
                    {{ votaciones[rec.votIdx].titulo_ciudadano }}
                  </router-link>
                </td>
                <td>
                  <span class="badge badge--cat">
                    {{ fmt(categorias[votaciones[rec.votIdx].categoria]) }}
                  </span>
                </td>
                <td>
                  <ResultBadge :result="votResults[rec.votIdx].result" />
                </td>
                <td>
                  <span class="voto-pill" :class="votoPillClass(rec.code)">
                    {{ VOTO_LABELS[rec.code] || '?' }}
                  </span>
                </td>
              </tr>
              <tr v-if="!histPageItems.length">
                <td colspan="6" class="text-center" style="padding:1.5rem;color:var(--color-muted)">
                  Sin resultados
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <Pagination :total-pages="histTotalPages" :current="histPage" @page="p => histPage = p" />
      </div>

      <ShareBar :title="name + ' - ' + grupoName" />

      <AccountabilityCard
        v-if="showAccCard"
        :dip-idx="dipIdx"
        :tag="accTag"
        @close="closeAccCard"
      />
    </div>
  </section>
</template>
