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

<style scoped>
.result-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25em 0.75em;
  border-radius: 50px;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.result-badge--aprobada {
  background: var(--color-favor-light);
  color: var(--color-favor);
}

.result-badge--rechazada {
  background: var(--color-contra-light);
  color: var(--color-contra);
}

.result-badge--empate {
  background: var(--color-abstencion-light);
  color: var(--color-abstencion);
}

.result-badge--lg {
  font-size: 1.1rem;
  padding: 0.4em 1em;
}
</style>
