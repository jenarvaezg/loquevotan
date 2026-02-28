<script setup>
import { ref } from 'vue'

const isOpen = ref(false)
</script>

<template>
  <button class="filter-toggle" :class="{ open: isOpen }" @click="isOpen = !isOpen">
    Filtros
  </button>
  <div class="filter-bar" :class="{ open: isOpen }">
    <slot />
  </div>
</template>

<style scoped>
.filter-toggle {
  display: none;
  width: 100%;
  padding: 0.6rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text);
  text-align: center;
  margin-bottom: 0.5rem;
}

.filter-toggle::after { content: " ▼"; font-size: 0.7em; }
.filter-toggle.open::after { content: " ▲"; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: flex-end;
  margin-bottom: 1.25rem;
  padding: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

@media (max-width: 768px) {
  .filter-toggle { display: block; }

  .filter-bar {
    flex-direction: column;
    display: none;
  }

  .filter-bar.open { display: flex; }
}
</style>
