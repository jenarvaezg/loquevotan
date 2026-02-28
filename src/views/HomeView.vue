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
          :key="rebel.name"
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
        <VoteCard v-for="v in manifest.tightVotes" :key="v.id" :votData="v" :votResult="v" />
      </div>

      <div class="section-header">
        <h2>Últimas votaciones</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid">
        <VoteCard v-for="v in manifest.latestVotes" :key="v.id" :votData="v" :votResult="v" />
      </div>
    </div>
  </section>
  <div v-else class="loading-wrap">
    <div class="loading-spinner"></div>
  </div>
</template>

<style scoped>
.hero {
  background: linear-gradient(135deg, #1e3a8a 0%, #1a56db 50%, #2563eb 100%);
  color: #fff;
  padding: 3.5rem 1.25rem 3rem;
  text-align: center;
}

.hero h1 {
  color: #fff;
  font-size: 2.25rem;
  margin-bottom: 0.5rem;
}

.hero-tagline {
  font-size: 1.1rem;
  opacity: 0.85;
  margin-bottom: 2rem;
  font-weight: 400;
}

.hero-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.4rem;
  margin-top: 1.25rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.hero-chip {
  display: inline-block;
  padding: 0.35em 0.75em;
  border-radius: 50px;
  font-size: 0.82rem;
  font-weight: 500;
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.9);
  border: 1px solid rgba(255,255,255,0.2);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  text-decoration: none;
  white-space: nowrap;
}

.hero-chip:hover {
  background: rgba(255,255,255,0.25);
  border-color: rgba(255,255,255,0.4);
  text-decoration: none;
  color: #fff;
}

.stats-banner {
  display: flex;
  justify-content: center;
  gap: 2rem;
  padding: 1.5rem 0;
  margin: 0 0 2rem;
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--color-muted);
  font-weight: 500;
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.6rem;
  margin-bottom: 2rem;
}

.topic-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  text-decoration: none;
  color: inherit;
}

.topic-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
  text-decoration: none;
  color: inherit;
}

.topic-card-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text);
}

.topic-card-count {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-light);
  padding: 0.15em 0.5em;
  border-radius: 50px;
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

.ranking-card :deep(.avatar) {
  width: 44px;
  height: 44px;
  font-size: 1rem;
  flex-shrink: 0;
  margin-bottom: 0;
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

.ranking-detail {
  font-size: 0.8rem;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ranking-stat {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-contra);
}

.vote-cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
}

@media (max-width: 768px) {
  .hero { padding: 2.5rem 1rem 2rem; }
  .hero h1 { font-size: 1.75rem; }
  .hero-tagline { font-size: 1rem; }
  .stats-banner { gap: 1rem; }
  .stat-number { font-size: 1.35rem; }
  .topic-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .topic-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }
}
</style>
