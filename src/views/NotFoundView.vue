<script setup>
import ViewState from '../components/ViewState.vue'
</script>

<template>
  <section>
    <div class="container" style="padding-top:3rem">
      <ViewState
        type="empty"
        icon="404"
        title="Página no encontrada"
        message="La página que buscas no existe o ha sido movida."
        action-label="Ir al inicio"
        action-to="/"
      />
    </div>
  </section>
</template>
