<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, debounce, LEGISLATURAS, VOTES_PER_PAGE } from '../utils'
import VoteCard from '../components/VoteCard.vue'
import Pagination from '../components/Pagination.vue'
import FilterBar from '../components/FilterBar.vue'

const route = useRoute()
const router = useRouter()
const { votaciones, votResults, categorias, tagCounts, sortedVotIdxByDate } = useData()

const search = ref('')
const catFilter = ref('')
const resultFilter = ref('')
const legFilter = ref('XV')
const tagInput = ref('')
const sortMode = ref('recent')
const selectedTags = ref([])
const page = ref(1)

// Populate filter options
const sortedCategorias = computed(() => [...categorias.value].sort())
const allTags = computed(() => Object.keys(tagCounts.value).sort())

// Apply initial tag from query param
onMounted(() => {
  if (route.query.tag) {
    selectedTags.value = [route.query.tag]
  }
})

watch(() => route.query.tag, (tag) => {
  if (tag && !selectedTags.value.includes(tag)) {
    selectedTags.value = [tag]
    page.value = 1
  }
})

const filtered = computed(() => {
  const s = search.value.toLowerCase().trim()
  const cat = catFilter.value
  const result = resultFilter.value
  const leg = legFilter.value
  const tags = selectedTags.value

  let indices = sortedVotIdxByDate.value.filter(i => {
    const vot = votaciones.value[i]
    if (s && !vot.titulo_ciudadano.toLowerCase().includes(s)) return false
    if (cat && categorias.value[vot.categoria] !== cat) return false
    if (result && votResults.value[i].result !== result) return false
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

const onSearchInput = debounce(() => { page.value = 1 }, 250)

function addTag() {
  const value = tagInput.value.trim()
  if (!value) return
  const tag = value.replace(/ /g, '_')
  if (!selectedTags.value.includes(tag)) {
    selectedTags.value = [...selectedTags.value, tag]
    page.value = 1
  }
  tagInput.value = ''
}

function removeTag(tag) {
  selectedTags.value = selectedTags.value.filter(t => t !== tag)
  page.value = 1
}

function resetFilters() {
  search.value = ''
  catFilter.value = ''
  resultFilter.value = ''
  legFilter.value = ''
  sortMode.value = 'recent'
  tagInput.value = ''
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
            placeholder="Titulo..."
            @input="onSearchInput"
          >
        </div>
        <div class="filter-group">
          <label>Categoria</label>
          <select v-model="catFilter" class="filter-select" @change="page = 1">
            <option value="">Todas</option>
            <option v-for="c in sortedCategorias" :key="c" :value="c">{{ fmt(c) }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Resultado</label>
          <select v-model="resultFilter" class="filter-select" @change="page = 1">
            <option value="">Todos</option>
            <option value="Aprobada">Aprobada</option>
            <option value="Rechazada">Rechazada</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Legislatura</label>
          <select v-model="legFilter" class="filter-select" @change="page = 1">
            <option value="">Todas las legislaturas</option>
            <option v-for="l in LEGISLATURAS" :key="l.id" :value="l.id">{{ l.nombre }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Etiqueta</label>
          <input
            v-model="tagInput"
            type="search"
            class="filter-input"
            placeholder="Ej: subir_pensiones"
            :list="'vots-tags-list'"
            @keydown.enter.prevent="addTag"
            @change="addTag"
          >
          <datalist id="vots-tags-list">
            <option v-for="tag in allTags" :key="tag" :value="fmt(tag)" />
          </datalist>
        </div>
        <div class="filter-group">
          <label>Ordenar</label>
          <select v-model="sortMode" class="filter-select" @change="page = 1">
            <option value="recent">Mas recientes</option>
            <option value="closest">Mas ajustadas</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn btn--sm" @click="resetFilters">Limpiar</button>
        </div>
      </FilterBar>

      <div v-if="selectedTags.length" class="active-tags">
        <span v-for="tag in selectedTags" :key="tag" class="tag-active">
          {{ fmt(tag) }}
          <button type="button" class="tag-remove" @click="removeTag(tag)">&times;</button>
        </span>
      </div>

      <p style="font-size:0.85rem;color:var(--color-muted);margin-bottom:0.75rem">
        {{ filtered.length.toLocaleString('es-ES') }} votaciones
      </p>

      <div class="vote-cards-grid">
        <template v-if="pageItems.length">
          <VoteCard v-for="i in pageItems" :key="i" :idx="i" />
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
