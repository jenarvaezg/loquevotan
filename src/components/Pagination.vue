<script setup>
import { computed } from 'vue'

const props = defineProps({
  totalPages: Number,
  current: Number,
})

const emit = defineEmits(['page'])

function getPageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = [1]
  if (current > 3) pages.push('...')
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i)
  }
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
}

const pages = computed(() => getPageRange(props.current, props.totalPages))
</script>

<template>
  <nav v-if="totalPages > 1" class="pagination" aria-label="Paginación">
    <button class="page-btn" :disabled="current <= 1" @click="emit('page', current - 1)">
      &larr;
    </button>
    <template v-for="(p, i) in pages" :key="i">
      <span v-if="p === '...'" class="page-ellipsis">&hellip;</span>
      <button
        v-else
        class="page-btn"
        :class="{ active: p === current }"
        @click="emit('page', p)"
      >
        {{ p }}
      </button>
    </template>
    <button class="page-btn" :disabled="current >= totalPages" @click="emit('page', current + 1)">
      &rarr;
    </button>
  </nav>
</template>

<style scoped>
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
  margin: 1.5rem 0;
}

.page-btn {
  min-width: 2.25rem;
  height: 2.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.5rem;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  transition: background 0.15s;
}

.page-btn:hover:not(:disabled):not(.active) {
  background: var(--color-bg);
  border-color: var(--color-border-hover);
}

.page-btn.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.page-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.page-ellipsis { padding: 0 0.3rem; color: var(--color-muted); }

@media (max-width: 768px) {
  .page-btn {
    min-width: 2rem;
    height: 2rem;
    font-size: 0.8rem;
  }
}
</style>
