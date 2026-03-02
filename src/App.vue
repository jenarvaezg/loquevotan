<script setup>
import { computed } from 'vue'
import NavBar from './components/NavBar.vue'
import ErrorBanner from './components/ErrorBanner.vue'
import { useData } from './composables/useData'

const { error, loadData, retryLoad, ambitos, currentScopeId } = useData()

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
  <a href="#main-content" class="skip-link">Saltar al contenido</a>
  <NavBar />

  <ErrorBanner v-if="error" :message="error" @retry="retryLoad" />
  <section v-if="scopeWipLabel" class="wip-banner" role="status" aria-live="polite">
    <div class="container wip-banner__content">
      <strong>⚠ Datos provisionales:</strong>
      <span>{{ currentScope?.nombre }} está en proceso de actualización. {{ scopeWipLabel }}.</span>
    </div>
  </section>

  <main id="main-content">
    <router-view />
  </main>

  <footer class="site-footer">
    <div class="container footer-content">
      <p>
        Datos oficiales del
        <a href="https://www.congreso.es/es/opendata/votaciones" target="_blank" rel="noopener">Congreso</a>
        y de parlamentos autonómicos.
        Categorización automática por IA. Proyecto de código abierto.
      </p>
      <div class="footer-links">
        <router-link to="/metodologia">Metodología y Transparencia</router-link>
        <span class="footer-sep">|</span>
        <a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">GitHub</a>
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
  padding: 2rem 0;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-muted);
}

.footer-content p {
  margin-bottom: 0.75rem;
  max-width: 700px;
  margin-left: auto;
  margin-right: auto;
}

.footer-links {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.75rem;
}

.footer-links a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.footer-links a:hover {
  text-decoration: underline;
}

.footer-sep {
  color: var(--color-border);
  font-weight: 300;
}

@media (max-width: 640px) {
  .wip-banner__content {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.15rem;
  }
}
</style>
