<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, pct, normalize, dipPhotoUrl, avatarStyle, avatarInitials, LEGISLATURAS, DIPS_PER_PAGE, getGroupInfo } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const { grupos, diputados, dipStats, dipFotos, votaciones, votResults, groupAffinityByLeg, categorias, loaded } = useData()

const grupoRawName = computed(() => decodeURIComponent(route.params.grupo))
const grupoIdx = computed(() => grupos.value.indexOf(grupoRawName.value))
const groupInfo = computed(() => getGroupInfo(grupoRawName.value))

// Members of this grupo
const members = computed(() => {
  if (grupoIdx.value < 0) return []
  const result = []
  for (let i = 0; i < dipStats.value.length; i++) {
    if (dipStats.value[i].mainGrupo === grupoIdx.value) {
      result.push(i)
    }
  }
  return result.sort((a, b) => diputados.value[a].localeCompare(diputados.value[b]))
})

// Aggregate stats
const stats = computed(() => {
  let favor = 0, contra = 0, abstencion = 0, total = 0
  for (const i of members.value) {
    const ds = dipStats.value[i]
    favor += ds.favor
    contra += ds.contra
    abstencion += ds.abstencion
    total += ds.total
  }
  return { favor, contra, abstencion, total }
})

// Legislaturas this grupo appears in
const grupoLegs = computed(() => {
  const legs = new Set()
  for (const i of members.value) {
    const ds = dipStats.value[i]
    if (ds.legislaturas) ds.legislaturas.forEach(l => legs.add(l))
  }
  return LEGISLATURAS.filter(l => legs.has(l.id)).map(l => l.id)
})

// Average loyalty
const avgLoyalty = computed(() => {
  if (!members.value.length) return 0
  let sum = 0
  for (const i of members.value) {
    sum += dipStats.value[i].loyalty
  }
  return sum / members.value.length
})

// Most rebellious members
const rebels = computed(() => {
  return [...members.value]
    .filter(i => dipStats.value[i].total >= 10)
    .sort((a, b) => dipStats.value[a].loyalty - dipStats.value[b].loyalty)
    .slice(0, 5)
})

// Affinity with other groups (latest legislatura)
const affinityPairs = computed(() => {
  const leg = grupoLegs.value[0] || ''
  const aff = groupAffinityByLeg.value[leg] || groupAffinityByLeg.value[''] || {}
  const gIdx = grupoIdx.value
  const pairs = []
  for (const key in aff) {
    const parts = key.split(',').map(Number)
    if (parts[0] !== gIdx && parts[1] !== gIdx) continue
    const otherIdx = parts[0] === gIdx ? parts[1] : parts[0]
    const d = aff[key]
    if (d.total < 10) continue
    const agreement = d.same / d.total
    pairs.push({ grupoIdx: otherIdx, name: grupos.value[otherIdx], agreement, same: d.same, total: d.total })
  }
  return pairs.sort((a, b) => b.agreement - a.agreement)
})

// Member pagination
const memberPage = ref(1)
const memberSearch = ref('')

const filteredMembers = computed(() => {
  const q = normalize(memberSearch.value.trim())
  if (!q) return members.value
  return members.value.filter(i => normalize(diputados.value[i]).includes(q))
})

const memberTotalPages = computed(() => Math.max(1, Math.ceil(filteredMembers.value.length / DIPS_PER_PAGE)))

const memberPageItems = computed(() => {
  const p = Math.min(memberPage.value, memberTotalPages.value)
  const start = (p - 1) * DIPS_PER_PAGE
  return filteredMembers.value.slice(start, start + DIPS_PER_PAGE)
})

// Update document title
watch(grupoRawName, (n) => {
  if (n) document.title = getGroupInfo(n).label + ' | Lo Que Votan'
}, { immediate: true })
</script>

