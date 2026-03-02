<script setup>
import { computed } from 'vue'

const props = defineProps({
  favor: Number,
  contra: Number,
  abstencion: Number,
  total: Number,
  small: Boolean,
})

const safeTotal = computed(() => Math.max(0, Number(props.total) || 0))
const favorCount = computed(() => Math.max(0, Number(props.favor) || 0))
const contraCount = computed(() => Math.max(0, Number(props.contra) || 0))
const abstCount = computed(() => Math.max(0, Number(props.abstencion) || 0))

const pF = computed(() => (safeTotal.value > 0 ? ((favorCount.value / safeTotal.value) * 100).toFixed(1) : '0.0'))
const pC = computed(() => (safeTotal.value > 0 ? ((contraCount.value / safeTotal.value) * 100).toFixed(1) : '0.0'))
const pA = computed(() => (safeTotal.value > 0 ? ((abstCount.value / safeTotal.value) * 100).toFixed(1) : '0.0'))

const wF = computed(() => (safeTotal.value > 0 ? (favorCount.value / safeTotal.value) * 100 : 0))
const wC = computed(() => (safeTotal.value > 0 ? (contraCount.value / safeTotal.value) * 100 : 0))
const wA = computed(() => {
  if (safeTotal.value <= 0) return 0
  return Math.max(0, 100 - wF.value - wC.value)
})
</script>

<template>
  <div v-if="safeTotal > 0" :class="['vote-bar', { 'vote-bar--sm': small }]">
    <div
      class="vote-bar-seg vote-bar-seg--favor"
      :style="{ width: wF + '%', minWidth: favorCount > 0 ? '2px' : '0px' }"
      :title="'A favor: ' + pF + '%'"
    >
      <template v-if="!small">{{ favor }}</template>
    </div>
    <div
      class="vote-bar-seg vote-bar-seg--contra"
      :style="{ width: wC + '%', minWidth: contraCount > 0 ? '2px' : '0px' }"
      :title="'En contra: ' + pC + '%'"
    >
      <template v-if="!small">{{ contra }}</template>
    </div>
    <div
      class="vote-bar-seg vote-bar-seg--abstencion"
      :style="{ width: wA + '%', minWidth: abstCount > 0 ? '2px' : '0px' }"
      :title="'Abstenciones: ' + pA + '%'"
    >
      <template v-if="!small">{{ abstencion }}</template>
    </div>
  </div>
</template>

<style scoped>
.vote-bar {
  display: flex;
  height: 1.75rem;
  border-radius: 50px;
  overflow: hidden;
  background: var(--color-border);
}

.vote-bar--sm { height: 0.5rem; border-radius: 4px; }

.vote-bar-seg {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  min-width: 2px;
  transition: width 0.3s ease;
}

.vote-bar-seg--favor { background: var(--color-favor); }
.vote-bar-seg--contra { background: var(--color-contra); }
.vote-bar-seg--abstencion { background: var(--color-abstencion); }
</style>
