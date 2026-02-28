<template>
  <section>
    <div class="container" style="padding-top:3rem">
      <div class="empty-state">
        <div class="empty-state-icon" style="font-size:3.5rem;font-weight:800;color:var(--color-muted)">404</div>
        <h1 style="margin-bottom:0.5rem">Página no encontrada</h1>
        <p class="empty-state-text">La página que buscas no existe o ha sido movida.</p>
        <router-link to="/" class="btn btn--primary" style="margin-top:1.5rem">Ir al inicio</router-link>
      </div>
    </div>
  </section>
</template>
