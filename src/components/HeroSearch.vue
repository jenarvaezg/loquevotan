<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { debounce, normalize, getGroupInfo, matchSearch, formatFecha } from '../utils'

const props = defineProps({
  showNoResults: { type: Boolean, default: false },
})

const router = useRouter()
const { diputados, grupos, dipStats, votaciones, sortedVotIdxByDate, loaded } = useData()

const query = ref('')
const showDropdown = ref(false)
const highlightIdx = ref(-1)
const dipMatches = ref([])
const votMatches = ref([])
const wrapRef = ref(null)
const noResults = computed(() =>
  loaded.value &&
  query.value.trim().length >= 2 &&
  dipMatches.value.length === 0 &&
  votMatches.value.length === 0
)

const doSearch = debounce((q) => {
  if (q.length < 2) {
    showDropdown.value = false
    return
  }

  const dips = []
  for (let i = 0; i < diputados.value.length && dips.length < 5; i++) {
    if (dipStats.value[i].total === 0) continue
    if (matchSearch(q, diputados.value[i])) dips.push(i)
  }

  const allVots = []
  for (let i = 0; i < votaciones.value.length; i++) {
    if (matchSearch(q, votaciones.value[i].titulo_ciudadano)) allVots.push(i)
  }
  allVots.sort((a, b) => {
    const da = votaciones.value[a].fecha || ''
    const db = votaciones.value[b].fecha || ''
    return db.localeCompare(da)
  })
  const vots = allVots.slice(0, 3)

  dipMatches.value = dips
  votMatches.value = vots
  highlightIdx.value = -1
  showDropdown.value = dips.length > 0 || vots.length > 0 || props.showNoResults
}, 150)

function onInput() {
  doSearch(query.value.trim())
}

// A query typed before the data arrived is searched again once it's loaded.
watch(loaded, (isLoaded) => {
  if (isLoaded && query.value.trim().length >= 2) doSearch(query.value.trim())
})

function onKeydown(e) {
  if (!showDropdown.value) return
  const total = dipMatches.value.length + votMatches.value.length
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlightIdx.value = Math.min(highlightIdx.value + 1, total - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlightIdx.value = Math.max(highlightIdx.value - 1, 0)
  } else if (e.key === 'Enter' && highlightIdx.value >= 0) {
    e.preventDefault()
    selectHighlighted()
  } else if (e.key === 'Escape') {
    showDropdown.value = false
  }
}

function selectHighlighted() {
  const idx = highlightIdx.value
  if (idx < dipMatches.value.length) {
    goToDip(dipMatches.value[idx])
  } else {
    goToVot(votMatches.value[idx - dipMatches.value.length])
  }
}

function goToDip(i) {
  router.push('/diputado/' + encodeURIComponent(diputados.value[i]))
  close()
}

function goToVot(i) {
  router.push('/votacion/' + votaciones.value[i].id)
  close()
}

function close() {
  showDropdown.value = false
  query.value = ''
}

function dipGrupo(i) {
  const mg = dipStats.value[i].mainGrupo
  const raw = mg >= 0 ? grupos.value[mg] : ''
  return getGroupInfo(raw).label
}

function isHighlighted(section, i) {
  const flatIdx = section === 'dip' ? i : dipMatches.value.length + i
  return flatIdx === highlightIdx.value
}

function handleClickOutside(e) {
  if (wrapRef.value && !wrapRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<template>
  <div ref="wrapRef" class="hero-search-wrap">
    <svg class="hero-search-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5L21 21" /></svg>
    <input
      v-model="query"
      type="search"
      class="hero-search"
      placeholder="Diputado o votación"
      aria-label="Buscar diputados y votaciones"
      autocomplete="off"
      @input="onInput"
      @keydown="onKeydown"
    >
    <div v-if="showDropdown" class="autocomplete-dropdown">
      <div v-if="noResults" class="autocomplete-empty">
        No se encontraron diputados ni votaciones con ese texto.
      </div>
      <template v-if="dipMatches.length">
        <div class="ac-section-label">Diputados</div>
        <a
          v-for="(i, pos) in dipMatches"
          :key="'d' + i"
          class="autocomplete-item"
          :class="{ highlighted: isHighlighted('dip', pos) }"
          href="#"
          @click.prevent="goToDip(i)"
        >
          <span>{{ diputados[i] }}</span>
          <span class="ac-grupo">{{ dipGrupo(i) }}</span>
        </a>
      </template>
      <template v-if="votMatches.length">
        <div class="ac-section-label">Votaciones</div>
        <a
          v-for="(i, pos) in votMatches"
          :key="'v' + i"
          class="autocomplete-item"
          :class="{ highlighted: isHighlighted('vot', pos) }"
          href="#"
          @click.prevent="goToVot(i)"
        >
          <span>{{ votaciones[i].titulo_ciudadano }}</span>
          <span class="ac-grupo">{{ formatFecha(votaciones[i].fecha, 'short') }}</span>
        </a>
      </template>
    </div>
  </div>
</template>

<style scoped>
.hero-search-wrap {
  position: relative;
}

.hero-search {
  width: 100%;
  padding: 0.45rem 0.75rem 0.45rem 2.1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
}

.hero-search::placeholder { color: var(--color-muted); }
.hero-search:focus {
  border-color: var(--color-text);
  background: var(--color-surface);
}

.hero-search-icon {
  position: absolute;
  left: 0.65rem;
  top: 50%;
  width: 15px;
  height: 15px;
  transform: translateY(-50%);
  fill: none;
  stroke: var(--color-muted);
  stroke-width: 2;
  stroke-linecap: round;
  pointer-events: none;
}

.autocomplete-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  width: max(100%, 400px);
  max-width: calc(100vw - 32px);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 50;
  max-height: 360px;
  overflow-y: auto;
}

.autocomplete-dropdown[hidden] { display: none; }

.autocomplete-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  color: var(--color-text);
  cursor: pointer;
  transition: background 0.1s;
  text-decoration: none;
  font-size: 0.95rem;
}

.autocomplete-item:hover,
.autocomplete-item.highlighted {
  background: var(--color-primary-light);
  text-decoration: none;
}

.autocomplete-item .ac-grupo {
  font-size: 0.8rem;
  color: var(--color-muted);
}

.ac-section-label {
  padding: 0.4rem 1.25rem 0.2rem;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.autocomplete-empty {
  padding: 0.85rem 1.25rem;
  font-size: 0.9rem;
  color: var(--color-muted);
  background: var(--color-surface);
}
</style>
