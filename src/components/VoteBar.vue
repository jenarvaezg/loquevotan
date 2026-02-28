<script setup>
import { computed } from 'vue'

const props = defineProps({
  favor: Number,
  contra: Number,
  abstencion: Number,
  total: Number,
  small: Boolean,
})

const pF = computed(() => ((props.favor / props.total) * 100).toFixed(1))
const pC = computed(() => ((props.contra / props.total) * 100).toFixed(1))
const pA = computed(() => ((props.abstencion / props.total) * 100).toFixed(1))
</script>

<template>
  <div v-if="total > 0" :class="['vote-bar', { 'vote-bar--sm': small }]">
    <div
      class="vote-bar-seg vote-bar-seg--favor"
      :style="{ width: pF + '%' }"
      :title="'A favor: ' + pF + '%'"
    >
      <template v-if="!small">{{ favor }}</template>
    </div>
    <div
      class="vote-bar-seg vote-bar-seg--contra"
      :style="{ width: pC + '%' }"
      :title="'En contra: ' + pC + '%'"
    >
      <template v-if="!small">{{ contra }}</template>
    </div>
    <div
      class="vote-bar-seg vote-bar-seg--abstencion"
      :style="{ width: pA + '%' }"
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
