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