<template>
  <section v-if="grupoIdx >= 0">
    <div class="container" style="padding-top:1.5rem">
      <router-link to="/grupos" class="back-link">&larr; Partidos</router-link>

      <div class="detail-header" style="display:flex; align-items:center; gap:1rem">
        <span class="group-icon-large" :style="{ backgroundColor: groupInfo.color }"></span>
        <div>
          <h1 style="margin:0">{{ groupInfo.label }}</h1>
          <div class="detail-meta" style="margin-top:0.25rem">
            <span class="detail-meta-item">{{ members.length }} diputados</span>
            <span class="detail-meta-item">Lealtad media: {{ pct(avgLoyalty) }}</span>
            <span v-for="l in grupoLegs" :key="l" class="badge badge--leg">{{ l }}</span>
          </div>
          <p class="small text-muted" style="margin-top:0.25rem">Nombre oficial: {{ grupoRawName }}</p>
        </div>
      </div>

      <!-- Aggregate stats -->
      <div class="stat-cards">
        <div class="stat-card">
          <span class="stat-card-value">{{ stats.total.toLocaleString('es-ES') }}</span>
          <span class="stat-card-label">Votos totales</span>
        </div>
        <div class="stat-card stat-card--favor">
          <span class="stat-card-value">{{ stats.favor.toLocaleString('es-ES') }}</span>
          <span class="stat-card-label">A favor ({{ pct(stats.favor / stats.total) }})</span>
        </div>
        <div class="stat-card stat-card--contra">
          <span class="stat-card-value">{{ stats.contra.toLocaleString('es-ES') }}</span>
          <span class="stat-card-label">En contra ({{ pct(stats.contra / stats.total) }})</span>
        </div>
        <div class="stat-card stat-card--abstencion">
          <span class="stat-card-value">{{ stats.abstencion.toLocaleString('es-ES') }}</span>
          <span class="stat-card-label">Abstenciones ({{ pct(stats.abstencion / stats.total) }})</span>
        </div>
      </div>

      <VoteBar :favor="stats.favor" :contra="stats.contra" :abstencion="stats.abstencion" :total="stats.total" />

      <!-- Affinity with other groups -->
      <div v-if="affinityPairs.length" class="detail-section">
        <h2>Afinidad con otros grupos</h2>
        <p class="hint-text">Porcentaje de votaciones en las que ambos grupos votaron mayoritariamente igual</p>
        <div class="affinity-list">
          <router-link
            v-for="pair in affinityPairs"
            :key="pair.grupoIdx"
            :to="'/grupo/' + encodeURIComponent(pair.name)"
            class="affinity-list-item card-link"
          >
            <div style="min-width:180px; display:flex; align-items:center; gap:0.5rem">
              <span class="group-dot" :style="{ backgroundColor: getGroupInfo(pair.name).color }"></span>
              <span class="affinity-list-name">{{ getGroupInfo(pair.name).label }}</span>
            </div>
            <div class="affinity-list-bar">
              <div class="affinity-list-bar-fill" :style="{ width: Math.round(pair.agreement * 100) + '%', background: getGroupInfo(pair.name).color }"></div>
            </div>
            <span class="affinity-list-pct">{{ Math.round(pair.agreement * 100) }}%</span>
          </router-link>
        </div>
      </div>

      <!-- Most rebellious -->
      <div v-if="rebels.length" class="detail-section">
        <h2>Diputados menos alineados</h2>
        <div class="ranking-grid">
          <router-link
            v-for="i in rebels"
            :key="i"
            class="ranking-card card-link"
            :to="'/diputado/' + encodeURIComponent(diputados[i])"
          >
            <img v-if="dipPhotoUrl(dipFotos[i])" :src="dipPhotoUrl(dipFotos[i])" :alt="diputados[i]" class="ranking-card-photo">
            <div v-else class="avatar" :style="avatarStyle(diputados[i])">{{ avatarInitials(diputados[i]) }}</div>
            <div class="ranking-info">
              <span class="ranking-name">{{ diputados[i] }}</span>
              <span class="ranking-stat">{{ Math.round(dipStats[i].loyalty * 100) }}% lealtad</span>
            </div>
          </router-link>
        </div>
      </div>

      <!-- All members -->
      <div class="detail-section">
        <h2>Todos los miembros ({{ members.length }})</h2>
        <input
          v-model="memberSearch"
          type="search"
          class="filter-input"
          placeholder="Buscar diputado/a..."
          style="max-width:350px;margin-bottom:0.75rem"
          @input="memberPage = 1"
        >
        <div class="dip-cards-grid">
          <router-link
            v-for="i in memberPageItems"
            :key="i"
            class="dip-mini-card card-link"
            :to="'/diputado/' + encodeURIComponent(diputados[i])"
          >
            <img v-if="dipPhotoUrl(dipFotos[i])" :src="dipPhotoUrl(dipFotos[i])" :alt="diputados[i]" class="dip-mini-photo">
            <div v-else class="avatar avatar--sm" :style="avatarStyle(diputados[i])">{{ avatarInitials(diputados[i]) }}</div>
            <div class="dip-mini-info">
              <span class="dip-mini-name">{{ diputados[i] }}</span>
              <span class="dip-mini-stat">{{ dipStats[i].total }} votos &middot; {{ pct(dipStats[i].loyalty) }} lealtad</span>
            </div>
          </router-link>
        </div>
        <Pagination :total-pages="memberTotalPages" :current="memberPage" @page="p => memberPage = p" />
      </div>
    </div>
  </section>

  <div v-else-if="!loaded" class="loading-wrap">
    <div class="loading-spinner"></div>
  </div>

  <section v-else>
    <div class="container" style="padding-top:3rem">
      <div class="empty-state">
        <div class="empty-state-icon">&#128202;</div>
        <h1 style="margin-bottom:0.5rem">Grupo no encontrado</h1>
        <p class="empty-state-text">El grupo parlamentario que buscas no existe.</p>
        <router-link to="/grupos" class="btn btn--primary" style="margin-top:1.5rem">Ver partidos</router-link>
      </div>
    </div>
  </section>
