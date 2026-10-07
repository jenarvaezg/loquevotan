<script setup>
// PROTOTYPE — Variante C «Marcador». La portada es el panel electrónico del
// pleno más una página de resultados densa, como la de una liga: muchas
// votaciones de un vistazo, y la elegida se enciende en el marcador.
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { fmt } from '../../utils'
import { usePrototypeData, loadFonts, shortDate, longDate } from './usePrototype'

const props = defineProps({ manifest: Object })
loadFonts('https://fonts.googleapis.com/css2?family=Doto:wght@600..900&family=Sofia+Sans+Semi+Condensed:ital,wght@0,300..900;1,400..700&display=swap')

const { ambitos, currentScopeId, setScope, votaciones, votResults, categorias, sortedVotIdxByDate } = usePrototypeData()

const recent = computed(() =>
  sortedVotIdxByDate.value.slice(0, 400).map((i) => ({
    i,
    v: votaciones.value[i],
    r: votResults.value[i],
    cat: categorias.value[votaciones.value[i].categoria] || 'Otros',
  }))
)
const cats = computed(() => {
  const counts = new Map()
  for (const row of recent.value) counts.set(row.cat, (counts.get(row.cat) || 0) + 1)
  return [...counts.entries()].filter(([c]) => c !== 'Otros').sort((a, b) => b[1] - a[1]).slice(0, 6).map(([c]) => c)
})
const cat = ref('')
const rows = computed(() => recent.value.filter((row) => !cat.value || row.cat === cat.value).slice(0, 22))

