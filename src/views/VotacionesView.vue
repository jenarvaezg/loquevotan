<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, debounce, normalize, LEGISLATURAS, VOTES_PER_PAGE } from '../utils'
import VoteCard from '../components/VoteCard.vue'
import Pagination from '../components/Pagination.vue'
import FilterBar from '../components/FilterBar.vue'
import TagSelect from '../components/TagSelect.vue'

const route = useRoute()
const router = useRouter()
const { votaciones, votResults, categorias, tagCounts, sortedVotIdxByDate, votsByExp } = useData()

const search = ref('')
const catFilter = ref('')
const resultFilter = ref('')
const proponenteFilter = ref('')
const legFilter = ref('XV')
const sortMode = ref('recent')
const selectedTags = ref([])
const page = ref(1)
const groupByExp = ref(true)
const expandedExps = ref({})

// Populate filter options
const sortedCategorias = computed(() => [...categorias.value].sort())
const allTags = computed(() => Object.keys(tagCounts.value).sort())
const allProponentes = computed(() => {
  const set = new Set()
  votaciones.value.forEach(v => {
    if (v.proponente) set.add(v.proponente)
  })
  return Array.from(set).sort()
})

// Apply initial tag from query param
onMounted(() => {
  if (route.query.tag) {
    selectedTags.value = [route.query.tag]
    legFilter.value = ''
  }
})

watch(() => route.query.tag, (tag) => {
  if (tag && !selectedTags.value.includes(tag)) {
    selectedTags.value = [tag]
    legFilter.value = ''
    page.value = 1
  }
})

const filtered = computed(() => {
  const s = normalize(search.value.trim())
  const cat = catFilter.value
  const result = resultFilter.value
  const proponente = proponenteFilter.value
  const leg = legFilter.value
  const tags = selectedTags.value

  let indices = sortedVotIdxByDate.value.filter(i => {
    const vot = votaciones.value[i]
    if (s && !normalize(vot.titulo_ciudadano).includes(s)) return false
    if (cat && categorias.value[vot.categoria] !== cat) return false
    if (result && votResults.value[i].result !== result) return false
    if (proponente && vot.proponente !== proponente) return false
    if (leg && vot.legislatura !== leg) return false
    if (tags.length > 0) {
      const etiquetas = vot.etiquetas || []
      if (!tags.every(t => etiquetas.includes(t))) return false
    }
    return true
  })

  if (sortMode.value === 'closest') {
    indices = [...indices].sort((a, b) => votResults.value[a].margin - votResults.value[b].margin)
  }

  return indices
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / VOTES_PER_PAGE)))

const pageItems = computed(() => {
  const p = Math.min(page.value, totalPages.value)
  const start = (p - 1) * VOTES_PER_PAGE
  return filtered.value.slice(start, start + VOTES_PER_PAGE)
})

// Group page items by expediente
const groupedPageItems = computed(() => {
  if (!groupByExp.value) return pageItems.value.map(i => ({ type: 'single', idx: i }))

  const items = []
  const seen = new Set()
  for (const idx of pageItems.value) {
    const exp = votaciones.value[idx].exp
    if (!exp || !votsByExp.value[exp] || votsByExp.value[exp].length <= 1) {
      items.push({ type: 'single', idx })
      continue
    }
    if (seen.has(exp)) continue
    seen.add(exp)
    // Find all votaciones in this exp that are also in the current filtered set
    const filteredSet = new Set(filtered.value)
    const expIndices = votsByExp.value[exp].filter(i => filteredSet.has(i))
    if (expIndices.length <= 1) {
      items.push({ type: 'single', idx })
      continue
    }
    items.push({ type: 'group', exp, indices: expIndices, primary: idx })
  }
  return items
})

function toggleExp(exp) {
  expandedExps.value = { ...expandedExps.value, [exp]: !expandedExps.value[exp] }
}

const onSearchInput = debounce(() => { page.value = 1 }, 250)

function resetFilters() {
  search.value = ''
  catFilter.value = ''
  resultFilter.value = ''
  proponenteFilter.value = ''
  legFilter.value = ''
  sortMode.value = 'recent'
  selectedTags.value = []
  page.value = 1
  router.replace({ query: {} })
}

