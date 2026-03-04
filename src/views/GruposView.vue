<script setup>
import { ref, computed } from 'vue'
import { useData } from '../composables/useData'
import { LEGISLATURAS, affinityColor, getGroupInfo, sanitizeGroupName, isMeaningfulGroupName } from '../utils'
import ViewState from '../components/ViewState.vue'

const { grupos, groupAffinityByLeg, loaded } = useData()

const legFilter = ref('XV')
const mobileGroup = ref('')

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
    .filter(g => {
      if ((groupTotals[g] || 0) < 10) return false
      const groupName = sanitizeGroupName(grupos.value[g])
      return isMeaningfulGroupName(groupName)
    })
    .sort((a, b) => {
      const infoA = getGroupInfo(grupos.value[a])
      const infoB = getGroupInfo(grupos.value[b])
      return infoA.label.localeCompare(infoB.label)
    })

  return { aff, validGroups }
})

// Mobile ranked list: for a selected group, show affinity with all others
const mobileRankedPairs = computed(() => {
  const { aff, validGroups } = affinityData.value
  const selectedName = mobileGroup.value
  const gIdx = selectedName ? validGroups.find(g => grupos.value[g] === selectedName) : validGroups[0]
  if (gIdx === undefined) return []

  const pairs = []
  for (const other of validGroups) {
    if (other === gIdx) continue
    const key = gIdx < other ? gIdx + ',' + other : other + ',' + gIdx
    const d = aff[key]
    if (!d || d.total === 0) continue
    const agreement = d.same / d.total
    pairs.push({ idx: other, name: grupos.value[other], agreement, same: d.same, total: d.total })
  }
  return pairs.sort((a, b) => b.agreement - a.agreement)
})