</template>

<style scoped>
.group-icon-large {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex-shrink: 0;
}

.group-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}

.detail-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--color-border);
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  font-size: 0.875rem;
}

.detail-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--color-muted);
}

.detail-section {
  margin-top: 2rem;
}

.detail-section h2 {
  font-size: 1.15rem;
  margin-bottom: 0.75rem;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
  padding: 1rem;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.stat-card-value {
  display: block;
  font-size: 1.75rem;
  font-weight: 800;
  line-height: 1.2;
}

.stat-card-label {
  font-size: 0.8rem;
  color: var(--color-muted);
  font-weight: 500;
}

.stat-card--favor { border-left: 4px solid var(--color-favor); }
.stat-card--favor .stat-card-value { color: var(--color-favor); }
.stat-card--contra { border-left: 4px solid var(--color-contra); }
.stat-card--contra .stat-card-value { color: var(--color-contra); }
.stat-card--abstencion { border-left: 4px solid var(--color-abstencion); }
.stat-card--abstencion .stat-card-value { color: var(--color-abstencion); }

.hint-text {
  font-size: 0.82rem;
  color: var(--color-muted);
  margin-bottom: 0.5rem;
  font-style: italic;
}

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

.affinity-list-name {
  min-width: 180px;
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

.ranking-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.ranking-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  text-decoration: none;
  transition: box-shadow 0.15s, border-color 0.15s;
}

.ranking-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary);
}

.ranking-card-photo {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.ranking-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ranking-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ranking-stat {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-contra);
}

.dip-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
}

.dip-mini-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  text-decoration: none;
  color: var(--color-text);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.dip-mini-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
  text-decoration: none;
}

.dip-mini-photo {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.dip-mini-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.dip-mini-name {
  font-size: 0.88rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dip-mini-stat {
  font-size: 0.78rem;
  color: var(--color-muted);
}

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .stat-card-value { font-size: 1.35rem; }
  .detail-meta { flex-direction: column; align-items: flex-start; }
  .affinity-list-name { min-width: 120px; font-size: 0.8rem; }
  .dip-cards-grid { grid-template-columns: 1fr; }
}
</style>
