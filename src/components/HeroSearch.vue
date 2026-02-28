<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { debounce, normalize, getGroupInfo } from '../utils'

const router = useRouter()
const { diputados, grupos, dipStats, votaciones, sortedVotIdxByDate } = useData()

const query = ref('')
const showDropdown = ref(false)
const highlightIdx = ref(-1)
const dipMatches = ref([])
const votMatches = ref([])
const wrapRef = ref(null)

const doSearch = debounce((q) => {
  if (q.length < 2) {
    showDropdown.value = false
    return
  }

  const norm = normalize(q)

  const dips = []
  for (let i = 0; i < diputados.value.length && dips.length < 5; i++) {
    if (dipStats.value[i].total === 0) continue
    if (normalize(diputados.value[i]).includes(norm)) dips.push(i)
  }

  const vots = []
  const sorted = sortedVotIdxByDate.value
  for (let i = 0; i < sorted.length && vots.length < 3; i++) {
    const idx = sorted[i]
    if (normalize(votaciones.value[idx].titulo_ciudadano).includes(norm)) vots.push(idx)
  }

  dipMatches.value = dips
  votMatches.value = vots
  highlightIdx.value = -1
  showDropdown.value = dips.length > 0 || vots.length > 0
}, 150)

function onInput() {
  doSearch(query.value.trim())
}

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
    <span class="hero-search-icon">&#128269;</span>
    <input
      v-model="query"
      type="search"
      class="hero-search"
      placeholder="Busca diputados y votaciones..."
      autocomplete="off"
      @input="onInput"
      @keydown="onKeydown"
    >
    <div v-if="showDropdown" class="autocomplete-dropdown">
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
          <span class="ac-grupo">{{ votaciones[i].fecha }}</span>
        </a>
      </template>
    </div>
  </div>
</template>

<style scoped>
.hero-search-wrap {
  max-width: 500px;
  margin: 0 auto;
  position: relative;
}

.hero-search {
  width: 100%;
  padding: 0.85rem 1.25rem;
  padding-left: 2.75rem;
  border: 2px solid rgba(255,255,255,0.25);
  border-radius: 50px;
  background: rgba(255,255,255,0.15);
  color: #fff;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}

.hero-search::placeholder { color: rgba(255,255,255,0.6); }
.hero-search:focus {
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.2);
}

.hero-search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.1rem;
  opacity: 0.6;
  pointer-events: none;
}

.autocomplete-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
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
</style>
