<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useData } from '../composables/useData'
import ViewState from '../components/ViewState.vue'
import HomeSpotlight from '../components/home/HomeSpotlight.vue'
import AskParty from '../components/home/AskParty.vue'
import VoteRows from '../components/home/VoteRows.vue'

const { currentScopeId } = useData()
const manifest = ref(null)
const extras = ref(null)
const loading = ref(true)
const error = ref('')

async function fetchJson(url) {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

// Home fetches its two small files itself so it can render before the full
// metadata arrives. Only the latest request (scope switches) may apply.
let request = 0

async function load() {
  const current = ++request
  manifest.value = null
  extras.value = null
  error.value = ''
  loading.value = true

  const scopePath = currentScopeId.value === 'nacional' ? '' : `${currentScopeId.value}/`
  const base = `${import.meta.env.BASE_URL}data/${scopePath}`
  const [manifestResult, extrasResult] = await Promise.allSettled([
    fetchJson(`${base}manifest_home.json`),
    fetchJson(`${base}home_extras.json`),
  ])
  if (current !== request) return

  if (manifestResult.status === 'fulfilled') {
    manifest.value = manifestResult.value
  } else {
    console.error('Error loading manifest:', manifestResult.reason)
    error.value = 'No se pudo cargar el resumen inicial para este ámbito.'
  }
  // Without the extras the home still works: the chamber is drawn from the totals.
  if (extrasResult.status === 'fulfilled') {
    extras.value = extrasResult.value
  } else {
    console.warn('Error loading home extras:', extrasResult.reason)
  }
  loading.value = false
}

onMounted(load)
watch(currentScopeId, load)

const spotlight = computed(() => {
  if (extras.value?.spotlight?.length) return extras.value.spotlight
  return (manifest.value?.featuredVotes || []).map((v) => ({ ...v, titulo: v.titulo_ciudadano, resumen: '', groups: null }))
})
const hasQuestions = computed(() => (extras.value?.questions?.topics?.length || 0) > 0)
</script>

<template>
  <h1 class="sr-only">Lo Que Votan: qué vota cada diputado</h1>

  <div v-if="manifest" data-testid="home-manifest-loaded">
    <HomeSpotlight v-if="spotlight.length" :votes="spotlight" />

    <AskParty
      v-if="hasQuestions"
      :questions="extras.questions"
      :preferred-tags="(manifest.heroExamples || []).map(([tag]) => tag)"
    />

    <section class="home-lists">
      <VoteRows title="Últimas votaciones" :votes="manifest.latestVotes.slice(0, 6)" data-testid="home-latest-votes" />
      <VoteRows title="Decididas por un puñado de votos" :votes="manifest.tightVotes.slice(0, 6)" data-testid="home-tight-votes" />
    </section>

    <section class="home-quiz" data-testid="home-quiz-banner">
      <div>
        <h2>¿Y tú, qué habrías votado?</h2>
        <p>Vota a ciegas propuestas que ya pasaron por el pleno y compara tus respuestas con lo que votó cada grupo.</p>
      </div>
      <router-link to="/quiz" class="home-quiz-btn">Hacer el test</router-link>
    </section>
  </div>

  <div v-else-if="error" class="container home-error">
    <ViewState
      type="error"
      title="No pudimos cargar la portada"
      :message="error"
      action-label="Reintentar"
      @action="load"
    />
  </div>

  <ViewState v-else-if="loading" type="loading" />
</template>

<style scoped>
.home-lists {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 56px;
  max-width: var(--container-max);
  margin: 72px auto 0;
  padding: 0 1.25rem;
}

.home-quiz {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  max-width: calc(var(--container-max) - 2.5rem);
  margin: 72px auto 0;
  padding: 36px 40px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: var(--color-on-primary);
}
.home-quiz h2 { font-size: 2.2rem; font-stretch: 72%; color: inherit; margin-bottom: 0.3rem; }
.home-quiz p { opacity: 0.8; max-width: 56ch; }
.home-quiz-btn {
  padding: 0.85rem 1.5rem;
  border-radius: var(--radius-md);
  background: var(--color-on-primary);
  color: var(--color-primary);
  font-weight: 700;
  white-space: nowrap;
}
.home-quiz-btn:hover { color: var(--color-primary); text-decoration: none; opacity: 0.9; }

.home-error { padding-top: 2rem; }

@media (max-width: 900px) {
  .home-lists { grid-template-columns: 1fr; gap: 36px; padding: 0 16px; margin-top: 48px; }
  .home-quiz { margin: 48px 16px 0; padding: 24px; flex-direction: column; align-items: flex-start; }
}
</style>
