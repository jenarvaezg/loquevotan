<script setup>
import { ref, computed } from 'vue'
import { useData } from '../composables/useData'
import { LEGISLATURAS, affinityColor } from '../utils'

const { grupos, groupAffinityByLeg, loaded } = useData()

const legFilter = ref('XV')

const affinityData = computed(() => {
  const leg = legFilter.value
  const aff = groupAffinityByLeg.value[leg] || groupAffinityByLeg.value[''] || {}

  const groupTotals = {}
  const allGroups = new Set()
  for (const key in aff) {
    const parts = key.split(',')
    const ga = Number(parts[0])
    const gb = Number(parts[1])
    allGroups.add(ga)
    allGroups.add(gb)
    groupTotals[ga] = (groupTotals[ga] || 0) + aff[key].total
    groupTotals[gb] = (groupTotals[gb] || 0) + aff[key].total
  }

  const validGroups = Array.from(allGroups)
    .filter(g => (groupTotals[g] || 0) >= 10)
    .sort((a, b) => a - b)

  return { aff, validGroups }
})

function cellData(ga, gb) {
  if (ga === gb) return { pctStr: '100%', bg: '#e2e8f0', color: 'var(--color-muted)', isSelf: true }
  const key = ga < gb ? ga + ',' + gb : gb + ',' + ga
  const d = affinityData.value.aff[key]
  if (!d || d.total === 0) return { pctStr: '\u2014', bg: '#e2e8f0', color: 'var(--color-muted)', title: 'Sin datos', isSelf: false }
  const pct = d.same / d.total
  const pctStr = Math.round(pct * 100) + '%'
  const title = `${pctStr} (${d.same}/${d.total} votaciones coinciden)`
  const color = pct < 0.2 ? '#fff' : '#1e293b'
  return { pctStr, bg: affinityColor(pct), color, title, isSelf: false }
}
</script>

<template>
  <section>
    <div class="container" style="padding-top:1.5rem">
      <h1 class="mb-2">Afinidad entre grupos parlamentarios</h1>
      <p style="color:var(--color-muted);font-size:0.9rem;margin-bottom:1.25rem">
        Porcentaje de votaciones en las que cada par de grupos votó mayoritariamente igual.
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
                  :style="{ background: cellData(ga, gb).bg, color: cellData(ga, gb).color }"
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

      <div v-else-if="!loaded" class="loading-wrap" style="padding:2rem">
        <div class="loading-spinner"></div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-state-icon">&#128202;</div>
        <p class="empty-state-text">No hay datos suficientes para esta legislatura.</p>
      </div>
    </div>
  </section>
</template>
