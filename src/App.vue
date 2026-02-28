<script setup>
import NavBar from './components/NavBar.vue'
import { useData } from './composables/useData'

const { error, loadData } = useData()
loadData()
</script>

<template>
  <NavBar />

  <p v-if="error" class="error-msg" role="alert" style="display:block">
    {{ error }}
  </p>

  <router-view />

  <footer class="site-footer">
    Datos oficiales del
    <a href="https://www.congreso.es/es/opendata/votaciones" target="_blank" rel="noopener">
      Congreso de los Diputados (Datos Abiertos)
    </a>.
    Categorizacion automatica por IA. Proyecto de codigo abierto.
  </footer>
</template>
