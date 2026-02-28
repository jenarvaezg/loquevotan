<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fmt, avatarStyle, avatarInitials } from '../utils'
import VoteCard from '../components/VoteCard.vue'
import HeroSearch from '../components/HeroSearch.vue'

const router = useRouter()
const manifest = ref(null)

onMounted(async () => {
  try {
    const url = import.meta.env.BASE_URL + 'data/manifest_home.json'
    const resp = await fetch(url)
    if (resp.ok) manifest.value = await resp.json()
  } catch (e) {
    console.error('Error loading manifest:', e)
  }
})

function goToTag(tag) {
  router.push({ path: '/votaciones', query: { tag } })
}
</script>

<template>
  <section v-if="manifest">
    <div class="hero">
      <h1>Lo Que Votan</h1>
      <p class="hero-tagline">Qué vota cada diputado en el Congreso, explicado para ciudadanos</p>
      <HeroSearch />
      <div class="hero-chips">
        <a
          v-for="[tag, label] in manifest.heroExamples"
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
          <span class="stat-number">{{ manifest.stats.diputados.toLocaleString('es-ES') }}</span>
          <span class="stat-label">diputados</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">{{ manifest.stats.votaciones.toLocaleString('es-ES') }}</span>
          <span class="stat-label">votaciones</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">{{ manifest.stats.votos.toLocaleString('es-ES') }}</span>
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
          v-for="[tag, count] in manifest.topTags"
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
        <h2>Diputados más rebeldes</h2>
        <router-link to="/diputados">Ver todos &rarr;</router-link>
      </div>
      <div class="ranking-grid">
        <router-link
          v-for="rebel in manifest.rebels"
          :key="rebel.idx"
          class="ranking-card card-link"
          :to="'/diputado/' + encodeURIComponent(rebel.name)"
        >
          <div class="avatar" :style="avatarStyle(rebel.name)">{{ avatarInitials(rebel.name) }}</div>
          <div class="ranking-info">
            <span class="ranking-name">{{ rebel.name }}</span>
            <span class="ranking-detail">{{ rebel.grupo }}</span>
            <span class="ranking-stat">{{ Math.round(rebel.loyalty * 100) }}% lealtad al grupo</span>
          </div>
        </router-link>
      </div>

      <div class="section-header">
        <h2>Votaciones más ajustadas</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid">
        <VoteCard v-for="v in manifest.tightVotes" :key="v.idx" :votData="v" :votResult="v" />
      </div>

      <div class="section-header">
        <h2>Últimas votaciones</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid">
        <VoteCard v-for="v in manifest.latestVotes" :key="v.idx" :votData="v" :votResult="v" />
      </div>
    </div>
  </section>
  <div v-else class="loading-wrap">
    <div class="loading-spinner"></div>
  </div>
</template>