function goToPage(p) {
  page.value = p
}
</script>

<template>
  <section>
    <div class="container" style="padding-top:1.5rem">
      <h1 class="mb-2">Votaciones</h1>

      <FilterBar>
        <div class="filter-group">
          <label>Buscar</label>
          <input
            v-model="search"
            type="search"
            class="filter-input"
            data-testid="vot-search"
            placeholder="Titulo..."
            @input="onSearchInput"
          >
        </div>
        <div class="filter-group">
          <label>Categoria</label>
          <select v-model="catFilter" class="filter-select" data-testid="vot-filter-category" @change="page = 1">
            <option value="">Todas</option>
            <option v-for="c in sortedCategorias" :key="c" :value="c">{{ fmt(c) }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Resultado</label>
          <select v-model="resultFilter" class="filter-select" data-testid="vot-filter-result" @change="page = 1">
            <option value="">Todos</option>
            <option value="Aprobada">Aprobada</option>
            <option value="Rechazada">Rechazada</option>
            <option value="Empate">Empate</option>
          </select>
        </div>
        <div v-if="allProponentes.length > 0" class="filter-group">
          <label>Proponente</label>
          <select v-model="proponenteFilter" class="filter-select" data-testid="vot-filter-proponente" @change="page = 1">
            <option value="">Todos</option>
            <option v-for="p in allProponentes" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Legislatura</label>
          <select v-model="legFilter" class="filter-select" data-testid="vot-filter-legislatura" @change="page = 1">
            <option value="">Todas las legislaturas</option>
            <option v-for="l in LEGISLATURAS" :key="l.id" :value="l.id">{{ l.nombre }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Etiqueta</label>
          <TagSelect :tags="allTags" v-model="selectedTags" @update:model-value="page = 1" />
        </div>
        <div class="filter-group">
          <label>Ordenar</label>
          <select v-model="sortMode" class="filter-select" data-testid="vot-filter-sort" @change="page = 1">
            <option value="recent">Más recientes</option>
            <option value="closest">Más ajustadas</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn btn--sm" @click="resetFilters">Limpiar</button>
        </div>
      </FilterBar>

      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.75rem">
        <p style="font-size:0.85rem;color:var(--color-muted);margin:0" data-testid="vot-count">
          {{ filtered.length.toLocaleString('es-ES') }} votaciones
        </p>
        <label style="font-size:0.8rem;color:var(--color-muted);display:flex;align-items:center;gap:0.35rem;margin-left:auto;cursor:pointer">
          <input type="checkbox" v-model="groupByExp"> Agrupar por expediente
        </label>
      </div>

      <div class="vote-cards-grid">
        <template v-if="groupedPageItems.length">
          <template v-for="item in groupedPageItems" :key="item.type === 'single' ? item.idx : item.exp">
            <VoteCard v-if="item.type === 'single'" :idx="item.idx" />
            <div v-else class="exp-group-card">
              <button class="exp-group-header" @click="toggleExp(item.exp)">
                <span class="exp-group-arrow">{{ expandedExps[item.exp] ? '&#9660;' : '&#9654;' }}</span>
                <span class="exp-group-title">{{ votaciones[item.primary].titulo_ciudadano }}</span>
                <span class="badge badge--sm badge--leg">{{ item.indices.length }} votaciones</span>
              </button>
              <template v-if="expandedExps[item.exp]">
                <VoteCard v-for="i in item.indices" :key="i" :idx="i" />
              </template>
              <VoteCard v-else :idx="item.primary" />
            </div>
          </template>
        </template>
        <div v-else class="empty-state">
          <div class="empty-state-icon">&#128270;</div>
          <p class="empty-state-text">No se encontraron votaciones</p>
        </div>
      </div>

      <Pagination :total-pages="totalPages" :current="page" @page="goToPage" />
    </div>
  </section>
</template>

<style scoped>
.vote-cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}

.exp-group-card {
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0;
  overflow: hidden;
}

.exp-group-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  border: none;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  text-align: left;
  font-size: 0.88rem;
  color: var(--color-text);
}

.exp-group-header:hover {
  background: var(--color-primary-lighter);
}

.exp-group-arrow {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--color-muted);
}

.exp-group-title {
  flex: 1;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
