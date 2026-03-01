<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { pct, normalize, dipPhotoUrl, avatarStyle, avatarInitials, VOTO_LABELS, VOTES_PER_PAGE, votoPillClass } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import Pagination from '../components/Pagination.vue'
import ViewState from '../components/ViewState.vue'

const route = useRoute()
const router = useRouter()
const { diputados, grupos, dipStats, dipFotos, votos, votaciones, votResults, votosByDiputado, loadVotosForLeg, votosLoaded } = useData()

// Deputy selection state
const searchA = ref('')
const searchB = ref('')
const showDropA = ref(false)
const showDropB = ref(false)

const dipIdxA = ref(-1)
const dipIdxB = ref(-1)

// Initialize from URL query params
watch(diputados, (dips) => {
  if (!dips.length) return
  const a = route.query.a ? decodeURIComponent(route.query.a) : ''
  const b = route.query.b ? decodeURIComponent(route.query.b) : ''
  if (a) {
    const idx = dips.indexOf(a)
    if (idx >= 0) { dipIdxA.value = idx; searchA.value = a }
  }
  if (b) {
    const idx = dips.indexOf(b)
    if (idx >= 0) { dipIdxB.value = idx; searchB.value = b }
  }
}, { immediate: true })

// Update URL when both selected
watch([dipIdxA, dipIdxB], ([a, b]) => {
  if (a >= 0 && b >= 0) {
    router.replace({
      query: {
        a: encodeURIComponent(diputados.value[a]),
        b: encodeURIComponent(diputados.value[b]),
      }
    })
  }
})

// Autocomplete filtered lists
const filteredA = computed(() => {
  const q = normalize(searchA.value.trim())
  if (!q) return []
  return diputados.value
    .map((name, idx) => ({ name, idx }))
    .filter(d => normalize(d.name).includes(q))
    .slice(0, 8)
})

const filteredB = computed(() => {
  const q = normalize(searchB.value.trim())
  if (!q) return []
  return diputados.value
    .map((name, idx) => ({ name, idx }))
    .filter(d => normalize(d.name).includes(q))
    .slice(0, 8)
})

function selectA(idx) {
  dipIdxA.value = idx
  searchA.value = diputados.value[idx]
  showDropA.value = false
}

function selectB(idx) {
  dipIdxB.value = idx
  searchB.value = diputados.value[idx]
  showDropB.value = false
}

function onInputA() {
  dipIdxA.value = -1
  showDropA.value = true
}

function onInputB() {
  dipIdxB.value = -1
  showDropB.value = true
}

function blurA() { setTimeout(() => { showDropA.value = false }, 150) }
function blurB() { setTimeout(() => { showDropB.value = false }, 150) }

// Derived stats
const dsA = computed(() => dipIdxA.value >= 0 ? dipStats.value[dipIdxA.value] : null)
const dsB = computed(() => dipIdxB.value >= 0 ? dipStats.value[dipIdxB.value] : null)
const bothSelected = computed(() => dipIdxA.value >= 0 && dipIdxB.value >= 0 && dipIdxA.value !== dipIdxB.value)
const sameSelected = computed(() => dipIdxA.value >= 0 && dipIdxA.value === dipIdxB.value)

const photoA = computed(() => dipPhotoUrl(dipFotos.value[dipIdxA.value]))
const photoB = computed(() => dipPhotoUrl(dipFotos.value[dipIdxB.value]))

const grupoA = computed(() => dsA.value?.mainGrupo >= 0 ? grupos.value[dsA.value.mainGrupo] : 'Sin grupo')
const grupoB = computed(() => dsB.value?.mainGrupo >= 0 ? grupos.value[dsB.value.mainGrupo] : 'Sin grupo')

// Load votos for both deputies
watch(dsA, (stats) => {
  if (stats?.legislaturas?.length) {
    stats.legislaturas.forEach(leg => loadVotosForLeg(leg))
  }
}, { immediate: true })

watch(dsB, (stats) => {
  if (stats?.legislaturas?.length) {
    stats.legislaturas.forEach(leg => loadVotosForLeg(leg))
  }
}, { immediate: true })

