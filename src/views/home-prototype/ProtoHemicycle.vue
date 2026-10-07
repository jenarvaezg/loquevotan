<script setup>
// PROTOTYPE — hemiciclo compartido por las variantes E y F. Color = partido,
// relleno = voto. Con `focus`, solo ese partido conserva su color.
import { computed } from 'vue'
import { partyRank } from './usePrototype'

const props = defineProps({
  ballots: { type: Array, default: () => [] },
  focus: { type: String, default: null },
  label: { type: String, default: '' },
  legend: { type: Boolean, default: true },
  pickable: { type: Boolean, default: false },
})
const emit = defineEmits(['pick'])

const uid = 'ph' + Math.random().toString(36).slice(2, 7)
const DIM = '#cfd3d8'

const layoutCache = new Map()
function seatLayout(n) {
  if (layoutCache.has(n)) return layoutCache.get(n)
  const r0 = 0.46
  const capOf = (rows) => {
    const s = (1 - r0) / (rows - 1)
    return Array.from({ length: rows }, (_, i) => Math.floor((Math.PI * (r0 + i * s)) / s) + 1)
  }
  let rows = 3
  while (capOf(rows).reduce((a, b) => a + b, 0) < n) rows++
  const s = (1 - r0) / (rows - 1)
  const caps = capOf(rows)
  const capTotal = caps.reduce((a, b) => a + b, 0)
  const counts = caps.map((c) => Math.floor((c * n) / capTotal))
  let rem = n - counts.reduce((a, b) => a + b, 0)
  for (let i = rows - 1; rem > 0; i = (i - 1 + rows) % rows) {
    if (counts[i] < caps[i]) { counts[i]++; rem-- }
  }
  const seats = []
  counts.forEach((cnt, i) => {
    const rr = r0 + i * s
    for (let j = 0; j < cnt; j++) {
      const a = cnt === 1 ? Math.PI / 2 : Math.PI - (j * Math.PI) / (cnt - 1)
      seats.push({ x: rr * Math.cos(a), y: -rr * Math.sin(a), a, rr })
    }
  })
  seats.sort((p, q) => q.a - p.a || p.rr - q.rr)
  const layout = { seats, radius: s * 0.4 }
  layoutCache.set(n, layout)
  return layout
}

const VOTE_ORDER = { 1: 0, 3: 1, 2: 2, 4: 3 }
const seats = computed(() => {
  const sorted = [...props.ballots].sort((x, y) =>
    partyRank(x.label) - partyRank(y.label) || x.label.localeCompare(y.label) || VOTE_ORDER[x.voto] - VOTE_ORDER[y.voto]
  )
  if (!sorted.length) return []
  const { seats: pos } = seatLayout(sorted.length)
  return sorted.map((b, i) => ({ ...b, x: pos[i].x, y: pos[i].y }))
})
const seatR = computed(() => (seats.value.length ? seatLayout(seats.value.length).radius : 0))
const halves = computed(() => {
  const seen = new Map([['__dim', DIM]])
  for (const s of seats.value) if (!seen.has(s.label)) seen.set(s.label, s.color)
  return [...seen.entries()].map(([label, color], i) => ({ label, color, id: `${uid}-${i}` }))
})
const halfId = computed(() => Object.fromEntries(halves.value.map((h) => [h.label, h.id])))

function seatStyle(s) {
  const dim = props.focus && s.label !== props.focus
  const c = dim ? DIM : s.color
  if (s.voto === 1) return { fill: c, stroke: c }
  if (s.voto === 3) return { fill: `url(#${halfId.value[dim ? '__dim' : s.label]})`, stroke: c }
  if (s.voto === 2) return { fill: '#fff', stroke: c }
  return { fill: '#fff', stroke: dim ? '#e4e7ea' : '#c3c9d1' }
}
</script>

<template>
  <div class="ph">
    <div class="ph-arc">
      <svg viewBox="-1.03 -1.03 2.06 1.08" role="img" :aria-label="label" :class="{ 'is-pickable': pickable }">
        <defs>
          <linearGradient v-for="h in halves" :id="h.id" :key="h.id">
            <stop offset="50%" :stop-color="h.color" />
            <stop offset="50%" stop-color="#fff" />
          </linearGradient>
        </defs>
        <circle
          v-for="(s, i) in seats"
          :key="i"
          class="ph-seat"
          :cx="s.x"
          :cy="s.y"
          :r="seatR"
          :stroke-width="seatR * 0.42"
          :style="seatStyle(s)"
          @click="pickable && emit('pick', s.label)"
        >
          <title>{{ s.label }}</title>
        </circle>
      </svg>
      <div class="ph-center"><slot /></div>
    </div>
    <ul v-if="legend" class="ph-legend">
      <li><svg viewBox="-1 -1 2 2"><circle r="0.7" class="lg lg--si" /></svg>A favor</li>
      <li><svg viewBox="-1 -1 2 2"><circle r="0.7" class="lg lg--no" /></svg>En contra</li>
      <li>
        <svg viewBox="-1 -1 2 2">
          <defs><linearGradient :id="uid + '-lg'"><stop offset="50%" stop-color="currentColor" /><stop offset="50%" stop-color="#fff" /></linearGradient></defs>
          <circle r="0.7" class="lg" :fill="`url(#${uid}-lg)`" />
        </svg>Abstención
      </li>
      <li><svg viewBox="-1 -1 2 2"><circle r="0.7" class="lg lg--nv" /></svg>No vota</li>
    </ul>
  </div>
</template>

<style scoped>
.ph-arc { position: relative; }
.ph svg { display: block; width: 100%; height: auto; overflow: visible; }
.ph-seat { transition: fill 0.45s ease, stroke 0.45s ease; }
.is-pickable .ph-seat { cursor: pointer; }
.ph-center {
  position: absolute;
  left: 50%;
  bottom: 4%;
  transform: translateX(-50%);
  text-align: center;
  pointer-events: none;
}
.ph-legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.4rem 1.25rem;
  list-style: none;
  margin-top: 1.25rem;
  font-size: 0.85rem;
  color: #525c69;
}
.ph-legend li { display: inline-flex; align-items: center; gap: 0.4rem; }
.ph-legend svg { width: 14px; height: 14px; color: #18212b; }
.lg { stroke: #18212b; stroke-width: 0.28; }
.lg--si { fill: #18212b; }
.lg--no { fill: #fff; }
.lg--nv { fill: #fff; stroke: #c3c9d1; }
</style>
