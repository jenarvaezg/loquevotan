<script setup>
import NavBar from './components/NavBar.vue'
import ErrorBanner from './components/ErrorBanner.vue'
import { useData } from './composables/useData'

const { error, loadData, retryLoad } = useData()
loadData()
</script>

<template>
  <a href="#main-content" class="skip-link">Saltar al contenido</a>
  <NavBar />

  <ErrorBanner v-if="error" :message="error" @retry="retryLoad" />

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
</style>
