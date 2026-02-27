<script setup>
import { ref, computed, watch } from 'vue'
import { useData } from '../composables/useData'
import { LEGISLATURAS, affinityColor } from '../utils'

const { votaciones, votos, votosByVotacion, grupos } = useData()

const legFilter = ref('XV')

const affinityData = computed(() => {
  const leg = legFilter.value

  // Collect valid group indices
  const grupoSet = new Set()
  for (let vi = 0; vi < votaciones.value.length; vi++) {
    if (leg && votaciones.value[vi].legislatura !== leg) continue
    const indices = votosByVotacion.value[vi] || []
    for (let j = 0; j < indices.length; j++) {
      grupoSet.add(votos.value[indices[j]][2])
    }
  }

  // Recompute affinity filtered by legislatura
  const aff = {}
  for (let vi = 0; vi < votaciones.value.length; vi++) {
    if (leg && votaciones.value[vi].legislatura !== leg) continue
    const indices = votosByVotacion.value[vi] || []
    const byGroup = {}
    for (let j = 0; j < indices.length; j++) {
      const v = votos.value[indices[j]]
      const grp = v[2]
      const code = v[3]
      if (!byGroup[grp]) byGroup[grp] = { 1: 0, 2: 0, 3: 0 }
      byGroup[grp][code]++
    }
    const gm = {}
    for (const gIdx in byGroup) {
      const c = byGroup[gIdx]
      gm[gIdx] = c[1] >= c[2] && c[1] >= c[3] ? 1 : c[2] >= c[3] ? 2 : 3
    }
    const gKeys = Object.keys(gm).map(Number)
    for (let a = 0; a < gKeys.length; a++) {
      for (let b = a + 1; b < gKeys.length; b++) {
        const ga = gKeys[a]
        const gb = gKeys[b]
        const key = ga < gb ? ga + ',' + gb : gb + ',' + ga
        if (!aff[key]) aff[key] = { same: 0, total: 0 }
        aff[key].total++
        if (gm[ga] === gm[gb]) aff[key].same++
      }
    }
  }

  // Count total votaciones per group
  const groupTotals = {}
  for (const key in aff) {
    const parts = key.split(',')
    const ga = Number(parts[0])
    const gb = Number(parts[1])
    groupTotals[ga] = (groupTotals[ga] || 0) + aff[key].total
    groupTotals[gb] = (groupTotals[gb] || 0) + aff[key].total
  }

  // Filter groups with >= 10 votaciones
  const validGroups = Array.from(grupoSet)
    .filter(g => (groupTotals[g] || 0) >= 10)
    .sort((a, b) => a - b)

  return { aff, validGroups }
})

function cellData(ga, gb) {
  if (ga === gb) return { pctStr: '100%', bg: '#e2e8f0', isSelf: true }
  const key = ga < gb ? ga + ',' + gb : gb + ',' + ga
  const d = affinityData.value.aff[key]
  if (!d || d.total === 0) return { pctStr: '\u2014', bg: '#e2e8f0', title: 'Sin datos', isSelf: false }
  const pct = d.same / d.total
  const pctStr = Math.round(pct * 100) + '%'
  const title = `${pctStr} (${d.same}/${d.total} votaciones coinciden)`
  return { pctStr, bg: affinityColor(pct), title, isSelf: false }
}

watch(legFilter, () => {}, { immediate: true })
</script>

<template>
  <section>
    <div class="container" style="padding-top:1.5rem">
      <h1 class="mb-2">Afinidad entre grupos parlamentarios</h1>
      <p style="color:var(--color-muted);font-size:0.9rem;margin-bottom:1.25rem">
        Porcentaje de votaciones en las que cada par de grupos voto mayoritariamente igual.
        Se excluyen grupos con menos de 10 votaciones en el periodo seleccionado.
      </p>

      <div class="filter-bar" style="margin-bottom:1.25rem">
        <div class="filter-group">
          <label>Legislatura</label>
          <select v-model="legFilter" class="filter-select">
            <option value="">Todas las legislaturas</option>
            <option v-for="l in LEGISLATURAS" :key="l.id" :value="l.id">{{ l.nombre }}</option>
          </select>
        </div>
      </div>

      <template v-if="affinityData.validGroups.length">
        <div class="affinity-table-wrap">
          <table class="affinity-table">
            <thead>
              <tr>
                <th></th>
                <th v-for="g in affinityData.validGroups" :key="g" class="affinity-th-col">
                  <div class="affinity-th-label">{{ grupos[g] || ('Grupo ' + g) }}</div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ga in affinityData.validGroups" :key="ga">
                <td class="affinity-row-label">{{ grupos[ga] || ('Grupo ' + ga) }}</td>
                <td
                  v-for="gb in affinityData.validGroups"
                  :key="gb"
                  class="affinity-cell"
                  :class="{ 'affinity-cell--self': ga === gb }"
                  :style="{ background: cellData(ga, gb).bg }"
                  :title="cellData(ga, gb).title || cellData(ga, gb).pctStr"
                >
                  {{ cellData(ga, gb).pctStr }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="affinity-legend">
          <span class="affinity-legend-item">
            <span class="affinity-legend-swatch" style="background:#16a34a"></span>&gt;80% coincidencia
          </span>
          <span class="affinity-legend-item">
            <span class="affinity-legend-swatch" style="background:#86efac"></span>60-80%
          </span>
          <span class="affinity-legend-item">
            <span class="affinity-legend-swatch" style="background:#fde047"></span>40-60%
          </span>
          <span class="affinity-legend-item">
            <span class="affinity-legend-swatch" style="background:#fca5a5"></span>20-40%
          </span>
          <span class="affinity-legend-item">
            <span class="affinity-legend-swatch" style="background:#dc2626"></span>&lt;20%
          </span>
        </div>
      </template>

      <div v-else class="empty-state">
        <div class="empty-state-icon">&#128202;</div>
        <p class="empty-state-text">No hay datos suficientes para esta legislatura.</p>
      </div>
    </div>
  </section>
</template>
