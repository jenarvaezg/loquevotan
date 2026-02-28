<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { debounce, normalize, DIPS_PER_PAGE } from '../utils'
import DipCard from '../components/DipCard.vue'
import Pagination from '../components/Pagination.vue'
import FilterBar from '../components/FilterBar.vue'

const { diputados, grupos, dipStats } = useData()

const route = useRoute()

const search = ref('')
const grupoFilter = ref('')
const sortMode = ref('name')
const page = ref(1)

// Apply grupo filter from query param
watch(() => route.query.grupo, (g) => {
  if (g) { grupoFilter.value = g; page.value = 1 }
}, { immediate: true })

const sortedGrupos = computed(() => [...grupos.value].sort())

const filtered = computed(() => {
  const s = normalize(search.value.trim())
  const grupo = grupoFilter.value
  const sort = sortMode.value

  let result = []
  for (let i = 0; i < diputados.value.length; i++) {
    const ds = dipStats.value[i]
    if (ds.total === 0) continue
    if (s && !normalize(diputados.value[i]).includes(s)) continue
    if (grupo && (ds.mainGrupo < 0 || grupos.value[ds.mainGrupo] !== grupo)) continue
    result.push(i)
  }

  if (sort === 'name') {
    result.sort((a, b) => diputados.value[a].localeCompare(diputados.value[b]))
  } else if (sort === 'active') {
    result.sort((a, b) => dipStats.value[b].total - dipStats.value[a].total)
  } else if (sort === 'loyalty-low') {
    result.sort((a, b) => dipStats.value[a].loyalty - dipStats.value[b].loyalty)
  }

  return result
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / DIPS_PER_PAGE)))

const pageItems = computed(() => {
  const p = Math.min(page.value, totalPages.value)
  const start = (p - 1) * DIPS_PER_PAGE
  return filtered.value.slice(start, start + DIPS_PER_PAGE)
})

const onSearchInput = debounce(() => { page.value = 1 }, 250)

function resetFilters() {
  search.value = ''
  grupoFilter.value = ''
  sortMode.value = 'name'
  page.value = 1
}

function goToPage(p) {
  page.value = p
}
</script>

<template>
  <section>
    <div class="container" style="padding-top:1.5rem">
      <h1 class="mb-2">Diputados</h1>

      <FilterBar>
        <div class="filter-group">
          <label>Nombre</label>
          <input
            v-model="search"
            type="search"
            class="filter-input"
            placeholder="Apellidos, Nombre..."
            @input="onSearchInput"
          >
        </div>
        <div class="filter-group">
          <label>Grupo</label>
          <select v-model="grupoFilter" class="filter-select" @change="page = 1">
            <option value="">Todos</option>
            <option v-for="g in sortedGrupos" :key="g" :value="g">{{ g }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Ordenar</label>
          <select v-model="sortMode" class="filter-select" @change="page = 1">
            <option value="name">Nombre</option>
            <option value="active">Más activo</option>
            <option value="loyalty-low">Menor lealtad</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn btn--sm" @click="resetFilters">Limpiar</button>
        </div>
      </FilterBar>

      <p style="font-size:0.85rem;color:var(--color-muted);margin-bottom:0.75rem">
        {{ filtered.length.toLocaleString('es-ES') }} diputados
      </p>

      <div class="dip-cards-grid">
        <template v-if="pageItems.length">
          <DipCard v-for="i in pageItems" :key="i" :idx="i" />
        </template>
        <div v-else class="empty-state">
          <div class="empty-state-icon">&#128100;</div>
          <p class="empty-state-text">No se encontraron diputados</p>
        </div>
      </div>

      <Pagination :total-pages="totalPages" :current="page" @page="goToPage" />
    </div>
  </section>
</template>
