<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: String,
  large: Boolean,
})

const cls = computed(() => {
  const variant = props.result === 'Aprobada' ? 'aprobada'
    : props.result === 'Rechazada' ? 'rechazada'
    : 'empate'
  return ['result-badge', `result-badge--${variant}`, { 'result-badge--lg': props.large }]
})
</script>

<template>
  <span :class="cls">{{ result }}</span>
</template>
