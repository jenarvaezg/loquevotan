<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, debounce, VOTO_LABELS, resultMarginText } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'
import ShareBar from '../components/ShareBar.vue'

const route = useRoute()
const { votaciones, votResults, votos, votosByVotacion, categorias, grupos, diputados } = useData()

const idx = computed(() => parseInt(route.params.idx, 10))
const vot = computed(() => votaciones.value[idx.value])
const r = computed(() => votResults.value[idx.value])
const dipSearch = ref('')

// Group breakdown
const byGroup = computed(() => {
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
  const indices = votosByVotacion.value[idx.value] || []
  return [...indices].sort((a, b) =>
    diputados.value[votos.value[a][1]].localeCompare(diputados.value[votos.value[b][1]])
  )
})

const filteredVotes = computed(() => {
  const q = dipSearch.value.toLowerCase().trim()
  if (!q) return sortedVoteIndices.value
  return sortedVoteIndices.value.filter(vi => {
    const name = diputados.value[votos.value[vi][1]]
    return name.toLowerCase().includes(q)
  })
})

const onDipSearch = debounce(() => {}, 200)

function votoPillClass(code) {
  return code === 1 ? 'voto-pill--favor' : code === 2 ? 'voto-pill--contra' : 'voto-pill--abstencion'
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
        <div class="detail-meta" style="margin-top:0.75rem">
          <ResultBadge :result="r.result" large />
          <span class="result-margin">{{ resultMarginText(r) }}</span>
          <span class="detail-meta-item">{{ vot.fecha }}</span>
          <span v-if="vot.legislatura" class="badge badge--leg">{{ vot.legislatura }}</span>
          <span v-if="vot.proponente" class="badge badge--proponente">{{ vot.proponente }}</span>
          <span class="badge badge--cat">{{ fmt(categorias[vot.categoria]) }}</span>
          <span v-for="tag in (vot.etiquetas || [])" :key="tag" class="chip">{{ fmt(tag) }}</span>
        </div>
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
                <td><span class="badge badge--grupo">{{ grupos[gIdx] }}</span></td>
                <td>{{ byGroup[gIdx][1] }}</td>
                <td>{{ byGroup[gIdx][2] }}</td>
                <td>{{ byGroup[gIdx][3] }}</td>
                <td>{{ byGroup[gIdx].total }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="detail-section">
        <h2>Votos individuales</h2>
        <input
          v-model="dipSearch"
          type="search"
          class="filter-input"
          placeholder="Buscar diputado/a..."
          style="max-width:350px;margin-bottom:0.75rem"
          @input="onDipSearch"
        >
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Diputado/a</th>
                <th>Grupo</th>
                <th>Voto</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="vi in filteredVotes" :key="vi">
                <td>
                  <router-link :to="'/diputado/' + encodeURIComponent(diputados[votos[vi][1]])">
                    {{ diputados[votos[vi][1]] }}
                  </router-link>
                </td>
                <td><span class="badge badge--grupo">{{ grupos[votos[vi][2]] }}</span></td>
                <td>
                  <span class="voto-pill" :class="votoPillClass(votos[vi][3])">
                    {{ VOTO_LABELS[votos[vi][3]] || '?' }}
                  </span>
                </td>
              </tr>
              <tr v-if="!filteredVotes.length">
                <td colspan="3" class="text-center" style="padding:1.5rem;color:var(--color-muted)">
                  Sin resultados
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
