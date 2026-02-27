<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt } from '../utils'
import { avatarStyle, avatarInitials } from '../utils'
import VoteCard from '../components/VoteCard.vue'
import HeroSearch from '../components/HeroSearch.vue'

const router = useRouter()
const { diputados, grupos, votaciones, votos, dipStats, tagCounts, topTags, sortedVotIdxByDate, votResults } = useData()

const stats = computed(() => ({
  diputados: diputados.value.length.toLocaleString('es-ES'),
  votaciones: votaciones.value.length.toLocaleString('es-ES'),
  votos: votos.value.length.toLocaleString('es-ES'),
}))

const heroExamples = computed(() => {
  const examples = [
    ['subir_pensiones', 'Quien voto subir pensiones?'],
    ['facilitar_acceso_vivienda', 'Acceso a vivienda'],
    ['combatir_cambio_climatico', 'Cambio climatico'],
    ['reformar_codigo_penal', 'Reforma penal'],
    ['proteger_sanidad_publica', 'Sanidad publica'],
  ]
  return examples.filter(([tag]) => tagCounts.value[tag])
})

const rebels = computed(() =>
  Array.from({ length: diputados.value.length }, (_, i) => i)
    .filter(i => dipStats.value[i].total > 50)
    .sort((a, b) => dipStats.value[a].loyalty - dipStats.value[b].loyalty)
    .slice(0, 10)
)

const tightVotes = computed(() =>
  sortedVotIdxByDate.value
    .filter(i => votResults.value[i].total > 0)
    .sort((a, b) => votResults.value[a].margin - votResults.value[b].margin)
    .slice(0, 10)
)

const latestVotes = computed(() => sortedVotIdxByDate.value.slice(0, 10))

function goToTag(tag) {
  router.push({ path: '/votaciones', query: { tag } })
}

function rebelGrupo(i) {
  const mg = dipStats.value[i].mainGrupo
  return mg >= 0 ? grupos.value[mg] : 'Sin grupo'
}
</script>

<template>
  <section>
    <div class="hero">
      <h1>Lo Que Votan</h1>
      <p class="hero-tagline">Que vota cada diputado en el Congreso, explicado para ciudadanos</p>
      <HeroSearch />
      <div class="hero-chips">
        <a
          v-for="[tag, label] in heroExamples"
          :key="tag"
          class="hero-chip"
          href="#"
          @click.prevent="goToTag(tag)"
        >
          {{ label }}
        </a>
      </div>
    </div>

    <div class="container">
      <div class="stats-banner">
        <div class="stat-item">
          <span class="stat-number">{{ stats.diputados }}</span>
          <span class="stat-label">diputados</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">{{ stats.votaciones }}</span>
          <span class="stat-label">votaciones</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">{{ stats.votos }}</span>
          <span class="stat-label">votos individuales</span>
        </div>
        <router-link to="/grupos" class="btn btn--primary" style="margin-left:auto;display:inline-flex;align-items:center;gap:0.4rem">
          &#128202; Compara partidos
        </router-link>
      </div>

      <div class="section-header">
        <h2>Temas populares</h2>
      </div>
      <div class="topic-grid">
        <a
          v-for="[tag, count] in topTags"
          :key="tag"
          class="topic-card"
          href="#"
          @click.prevent="goToTag(tag)"
        >
          <span class="topic-card-label">{{ fmt(tag) }}</span>
          <span class="topic-card-count">{{ count }}</span>
        </a>
      </div>

      <div class="section-header">
        <h2>Diputados mas rebeldes</h2>
        <router-link to="/diputados">Ver todos &rarr;</router-link>
      </div>
      <div class="ranking-grid">
        <router-link
          v-for="i in rebels"
          :key="i"
          class="ranking-card card-link"
          :to="'/diputado/' + encodeURIComponent(diputados[i])"
        >
          <div class="avatar" :style="avatarStyle(diputados[i])">{{ avatarInitials(diputados[i]) }}</div>
          <div class="ranking-info">
            <span class="ranking-name">{{ diputados[i] }}</span>
            <span class="ranking-detail">{{ rebelGrupo(i) }}</span>
            <span class="ranking-stat">{{ Math.round(dipStats[i].loyalty * 100) }}% lealtad al grupo</span>
          </div>
        </router-link>
      </div>

      <div class="section-header">
        <h2>Votaciones mas ajustadas</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid">
        <VoteCard v-for="i in tightVotes" :key="i" :idx="i" />
      </div>

      <div class="section-header">
        <h2>Ultimas votaciones</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid">
        <VoteCard v-for="i in latestVotes" :key="i" :idx="i" />
      </div>
    </div>
  </section>
</template>
