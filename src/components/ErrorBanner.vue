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
