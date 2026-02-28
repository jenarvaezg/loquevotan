<script setup>
defineProps({
  message: String,
})

const emit = defineEmits(['retry'])
</script>

<template>
  <div class="error-banner">
    <div class="error-banner-icon">&#9888;</div>
    <p class="error-banner-text">{{ message }}</p>
    <button class="btn btn--primary btn--sm" @click="emit('retry')">Reintentar</button>
  </div>
</template>

<style scoped>
.error-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: var(--color-contra-light);
  border-bottom: 2px solid var(--color-contra);
  color: var(--color-text);
}

.error-banner-icon { font-size: 1.25rem; }
.error-banner-text { margin: 0; font-size: 0.9rem; }
</style>