const votosReadyA = computed(() => {
  if (!dsA.value?.legislaturas?.length) return false
  return dsA.value.legislaturas.every(leg => votosLoaded.value.has(leg))
})

const votosReadyB = computed(() => {
  if (!dsB.value?.legislaturas?.length) return false
  return dsB.value.legislaturas.every(leg => votosLoaded.value.has(leg))
})

const votosReady = computed(() => bothSelected.value && votosReadyA.value && votosReadyB.value)

// Build vote maps and find shared votaciones
const sharedVotaciones = computed(() => {
  if (!votosReady.value) return []

  const votByA = {}
  const indicesA = votosByDiputado.value[dipIdxA.value] || []
  for (let i = 0; i < indicesA.length; i++) {
    const v = votos.value[indicesA[i]]
    votByA[v[0]] = v[3]
  }

  const votByB = {}
  const indicesB = votosByDiputado.value[dipIdxB.value] || []
  for (let i = 0; i < indicesB.length; i++) {
    const v = votos.value[indicesB[i]]
    votByB[v[0]] = v[3]
  }

  const shared = []
  for (const votIdxStr of Object.keys(votByA)) {
    const votIdx = Number(votIdxStr)
    if (votIdx in votByB) {
      shared.push({
        votIdx,
        codeA: votByA[votIdx],
        codeB: votByB[votIdx],
        coinciden: votByA[votIdx] === votByB[votIdx],
      })
    }
  }

  return shared.sort((a, b) =>
    votaciones.value[b.votIdx].fecha.localeCompare(votaciones.value[a.votIdx].fecha)
  )
})

const coincidencias = computed(() => sharedVotaciones.value.filter(r => r.coinciden).length)
const agreementPct = computed(() => {
  const total = sharedVotaciones.value.length
  if (!total) return '0%'
  return pct(coincidencias.value / total)
})

// Filter and pagination
const tableFilter = ref('todas')
const tablePage = ref(1)

const filteredShared = computed(() => {
  if (tableFilter.value === 'coinciden') return sharedVotaciones.value.filter(r => r.coinciden)
  if (tableFilter.value === 'difieren') return sharedVotaciones.value.filter(r => !r.coinciden)
  return sharedVotaciones.value
})

watch(tableFilter, () => { tablePage.value = 1 })
watch(sharedVotaciones, () => { tablePage.value = 1 })

const totalPages = computed(() => Math.max(1, Math.ceil(filteredShared.value.length / VOTES_PER_PAGE)))

const pageItems = computed(() => {
  const p = Math.min(tablePage.value, totalPages.value)
  const start = (p - 1) * VOTES_PER_PAGE
  return filteredShared.value.slice(start, start + VOTES_PER_PAGE)
})
</script>

