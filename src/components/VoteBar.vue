<script setup>
import { computed } from 'vue'

const props = defineProps({
  favor: Number,
  contra: Number,
  abstencion: Number,
  noVota: Number,
  total: Number,
  small: Boolean,
})

const safeTotal = computed(() => Math.max(0, Number(props.total) || 0))
const favorCount = computed(() => Math.max(0, Number(props.favor) || 0))
const contraCount = computed(() => Math.max(0, Number(props.contra) || 0))
const abstCount = computed(() => Math.max(0, Number(props.abstencion) || 0))

const noVotaCount = computed(() => {
  if (Number.isFinite(props.noVota)) return Math.max(0, Number(props.noVota) || 0)
  const inferred = safeTotal.value - favorCount.value - contraCount.value - abstCount.value
  return Math.max(0, inferred)
})

const effectiveTotal = computed(() => {
  const sum = favorCount.value + contraCount.value + abstCount.value + noVotaCount.value
  return Math.max(safeTotal.value, sum)
})

function percentage(value) {
  if (effectiveTotal.value <= 0) return 0
  return (value / effectiveTotal.value) * 100
}

const wF = computed(() => percentage(favorCount.value))
const wC = computed(() => percentage(contraCount.value))
const wA = computed(() => percentage(abstCount.value))
const wN = computed(() => percentage(noVotaCount.value))

const pF = computed(() => wF.value.toFixed(1))
const pC = computed(() => wC.value.toFixed(1))
const pA = computed(() => wA.value.toFixed(1))
const pN = computed(() => wN.value.toFixed(1))
</script>

<template>
  <div v-if="effectiveTotal > 0" :class="['vote-bar', { 'vote-bar--sm': small }]">
    <div
      v-if="favorCount > 0"
      class="vote-bar-seg vote-bar-seg--favor"
      :style="{ flex: favorCount }"
      :title="'A favor: ' + pF + '%'"
    >
      <template v-if="!small">{{ favorCount }}</template>
    </div>
    <div
      v-if="contraCount > 0"
      class="vote-bar-seg vote-bar-seg--contra"
      :style="{ flex: contraCount }"
      :title="'En contra: ' + pC + '%'"
    >
      <template v-if="!small">{{ contraCount }}</template>
    </div>
    <div
      v-if="abstCount > 0"
      class="vote-bar-seg vote-bar-seg--abstencion"
      :style="{ flex: abstCount }"
      :title="'Abstenciones: ' + pA + '%'"
    >
      <template v-if="!small">{{ abstCount }}</template>
    </div>
    <div
      v-if="noVotaCount > 0"
      class="vote-bar-seg vote-bar-seg--no-vota"
      :style="{ flex: noVotaCount }"
      :title="'No vota: ' + pN + '%'"
    >
      <template v-if="!small">{{ noVotaCount }}</template>
    </div>
  </div>
</template>

<style scoped>
.vote-bar {
  display: flex;
  height: 1.75rem;
  border-radius: 50px;
  overflow: hidden;
  background: transparent;
  gap: 2px;
}

.vote-bar--sm { height: 0.5rem; border-radius: 4px; }

.vote-bar-seg {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  transition: flex 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.vote-bar-seg--favor { background: var(--color-favor); }
.vote-bar-seg--contra { background: var(--color-contra); }
.vote-bar-seg--abstencion { background: var(--color-abstencion); }
.vote-bar-seg--no-vota { background: var(--color-no-vota); }
</style>
