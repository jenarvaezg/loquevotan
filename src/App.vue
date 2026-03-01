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

  <router-view id="main-content" />

  <footer class="site-footer">
    Datos oficiales del
    <a href="https://www.congreso.es/es/opendata/votaciones" target="_blank" rel="noopener">Congreso</a>
    y de parlamentos autonómicos (fuentes institucionales enlazadas en cada votación).
    Categorización automática por IA. Proyecto de código abierto.
  </footer>
</template>
