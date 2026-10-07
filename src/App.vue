<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'
import ErrorBanner from './components/ErrorBanner.vue'
import { useData } from './composables/useData'

const { error, loadData, retryLoad, ambitos, currentScopeId, votosFailed, retryFailedVotos } = useData()
const route = useRoute()

// Embedded widgets render only the card, without the site chrome.
const isEmbed = computed(() => route.query.embed === 'true' && String(route.path).startsWith('/widget'))

const votosErrorMessage = computed(() => {
  const legs = [...votosFailed.value]
  if (!legs.length) return ''
  return `No se pudieron cargar las votaciones de la legislatura ${legs.join(', ')}. Comprueba tu conexión.`
})

const currentScope = computed(() => {
  return ambitos.value.find((a) => a.id === currentScopeId.value) || null
})

const scopeWipLabel = computed(() => {
  if (!currentScope.value?.wip) return null
  return currentScope.value.wipLabel || 'Datos en revisión (procesamiento en curso)'
})

loadData()
</script>

<template>
  <a v-if="!isEmbed" href="#main-content" class="skip-link">Saltar al contenido</a>
  <NavBar v-if="!isEmbed" />

  <ErrorBanner v-if="error" :message="error" @retry="retryLoad" />
  <ErrorBanner v-else-if="votosErrorMessage" :message="votosErrorMessage" @retry="retryFailedVotos" />
  <section v-if="scopeWipLabel && !isEmbed" class="wip-banner" role="status" aria-live="polite">
    <div class="container wip-banner__content">
      <strong>⚠ Datos provisionales:</strong>
      <span>{{ currentScope?.nombre }} está en proceso de actualización. {{ scopeWipLabel }}.</span>
    </div>
  </section>

  <main id="main-content">
    <router-view />
  </main>

  <footer v-if="!isEmbed" class="site-footer">
    <div class="container footer-content">
      <p>
        Datos oficiales del
        <a href="https://www.congreso.es/es/opendata/votaciones" target="_blank" rel="noopener">Congreso</a>
        y de los parlamentos autonómicos. Títulos y temas resumidos con IA.
      </p>
      <div class="footer-links">
        <router-link to="/metodologia">Metodología</router-link>
        <a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">Código abierto en GitHub</a>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.wip-banner {
  border-bottom: 1px solid rgba(194, 65, 12, 0.24);
  background: rgba(255, 237, 213, 0.8);
}

.wip-banner__content {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding-top: 0.55rem;
  padding-bottom: 0.55rem;
  font-size: 0.82rem;
  color: #9a3412;
  line-height: 1.35;
}

[data-theme="dark"] .wip-banner {
  border-bottom-color: rgba(251, 146, 60, 0.3);
  background: rgba(124, 45, 18, 0.33);
}

[data-theme="dark"] .wip-banner__content {
  color: #fdba74;
}

.site-footer {
  margin-top: 4rem;
  padding: 1.5rem 0 2.5rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.9rem;
  color: var(--color-muted);
}

.footer-content {
  display: flex;
  justify-content: space-between;
  gap: 2rem;
}

.footer-content p { max-width: 70ch; }

.footer-content a {
  color: var(--color-text);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.footer-links { display: flex; gap: 1.25rem; white-space: nowrap; }

@media (max-width: 640px) {
  .wip-banner__content {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.15rem;
  }

  .footer-content { flex-direction: column; gap: 0.75rem; }
}
</style>
