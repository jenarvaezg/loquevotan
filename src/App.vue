<script setup>
import NavBar from './components/NavBar.vue'
import { useData } from './composables/useData'

const { loading, error, loadData } = useData()
loadData()
</script>

<template>
  <NavBar />

  <div v-if="loading" class="loading-wrap">
    <div class="loading-spinner"></div>
    <p class="loading-text">Cargando datos del Congreso...</p>
  </div>

  <p v-else-if="error" class="error-msg" role="alert" style="display:block">
    {{ error }}
  </p>

  <router-view v-else />

  <footer class="site-footer">
    Datos oficiales del
    <a href="https://www.congreso.es/es/opendata/votaciones" target="_blank" rel="noopener">
      Congreso de los Diputados (Datos Abiertos)
    </a>.
    Categorizacion automatica por IA. Proyecto de codigo abierto.
  </footer>
</template>