const mobileSelectedGroup = computed(() => {
  const { validGroups } = affinityData.value
  if (mobileGroup.value) return mobileGroup.value
  return validGroups.length ? grupos.value[validGroups[0]] : ''
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
          <label for="grupos-leg-select">Legislatura</label>
          <select id="grupos-leg-select" v-model="legFilter" class="filter-select">
            <option value="">Todas las legislaturas</option>
            <option v-for="l in LEGISLATURAS" :key="l.id" :value="l.id">{{ l.nombre }}</option>
          </select>
        </div>
      </div>

      <template v-if="affinityData.validGroups.length">
        <!-- Desktop: NxN table -->
        <div class="affinity-table-wrap affinity-desktop">
          <table class="affinity-table">
            <thead>
              <tr>
                <th aria-label="Grupos"><span style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0;">Grupos</span></th>
                <th v-for="g in affinityData.validGroups" :key="g" class="affinity-th-col" :aria-label="getGroupInfo(grupos[g]).label || 'Grupo'">
                  <div class="affinity-th-label" :style="{ color: getGroupInfo(grupos[g]).color }">
                    {{ getGroupInfo(grupos[g]).label || 'Grupo' }}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ga in affinityData.validGroups" :key="ga">
                <td class="affinity-row-label">
                  <router-link :to="'/grupo/' + encodeURIComponent(grupos[ga])" :aria-label="getGroupInfo(grupos[ga]).label || 'Grupo'" style="color:inherit;text-decoration:none;display:flex;align-items:center;gap:0.5rem">
                    <span class="group-dot" :style="{ backgroundColor: getGroupInfo(grupos[ga]).color }"></span>
                    <span class="sr-only" v-if="!getGroupInfo(grupos[ga]).label">Grupo</span>
                    {{ getGroupInfo(grupos[ga]).label }}
                  </router-link>
                </td>
                <td
                  v-for="gb in affinityData.validGroups"
                  :key="gb"
                  class="affinity-cell"
                  :class="{ 'affinity-cell--self': ga === gb, 'affinity-cell--link': ga !== gb }"
                  :style="{ background: cellData(ga, gb).bg, color: cellData(ga, gb).color }"
                  :title="cellData(ga, gb).title || cellData(ga, gb).pctStr"
                  @click="ga !== gb && $router.push({ path: '/afinidad', query: { ga: grupos[ga], gb: grupos[gb], leg: legFilter } })"
                >
                  {{ cellData(ga, gb).pctStr }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile: ranked list per group -->
        <div class="affinity-mobile">
          <div class="filter-group" style="margin-bottom:1rem">
            <label for="grupos-mobile-select">Grupo</label>
            <select id="grupos-mobile-select" v-model="mobileGroup" class="filter-select">
              <option v-for="g in affinityData.validGroups" :key="g" :value="grupos[g]">{{ getGroupInfo(grupos[g]).label }}</option>
            </select>
          </div>
          <p style="font-size:0.85rem;color:var(--color-muted);margin-bottom:0.75rem">
            Afinidad de <strong>{{ getGroupInfo(mobileSelectedGroup).label }}</strong> con otros grupos
          </p>
          <div class="affinity-list">
            <router-link
              v-for="pair in mobileRankedPairs"
              :key="pair.idx"
              :to="'/grupo/' + encodeURIComponent(pair.name)"
              class="affinity-list-item card-link"
            >
              <div class="affinity-list-name-wrap">
                <span class="group-dot" :style="{ backgroundColor: getGroupInfo(pair.name).color }"></span>
                <span class="affinity-list-name">{{ getGroupInfo(pair.name).label }}</span>
              </div>
              <div class="affinity-list-bar">
                <div class="affinity-list-bar-fill" :style="{ width: Math.round(pair.agreement * 100) + '%', background: affinityColor(pair.agreement) }"></div>
              </div>
              <span class="affinity-list-pct">{{ Math.round(pair.agreement * 100) }}%</span>
            </router-link>
          </div>
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

      <ViewState
        v-else-if="!loaded"
        type="loading"
        :padded="false"
      />

      <ViewState
        v-else
        type="empty"
        icon="&#128202;"
        message="No hay datos suficientes para esta legislatura."
      />
    </div>
  </section>
</template>

<style scoped>
.affinity-table-wrap {
  overflow-x: auto;
  margin: 0.75rem 0 1.5rem;
  -webkit-overflow-scrolling: touch;
}

.affinity-table {
  border-collapse: collapse;
  font-size: 0.8rem;
  white-space: nowrap;
}

@media (hover: hover) and (pointer: fine) and (min-width: 1024px) {
  .affinity-table tbody:hover td {
    color: transparent;
  }
  .affinity-table tbody:hover td:hover {
    color: inherit;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.6), 0 0 10px rgba(0, 0, 0, 0.1);
    z-index: 10;
    position: relative;
  }

  .affinity-table tr:hover td {
    color: inherit;
  }
  .affinity-table td:hover::after,
  .affinity-table td:hover::before {
    content: "";
    position: absolute;
    background-color: rgba(0, 0, 0, 0.05);
    left: 0;
    top: -5000px;
    height: 10000px;
    width: 100%;
    z-index: -1;
  }
  .affinity-table td:hover::before {
    left: -5000px;
    top: 0;
    width: 10000px;
    height: 100%;
  }
}

.affinity-table thead th {
  background: var(--color-surface);
  border-bottom: 2px solid var(--color-border);
  padding: 0;
  vertical-align: bottom;
  text-align: center;
}

.affinity-th-col {
  height: 120px;
  width: 48px;
  min-width: 48px;
  max-width: 48px;
}

.affinity-th-label {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  text-transform: none;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0;
  padding: 0.5rem 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-height: 110px;
}

.affinity-row-label {
  padding: 0.4rem 0.75rem 0.4rem 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  border-bottom: 1px solid var(--color-border);
  min-width: 140px;
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--color-surface);
}

.group-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.affinity-cell {
  width: 48px;
  min-width: 48px;
  max-width: 48px;
  height: 36px;
  text-align: center;
  vertical-align: middle;
  font-size: 0.72rem;
  font-weight: 600;
  color: #1e293b;
  border: 1px solid rgba(255,255,255,0.4);
  cursor: default;
  transition: opacity 0.1s, box-shadow 0.12s ease;
}

@media (hover: hover) and (pointer: fine) {
  .affinity-cell:hover { opacity: 0.85; }
}
.affinity-cell--link { cursor: pointer; }

.affinity-cell--self {
  background: #e2e8f0 !important;
  color: var(--color-muted);
  font-weight: 400;
}

.affinity-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.5rem;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
}

.affinity-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.affinity-legend-swatch {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 3px;
  flex-shrink: 0;
}

.affinity-mobile { display: none; }

.affinity-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.affinity-list-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  text-decoration: none;
  color: var(--color-text);
  transition: border-color 0.15s;
}

.affinity-list-item:hover {
  border-color: var(--color-primary);
  text-decoration: none;
}

.affinity-list-name-wrap {
  min-width: 180px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.affinity-list-name {
  font-size: 0.88rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.affinity-list-bar {
  flex: 1;
  height: 8px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.affinity-list-bar-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
  transition: width 0.3s;
}

.affinity-list-pct {
  font-size: 0.88rem;
  font-weight: 700;
  min-width: 3rem;
  text-align: right;
  color: var(--color-text);
}

@media (max-width: 768px) {
  .affinity-desktop { display: none; }
  .affinity-mobile { display: block; }
  .affinity-th-col { width: 40px; min-width: 40px; max-width: 40px; }
  .affinity-cell { width: 40px; min-width: 40px; max-width: 40px; font-size: 0.65rem; }
  .affinity-row-label { min-width: 100px; font-size: 0.75rem; }
  .affinity-list-name-wrap { min-width: 120px; }
  .affinity-list-name { font-size: 0.8rem; }
}
</style>