const selected = ref(null)
watch(rows, (list) => {
  if (!list.some((row) => row.i === selected.value)) {
    selected.value = (list.find((row) => row.r.contra >= 20) || list[0])?.i ?? null
  }
}, { immediate: true })
const pos = computed(() => rows.value.findIndex((row) => row.i === selected.value))
const board = computed(() => rows.value[pos.value] || null)
function step(d) {
  const n = rows.value.length
  if (!n) return
  selected.value = rows.value[(pos.value + d + n) % n].i
}
function pick(i, e) {
  selected.value = i
  const top = document.querySelector('.vc-board')?.getBoundingClientRect().top ?? 0
  if (top < 0 && e) window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Digits roll to the new count when another vote is lit.
const shown = ref({ favor: 0, contra: 0, abstencion: 0, total: 0 })
let raf = 0
watch(board, (b) => {
  if (!b) return
  const from = { ...shown.value }
  const to = { favor: b.r.favor, contra: b.r.contra, abstencion: b.r.abstencion, total: b.r.total }
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  cancelAnimationFrame(raf)
  const t0 = performance.now()
  const tick = (t) => {
    const k = reduce ? 1 : Math.min(1, (t - t0) / 450)
    const e = 1 - (1 - k) ** 3
    shown.value = Object.fromEntries(Object.keys(to).map((key) => [key, Math.round(from[key] + (to[key] - from[key]) * e)]))
    if (k < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
}, { immediate: true })
onBeforeUnmount(() => cancelAnimationFrame(raf))

const resultWord = (r) => (r.result === 'Empate' ? 'EMPATE' : r.result.toUpperCase())
const tight = computed(() => (props.manifest?.tightVotes || []).slice(0, 5))
</script>

<template>
  <div class="vc">
    <div class="vc-night">
      <header class="vc-top">
        <router-link to="/" class="vc-brand">Lo Que Votan</router-link>
        <nav class="vc-nav" aria-label="Secciones">
          <router-link to="/votaciones">Votaciones</router-link>
          <router-link to="/diputados">Diputados</router-link>
          <router-link to="/grupos">Partidos</router-link>
          <router-link to="/rankings">Rankings</router-link>
          <router-link to="/quiz">Test</router-link>
        </nav>
        <label class="vc-scope">
          <span class="vc-sr">Parlamento</span>
          <select :value="currentScopeId" @change="setScope($event.target.value)">
            <option v-for="a in ambitos" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </label>
      </header>

      <section v-if="board" class="vc-board" aria-live="polite">
        <div class="vc-board-head">
          <p class="vc-when">{{ longDate(board.v.fecha) }}</p>
          <h1>{{ board.v.titulo_ciudadano }}</h1>
        </div>
        <dl class="vc-counts">
          <div><dt>Sí</dt><dd>{{ shown.favor }}</dd></div>
          <div><dt>No</dt><dd>{{ shown.contra }}</dd></div>
          <div><dt>Abst.</dt><dd>{{ shown.abstencion }}</dd></div>
          <div class="vc-total"><dt>Votos</dt><dd>{{ shown.total }}</dd></div>
        </dl>
        <div class="vc-board-foot">
          <p class="vc-verdict">{{ resultWord(board.r) }}</p>
          <div class="vc-ctrl">
            <button type="button" @click="step(-1)">Anterior</button>
            <button type="button" @click="step(1)">Siguiente</button>
            <router-link :to="'/votacion/' + board.v.id" class="vc-open">Abrir la votación</router-link>
          </div>
        </div>
      </section>
    </div>

    <div class="vc-day">
      <section class="vc-results">
        <div class="vc-results-head">
          <h2>Resultados</h2>
          <div class="vc-tabs" role="group" aria-label="Filtrar por tema">
            <button type="button" :aria-pressed="!cat" @click="cat = ''">Todo</button>
            <button v-for="c in cats" :key="c" type="button" :aria-pressed="cat === c" @click="cat = c">{{ fmt(c) }}</button>
          </div>
        </div>
        <ol>
          <li v-for="row in rows" :key="row.i">
            <button type="button" class="vc-row" :class="{ 'is-lit': row.i === selected }" @click="pick(row.i, $event)">
              <span class="vc-rdate">{{ shortDate(row.v.fecha).replace(/ \d{4}$/, '') }}</span>
              <span class="vc-rtitle">{{ row.v.titulo_ciudadano }}<small>{{ fmt(row.cat) }}</small></span>
              <span class="vc-rscore" :class="row.r.result === 'Aprobada' ? 'won-f' : row.r.result === 'Rechazada' ? 'won-c' : ''">
                <b>{{ row.r.favor }}</b><i>–</i><b>{{ row.r.contra }}</b>
              </span>
              <span class="vc-rres">{{ row.r.result }}</span>
            </button>
          </li>
        </ol>
        <router-link to="/votaciones" class="vc-all">Ver todas las votaciones</router-link>
      </section>

      <aside class="vc-side">
        <h2>Por los pelos</h2>
        <ol class="vc-tight">
          <li v-for="v in tight" :key="v.id">
            <router-link :to="'/votacion/' + v.id">
              <span class="vc-tscore">{{ v.favor }}<i>–</i>{{ v.contra }}</span>
              <span class="vc-ttitle">{{ v.titulo_ciudadano }}</span>
              <span class="vc-tmeta">{{ v.result }}, {{ shortDate(v.fecha) }}</span>
            </router-link>
          </li>
        </ol>
        <div class="vc-quiz">
          <h2>Test de afinidad</h2>
          <p>Vota tú las mismas propuestas, sin saber quién las presentó, y mira con qué grupo coincides.</p>
          <router-link to="/quiz" class="vc-btn">Empezar el test</router-link>
        </div>
      </aside>
    </div>

    <footer class="vc-foot">
      <p>{{ manifest?.stats?.votaciones?.toLocaleString('es-ES') }} votaciones y {{ manifest?.stats?.diputados?.toLocaleString('es-ES') }} diputados, con datos oficiales del Congreso y los parlamentos autonómicos. Títulos y temas resumidos con IA.</p>
      <p><router-link to="/metodologia">Metodología</router-link><a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">GitHub</a></p>
    </footer>
  </div>
</template>

<style scoped>
.vc {
  --night: #1a1e23;
  --led: #ffb21e;
  --day: #e7e9ec;
  --paper: #fff;
  --ink: #1a1e23;
  --ink-2: #5c6570;
  --rule: #d2d6db;
  min-height: 100vh;
  background: var(--day);
  color: var(--ink);
  font-family: 'Sofia Sans Semi Condensed', system-ui, sans-serif;
  font-size: 17px;
  line-height: 1.45;
}
.vc a, .vc a:hover { color: inherit; }
.vc h1, .vc h2 { font-family: inherit; color: inherit; }
.vc-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.vc-night { background: var(--night); color: #e9ecef; padding-bottom: 40px; }
.vc-top { display: flex; align-items: center; gap: 2rem; padding: 18px 40px; }
.vc-brand { font-weight: 800; font-size: 1.15rem; text-decoration: none; margin-right: auto; letter-spacing: 0.01em; }
.vc-nav { display: flex; gap: 1.4rem; }
.vc-nav a { color: #b9c0c8 !important; text-decoration: none; font-weight: 500; }
.vc-nav a:hover { color: #fff !important; }
.vc-scope select {
  appearance: none;
  background: transparent;
  color: #e9ecef;
  border: 1px solid #3a414a;
  border-radius: 3px;
  padding: 0.35rem 0.7rem;
  font: inherit;
  font-size: 0.9rem;
}
.vc-scope option { color: #000; }

.vc-board {
  margin: 12px 40px 0;
  padding: 32px 40px 28px;
  border: 1px solid #343b44;
  border-radius: 6px;
  background:
    radial-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1.3px) 0 0 / 7px 7px,
    #14171b;
}
.vc-board-head { display: flex; flex-direction: column; gap: 0.25rem; max-width: 60rem; }
.vc-when { color: #8d96a0; font-size: 0.95rem; }
.vc-board h1 { font-size: clamp(1.5rem, 2.6vw, 2.2rem); font-weight: 600; line-height: 1.15; color: #fff; text-wrap: balance; }
.vc-counts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(0, 0.8fr);
  margin: 28px 0 20px;
  border-top: 1px solid #2d333b;
  border-bottom: 1px solid #2d333b;
}
.vc-counts > div { padding: 14px 0 10px; }
.vc-counts > div + div { border-left: 1px solid #2d333b; padding-left: 28px; }
.vc-counts dt { color: #8d96a0; font-size: 0.95rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; }
.vc-counts dd {
  font-family: 'Doto', monospace;
  font-weight: 900;
  font-size: clamp(3.5rem, 9vw, 8.5rem);
  line-height: 1;
  color: var(--led);
  text-shadow: 0 0 18px rgba(255, 178, 30, 0.35);
  font-variant-numeric: tabular-nums;
}
.vc-total dd { color: #d9dde2; text-shadow: none; opacity: 0.7; }
.vc-board-foot { display: flex; align-items: center; justify-content: space-between; gap: 1.5rem; flex-wrap: wrap; }
.vc-verdict { font-family: 'Doto', monospace; font-weight: 900; font-size: clamp(1.8rem, 3.6vw, 3rem); color: var(--led); letter-spacing: 0.04em; line-height: 1; }
.vc-ctrl { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.vc-ctrl button, .vc-open {
  border: 1px solid #3f4751;
  background: transparent;
  color: #e9ecef !important;
  padding: 0.5rem 0.9rem;
  border-radius: 3px;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}
.vc-ctrl button:hover { border-color: #8d96a0; }
.vc-open { background: var(--led); color: #1a1e23 !important; border-color: var(--led); }
.vc-open:hover { text-decoration: none; filter: brightness(1.08); }

.vc-day {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 40px;
  padding: 40px;
  align-items: start;
}
.vc-results { background: var(--paper); border-radius: 6px; padding: 24px 28px; }
.vc-results-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.vc-results h2, .vc-side h2 { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.01em; }
.vc-tabs { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.vc-tabs button {
  border: 0;
  background: none;
  padding: 0.3rem 0.6rem;
  border-radius: 3px;
  font: inherit;
  font-size: 0.92rem;
  color: var(--ink-2);
  cursor: pointer;
}
.vc-tabs button[aria-pressed='true'] { background: var(--ink); color: #fff; }
.vc-results ol { list-style: none; }
.vc-row {
  display: grid;
  grid-template-columns: 3.6rem minmax(0, 1fr) 7.5rem 5.6rem;
  gap: 1rem;
  align-items: center;
  width: 100%;
  padding: 0.6rem 0.5rem;
  border: 0;
  border-bottom: 1px solid var(--rule);
  background: none;
  text-align: left;
  font: inherit;
  color: inherit;
  cursor: pointer;
}
.vc-row:hover { background: #f4f5f7; }
.vc-row.is-lit { background: #fff6e0; box-shadow: inset 4px 0 0 var(--led); }
.vc-row:focus-visible { outline: 2px solid var(--ink); outline-offset: -2px; }
.vc-rdate { font-size: 0.9rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.vc-rtitle { font-weight: 600; line-height: 1.25; }
.vc-rtitle small { display: block; font-weight: 400; color: var(--ink-2); font-size: 0.82rem; margin-top: 0.1rem; }
.vc-rscore { font-size: 1.45rem; font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }
.vc-rscore b { font-weight: 400; }
.vc-rscore i { font-style: normal; color: #a4abb4; padding: 0 0.15em; }
.vc-rscore.won-f b:first-child, .vc-rscore.won-c b:last-child { font-weight: 800; }
.vc-rres { font-size: 0.9rem; color: var(--ink-2); }
.vc-all { display: inline-block; margin-top: 1rem; font-weight: 700; text-decoration: underline; text-underline-offset: 4px; }

.vc-side { display: flex; flex-direction: column; gap: 28px; }
.vc-tight { list-style: none; margin-top: 0.5rem; }
.vc-tight a { display: block; padding: 0.9rem 0; border-bottom: 1px solid var(--rule); text-decoration: none; }
.vc-tight a:hover .vc-ttitle { text-decoration: underline; text-underline-offset: 3px; }
.vc-tscore { display: block; font-size: 2.6rem; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.vc-tscore i { font-style: normal; color: #a4abb4; font-weight: 400; padding: 0 0.1em; }
.vc-ttitle { display: block; font-weight: 600; margin-top: 0.35rem; line-height: 1.25; }
.vc-tmeta { display: block; font-size: 0.88rem; color: var(--ink-2); }
.vc-quiz { background: var(--night); color: #e9ecef; border-radius: 6px; padding: 24px; }
.vc-quiz p { color: #b9c0c8; margin: 0.4rem 0 1.2rem; }
.vc-btn { display: inline-block; background: var(--led); color: #1a1e23 !important; font-weight: 700; padding: 0.6rem 1.1rem; border-radius: 3px; text-decoration: none; }
.vc-btn:hover { text-decoration: none; filter: brightness(1.08); }

.vc-foot { display: flex; justify-content: space-between; gap: 2rem; padding: 8px 40px 96px; color: var(--ink-2); font-size: 0.92rem; }
.vc-foot p { max-width: 72ch; }
.vc-foot a { margin-left: 1.25rem; text-decoration: underline; text-underline-offset: 3px; }

@media (max-width: 900px) {
  .vc-top { padding: 14px 16px; gap: 1rem; flex-wrap: wrap; }
  .vc-nav { order: 3; width: 100%; overflow-x: auto; gap: 1.1rem; }
  .vc-scope select { max-width: 50vw; }
  .vc-board { margin: 8px 16px 0; padding: 20px 18px; }
  .vc-counts { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .vc-counts > div + div { padding-left: 12px; }
  .vc-total { display: none; }
  .vc-day { grid-template-columns: 1fr; padding: 24px 16px; gap: 24px; }
  .vc-results { padding: 16px; }
  .vc-row { grid-template-columns: minmax(0, 1fr) auto; gap: 0.4rem 0.8rem; }
  .vc-rdate { grid-column: 1 / -1; }
  .vc-rres { display: none; }
  .vc-foot { flex-direction: column; padding: 8px 16px 96px; }
  .vc-foot a { margin: 0 1.25rem 0 0; }
}
</style>