<template>
  <section>
    <div class="container" style="padding-top:1.5rem">
      <h1 class="mb-2">Comparar diputados</h1>

      <!-- Deputy selector -->
      <div class="comparador-selectors">
        <div class="comparador-selector-col">
          <label class="filter-label">Diputado A</label>
          <div style="position:relative">
            <input
              v-model="searchA"
              type="search"
              class="filter-input"
              placeholder="Buscar diputado..."
              autocomplete="off"
              @input="onInputA"
              @focus="showDropA = true"
              @blur="blurA"
            >
            <div v-if="showDropA && filteredA.length" class="autocomplete-drop">
              <div
                v-for="d in filteredA"
                :key="d.idx"
                class="autocomplete-item"
                @mousedown.prevent="selectA(d.idx)"
              >
                {{ d.name }}
              </div>
            </div>
          </div>
        </div>

        <div class="comparador-vs">VS</div>

        <div class="comparador-selector-col">
          <label class="filter-label">Diputado B</label>
          <div style="position:relative">
            <input
              v-model="searchB"
              type="search"
              class="filter-input"
              placeholder="Buscar diputado..."
              autocomplete="off"
              @input="onInputB"
              @focus="showDropB = true"
              @blur="blurB"
            >
            <div v-if="showDropB && filteredB.length" class="autocomplete-drop">
              <div
                v-for="d in filteredB"
                :key="d.idx"
                class="autocomplete-item"
                @mousedown.prevent="selectB(d.idx)"
              >
                {{ d.name }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <p v-if="sameSelected" class="hint-text" style="color:var(--color-contra);margin-top:0.5rem">
        Selecciona dos diputados distintos para comparar.
      </p>

      <!-- Side-by-side comparison -->
      <template v-if="bothSelected && dsA && dsB">
        <!-- Headers -->
        <div class="comparador-cols" style="margin-top:1.5rem">
          <!-- Deputy A -->
          <div class="comparador-col">
            <div style="display:flex;flex-direction:column;align-items:center;gap:0.75rem;text-align:center">
              <img v-if="photoA" :src="photoA" :alt="diputados[dipIdxA]" class="dip-detail-photo">
              <span v-else class="dip-detail-avatar" :style="avatarStyle(diputados[dipIdxA])">
                {{ avatarInitials(diputados[dipIdxA]) }}
              </span>
              <div>
                <router-link :to="'/diputado/' + encodeURIComponent(diputados[dipIdxA])" class="dip-name-link">
                  {{ diputados[dipIdxA] }}
                </router-link>
                <div style="margin-top:0.35rem">
                  <span class="badge badge--grupo">{{ grupoA }}</span>
                </div>
              </div>
            </div>

            <div class="stat-cards" style="margin-top:1rem">
              <div class="stat-card">
                <span class="stat-card-value">{{ dsA.total }}</span>
                <span class="stat-card-label">Votaciones</span>
              </div>
              <div class="stat-card stat-card--favor">
                <span class="stat-card-value">{{ dsA.favor }}</span>
                <span class="stat-card-label">A favor ({{ pct(dsA.favor / dsA.total) }})</span>
              </div>
              <div class="stat-card stat-card--contra">
                <span class="stat-card-value">{{ dsA.contra }}</span>
                <span class="stat-card-label">En contra ({{ pct(dsA.contra / dsA.total) }})</span>
              </div>
              <div class="stat-card stat-card--abstencion">
                <span class="stat-card-value">{{ dsA.abstencion }}</span>
                <span class="stat-card-label">Abstenciones ({{ pct(dsA.abstencion / dsA.total) }})</span>
              </div>
            </div>
            <VoteBar :favor="dsA.favor" :contra="dsA.contra" :abstencion="dsA.abstencion" :total="dsA.total" />
          </div>

          <!-- Deputy B -->
          <div class="comparador-col">
            <div style="display:flex;flex-direction:column;align-items:center;gap:0.75rem;text-align:center">
              <img v-if="photoB" :src="photoB" :alt="diputados[dipIdxB]" class="dip-detail-photo">
              <span v-else class="dip-detail-avatar" :style="avatarStyle(diputados[dipIdxB])">
                {{ avatarInitials(diputados[dipIdxB]) }}
              </span>
              <div>
                <router-link :to="'/diputado/' + encodeURIComponent(diputados[dipIdxB])" class="dip-name-link">
                  {{ diputados[dipIdxB] }}
                </router-link>
                <div style="margin-top:0.35rem">
                  <span class="badge badge--grupo">{{ grupoB }}</span>
                </div>
              </div>
            </div>

            <div class="stat-cards" style="margin-top:1rem">
              <div class="stat-card">
                <span class="stat-card-value">{{ dsB.total }}</span>
                <span class="stat-card-label">Votaciones</span>
              </div>
              <div class="stat-card stat-card--favor">
                <span class="stat-card-value">{{ dsB.favor }}</span>
                <span class="stat-card-label">A favor ({{ pct(dsB.favor / dsB.total) }})</span>
              </div>
              <div class="stat-card stat-card--contra">
                <span class="stat-card-value">{{ dsB.contra }}</span>
                <span class="stat-card-label">En contra ({{ pct(dsB.contra / dsB.total) }})</span>
              </div>
              <div class="stat-card stat-card--abstencion">
                <span class="stat-card-value">{{ dsB.abstencion }}</span>
                <span class="stat-card-label">Abstenciones ({{ pct(dsB.abstencion / dsB.total) }})</span>
              </div>
            </div>
            <VoteBar :favor="dsB.favor" :contra="dsB.contra" :abstencion="dsB.abstencion" :total="dsB.total" />
          </div>
        </div>

        <!-- Agreement summary -->
        <div v-if="votosReady" class="detail-section" style="text-align:center">
          <p class="agreement-stat">
            Coinciden en <strong>{{ coincidencias }}</strong> de
            <strong>{{ sharedVotaciones.length }}</strong> votaciones compartidas
            (<strong>{{ agreementPct }}</strong>)
          </p>
        </div>

        <!-- Shared votaciones table -->
        <div class="detail-section">
          <h2>Votaciones compartidas</h2>

          <ViewState v-if="!votosReady" type="loading" :padded="false" />

          <template v-else>
            <!-- Filter chips -->
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem">
              <button
                class="chip chip--lg"
                :class="{ 'chip--active': tableFilter === 'todas' }"
                @click="tableFilter = 'todas'"
              >
                Todas ({{ sharedVotaciones.length }})
              </button>
              <button
                class="chip chip--lg"
                :class="{ 'chip--active': tableFilter === 'coinciden' }"
                @click="tableFilter = 'coinciden'"
              >
                Coinciden ({{ coincidencias }})
              </button>
              <button
                class="chip chip--lg"
                :class="{ 'chip--active': tableFilter === 'difieren' }"
                @click="tableFilter = 'difieren'"
              >
                Difieren ({{ sharedVotaciones.length - coincidencias }})
              </button>
            </div>

            <div class="table-wrap">
              <table class="responsive-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Asunto</th>
                    <th>Voto A</th>
                    <th>Voto B</th>
                    <th>Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="rec in pageItems" :key="rec.votIdx">
                    <td data-label="Fecha">{{ votaciones[rec.votIdx].fecha }}</td>
                    <td data-label="Asunto">
                      <router-link :to="'/votacion/' + votaciones[rec.votIdx].id">
                        {{ votaciones[rec.votIdx].titulo_ciudadano }}
                      </router-link>
                    </td>
                    <td data-label="Voto A">
                      <span class="voto-pill" :class="votoPillClass(rec.codeA)">
                        {{ VOTO_LABELS[rec.codeA] || '?' }}
                      </span>
                    </td>
                    <td data-label="Voto B">
                      <span class="voto-pill" :class="votoPillClass(rec.codeB)">
                        {{ VOTO_LABELS[rec.codeB] || '?' }}
                      </span>
                    </td>
                    <td data-label="Resultado">
                      <ResultBadge :result="votResults[rec.votIdx].result" />
                    </td>
                  </tr>
                  <tr v-if="!pageItems.length">
                    <td colspan="5" class="text-center" style="padding:1.5rem;color:var(--color-muted)">
                      Sin votaciones compartidas
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <Pagination :total-pages="totalPages" :current="tablePage" @page="p => tablePage = p" />
          </template>
        </div>
      </template>

      <!-- Placeholder when not both selected -->
      <div v-else-if="!sameSelected" style="margin-top:3rem">
        <ViewState
          type="empty"
          icon="&#9878;"
          message="Selecciona dos diputados para comparar su historial de votos"
          :padded="false"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.comparador-selectors {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
}

.comparador-selector-col {
  flex: 1;
  min-width: 200px;
}

.comparador-vs {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-muted);
  padding-bottom: 0.5rem;
  flex-shrink: 0;
}

.comparador-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

@media (max-width: 640px) {
  .comparador-cols {
    grid-template-columns: 1fr;
  }
  .comparador-selectors {
    flex-direction: column;
  }
  .comparador-vs {
    align-self: center;
  }
}

.comparador-col {
  min-width: 0;
}

.autocomplete-drop {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: 0.375rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  z-index: 100;
  max-height: 280px;
  overflow-y: auto;
}

.autocomplete-item {
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.autocomplete-item:hover {
  background: var(--color-hover, #f3f4f6);
}

.dip-name-link {
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-text);
  text-decoration: none;
}

.dip-name-link:hover {
  text-decoration: underline;
  color: var(--color-primary);
}

.filter-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-muted);
  margin-bottom: 0.35rem;
}

.agreement-stat {
  font-size: 1.1rem;
  color: var(--color-text);
  margin: 0.5rem 0;
}
</style>
