<script setup>
// The chamber for one vote: each seat is a deputy, its colour is the party and
// its fill is the vote. Without nominal votes (`groups` null) seats are drawn
// from the totals in ink, so only the fill carries meaning.
import { computed, useId } from 'vue'
import { seatLayout, ballotsFromGroups, ballotsFromTotals } from '../hemicycle'

const props = defineProps({
  groups: { type: Object, default: null },
  totals: { type: Object, required: true },
  label: { type: String, required: true },
  legend: { type: Boolean, default: true },
})

const uid = useId()
const INK = 'var(--color-text)'

const seats = computed(() => {
  const ballots = props.groups ? ballotsFromGroups(props.groups) : ballotsFromTotals(props.totals)
  const { seats: pos } = seatLayout(ballots.length)
  return ballots.map((b, i) => ({ ...b, color: b.color || INK, x: pos[i].x, y: pos[i].y }))
})
const radius = computed(() => seatLayout(seats.value.length).radius)

// Abstention is a half-filled seat: one gradient per colour in use.
const halves = computed(() => {
  const colors = [...new Set(seats.value.filter((s) => s.voto === 3).map((s) => s.color))]
  return colors.map((color, i) => ({ color, id: `${uid}-half-${i}` }))
})
const halfId = computed(() => Object.fromEntries(halves.value.map((h) => [h.color, h.id])))

function seatStyle(s) {
  if (s.voto === 1) return { fill: s.color, stroke: s.color }
  if (s.voto === 3) return { fill: `url(#${halfId.value[s.color]})`, stroke: s.color }
  if (s.voto === 2) return { fill: 'var(--color-surface)', stroke: s.color }
  return { fill: 'var(--color-surface)', stroke: 'var(--color-vacant)' }
}
</script>

<template>
  <figure class="hemicycle">
    <div class="hemicycle-arc">
      <svg viewBox="-1.03 -1.03 2.06 1.08" role="img" :aria-label="label">
        <defs>
          <linearGradient v-for="h in halves" :id="h.id" :key="h.id">
            <stop offset="50%" :style="{ stopColor: h.color }" />
            <stop offset="50%" style="stop-color: var(--color-surface)" />
          </linearGradient>
        </defs>
        <circle
          v-for="(s, i) in seats"
          :key="i"
          class="hemicycle-seat"
          :cx="s.x"
          :cy="s.y"
          :r="radius"
          :stroke-width="radius * 0.42"
          :style="seatStyle(s)"
        />
      </svg>
      <div class="hemicycle-center"><slot /></div>
    </div>
    <figcaption v-if="legend" class="hemicycle-legend">
      <span><i class="seat seat--si"></i>A favor</span>
      <span><i class="seat seat--no"></i>En contra</span>
      <span><i class="seat seat--abs"></i>Abstención</span>
      <span v-if="groups"><i class="seat seat--nv"></i>No vota</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.hemicycle { margin: 0; }
.hemicycle-arc { position: relative; }
.hemicycle svg { display: block; width: 100%; height: auto; overflow: visible; }
.hemicycle-seat { transition: fill 0.45s ease, stroke 0.45s ease; }

/* Sits in the empty middle of the arc, on its baseline. */
.hemicycle-center {
  position: absolute;
  left: 50%;
  bottom: 4%;
  transform: translateX(-50%);
  text-align: center;
}

.hemicycle-legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.4rem 1.25rem;
  margin-top: 1.25rem;
  font-size: 0.85rem;
  color: var(--color-muted);
}
.hemicycle-legend span { display: inline-flex; align-items: center; gap: 0.4rem; }
.seat {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-text);
  background: var(--color-surface);
}
.seat--si { background: var(--color-text); }
.seat--abs { background: linear-gradient(90deg, var(--color-text) 50%, var(--color-surface) 50%); }
.seat--nv { border-color: var(--color-vacant); }

@media (prefers-reduced-motion: reduce) {
  .hemicycle-seat { transition: none; }
}
</style>
