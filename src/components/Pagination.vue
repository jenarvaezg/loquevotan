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
  <nav v-if="totalPages > 1" class="pagination">
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
