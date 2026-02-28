<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt, pct, normalize, dipPhotoUrl, avatarStyle, avatarInitials, LEGISLATURAS, DIPS_PER_PAGE } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const { grupos, diputados, dipStats, dipFotos, votaciones, votResults, groupAffinityByLeg, categorias, loaded } = useData()

const grupoName = computed(() => decodeURIComponent(route.params.grupo))
const grupoIdx = computed(() => grupos.value.indexOf(grupoName.value))

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
watch(grupoName, (n) => {
  if (n) document.title = n + ' | Lo Que Votan'
}, { immediate: true })
</script>

<template>
  <section v-if="grupoIdx >= 0">
    <div class="container" style="padding-top:1.5rem">
      <router-link to="/grupos" class="back-link">&larr; Partidos</router-link>

      <div class="detail-header">
        <h1>{{ grupoName }}</h1>
        <div class="detail-meta" style="margin-top:0.5rem">
          <span class="detail-meta-item">{{ members.length }} diputados</span>
          <span class="detail-meta-item">Lealtad media: {{ pct(avgLoyalty) }}</span>
          <span v-for="l in grupoLegs" :key="l" class="badge badge--leg">{{ l }}</span>
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
            <span class="affinity-list-name">{{ pair.name }}</span>
            <div class="affinity-list-bar">
              <div class="affinity-list-bar-fill" :style="{ width: Math.round(pair.agreement * 100) + '%' }"></div>
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
