<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fmt } from '../utils'
import { useData } from '../composables/useData'
import VoteCard from '../components/VoteCard.vue'
import HeroSearch from '../components/HeroSearch.vue'
import ViewState from '../components/ViewState.vue'

const { currentScopeId } = useData()
const router = useRouter()
const manifest = ref(null)
const manifestLoading = ref(true)
const manifestError = ref('')

async function loadManifest() {
  manifest.value = null
  manifestError.value = ''
  manifestLoading.value = true
  try {
    const scopePath = currentScopeId.value === 'nacional' ? '' : `${currentScopeId.value}/`
    const url = `${import.meta.env.BASE_URL}data/${scopePath}manifest_home.json`
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    manifest.value = await resp.json()
  } catch (e) {
    console.error('Error loading manifest:', e)
    manifestError.value = 'No se pudo cargar el resumen inicial para este ámbito.'
  } finally {
    manifestLoading.value = false
  }
}

onMounted(loadManifest)
watch(currentScopeId, loadManifest)

function goToTag(tag) {
  router.push({ path: '/votaciones', query: { tag } })
}
</script>

<template>
  <section v-if="manifest" data-testid="home-manifest-loaded">
    <div class="hero">
      <h1>Lo Que Votan</h1>
      <p class="hero-tagline">Qué vota cada diputado en el Congreso, explicado para ciudadanos</p>
      <HeroSearch :show-no-results="true" />
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
      <div class="bento-grid">
        <!-- Quiz Banner -->
        <div class="bento-card quiz-bento" data-testid="home-quiz-banner">
          <div class="quiz-banner-content">
            <h2>¿Con quién coincide más tu voto?</h2>
            <p>Responde a ciegas y compara tu patrón con el voto real de los partidos en temas clave.</p>
          </div>
          <router-link to="/quiz" class="btn btn--primary btn--lg quiz-banner-btn">
            Hacer el test &rarr;
          </router-link>
        </div>

        <!-- Stats Banner -->
        <div class="bento-card stats-bento" data-testid="home-stats">
          <div class="stat-group">
            <div class="stat-item">
              <span class="stat-number">{{ manifest.stats.diputados.toLocaleString('es-ES') }}</span>
              <span class="stat-label">diputados</span>
            </div>
            <div class="stat-item">
              <span class="stat-number">{{ manifest.stats.votaciones.toLocaleString('es-ES') }}</span>
              <span class="stat-label">votaciones</span>
            </div>
          </div>
          <div class="stat-group stat-group--bottom">
            <div class="stat-item">
              <span class="stat-number">{{ manifest.stats.votos.toLocaleString('es-ES') }}</span>
              <span class="stat-label">votos procesados</span>
            </div>
            <router-link to="/grupos" class="btn compare-btn">
              &#128202; Compara partidos
            </router-link>
          </div>
        </div>
      </div>

      <div class="section-header">
        <h2>Temas populares</h2>
      </div>
      <div class="topic-grid" data-testid="home-top-tags">
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

      <!-- FEATURED VOTES -->
      <div v-if="manifest.featuredVotes && manifest.featuredVotes.length > 0" class="featured-section" data-testid="home-featured-votes">
        <div class="section-header">
          <h2>Votaciones destacadas</h2>
          <span>Fiscaliza los temas clave</span>
        </div>
        <div class="vote-cards-grid featured-grid">
          <VoteCard v-for="v in manifest.featuredVotes" :key="v.id" :votData="v" :votResult="v" class="featured-card" />
        </div>
      </div>

      <div class="section-header">
        <h2>Votaciones más ajustadas</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid" data-testid="home-tight-votes">
        <VoteCard v-for="v in manifest.tightVotes" :key="v.id" :votData="v" :votResult="v" />
      </div>

      <div class="section-header">
        <h2>Últimas votaciones</h2>
        <router-link to="/votaciones">Ver todas &rarr;</router-link>
      </div>
      <div class="vote-cards-grid" data-testid="home-latest-votes">
        <VoteCard v-for="v in manifest.latestVotes" :key="v.id" :votData="v" :votResult="v" />
      </div>
    </div>
  </section>

  <div v-else-if="manifestError" class="container" style="padding-top:2rem">
    <ViewState
      type="error"
      title="No pudimos cargar la portada"
      :message="manifestError"
      action-label="Reintentar"
      @action="loadManifest"
    />
  </div>

  <ViewState v-else-if="manifestLoading" type="loading" />
</template>

<style scoped>
.hero {
  background: linear-gradient(-45deg, #1e3a8a, #1a56db, #2563eb, #312e81);
  background-size: 400% 400%;
  animation: gradientBG 15s ease infinite;
  color: #fff;
  padding: 4rem 1.25rem 3.5rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}

@keyframes gradientBG {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.hero h1 {
  color: #fff;
  font-size: 2.75rem;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}

.hero-tagline {
  font-size: 1.15rem;
  opacity: 0.9;
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

.bento-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.25rem;
  margin: -2rem auto 2.5rem;
  position: relative;
  z-index: 10;
}

.bento-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  padding: 2rem;
  box-shadow: var(--shadow-lg);
  display: flex;
}

.quiz-bento {
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  background: var(--color-primary-lighter);
  border: 1px solid var(--color-primary-light);
  gap: 1.5rem;
}

.quiz-banner-content h2 {
  font-size: 1.8rem;
  margin: 0 0 0.5rem 0;
  color: var(--color-primary);
}

.quiz-banner-content p {
  margin: 0;
  font-size: 1.05rem;
  color: var(--color-text);
  line-height: 1.5;
  max-width: 500px;
}

.quiz-banner-btn {
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

.stats-bento {
  flex-direction: column;
  justify-content: space-between;
  gap: 1.5rem;
}

.stat-group {
  display: flex;
  gap: 1.5rem;
}

.stat-group--bottom {
  justify-content: space-between;
  align-items: flex-end;
}

.stat-item {
  text-align: left;
}

.stat-number {
  display: block;
  font-size: 1.85rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--color-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.compare-btn {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.compare-btn:hover {
  background: var(--color-bg);
  border-color: var(--color-primary);
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

.featured-section {
  margin-bottom: 3rem;
  background: var(--color-surface-muted);
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.featured-grid {
  gap: 1.25rem;
}

.featured-card {
  border-left: 4px solid var(--color-primary) !important;
  box-shadow: var(--shadow-md) !important;
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
  .bento-grid { grid-template-columns: 1fr; margin-top: -1.5rem; }
  .stat-number { font-size: 1.5rem; }
  .quiz-bento {
    align-items: stretch;
    text-align: center;
    padding: 1.5rem;
    gap: 1.25rem;
  }
  .quiz-banner-content h2 { font-size: 1.4rem; }
  .quiz-banner-btn { width: 100%; justify-content: center; }
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
