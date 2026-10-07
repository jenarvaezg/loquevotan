<script setup>
// PROTOTYPE — Variante A «Hemiciclo». La portada abre con una votación dibujada
// como el pleno: el color es del partido y el relleno es el sentido del voto.
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fmt, HIDDEN_TAGS } from '../../utils'
import { usePrototypeData, loadFonts, longDate, shortDate, partyRank, VOTE_WORD } from './usePrototype'

const props = defineProps({ manifest: Object })
loadFonts('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:ital,wght@0,400..900;1,400..700&display=swap')

const data = usePrototypeData()
const { ambitos, currentScopeId, setScope, votaciones, votacionDetail, votosLoaded, loadVotosForLeg } = data
const router = useRouter()

const featured = computed(() => (props.manifest?.featuredVotes || []).slice(0, 5))
const selectedId = ref(null)
watch(featured, (list) => {
  if (!list.some((v) => v.id === selectedId.value)) selectedId.value = list[0]?.id || null
}, { immediate: true })

const sel = computed(() => featured.value.find((v) => v.id === selectedId.value) || null)
const selIdx = computed(() => data.votIdx(selectedId.value))
const selLeg = computed(() => (selIdx.value == null ? null : votaciones.value[selIdx.value]?.legislatura))
watch(selLeg, (leg) => { if (leg) loadVotosForLeg(leg) }, { immediate: true })
const selReady = computed(() => !!selLeg.value && votosLoaded.value.has(selLeg.value))

const resumen = computed(() => (selIdx.value == null ? '' : votacionDetail.value[selIdx.value]?.resumen || ''))
const tally = computed(() => (selReady.value ? data.partyTally(selIdx.value) : []))

// ── Hemicycle geometry ──
const layoutCache = new Map()
function seatLayout(n) {
  if (layoutCache.has(n)) return layoutCache.get(n)
  const r0 = 0.46
  let rows = 3
  const capOf = (rows) => {
    const s = (1 - r0) / (rows - 1)
    return Array.from({ length: rows }, (_, i) => Math.floor((Math.PI * (r0 + i * s)) / s) + 1)
  }
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
  if (!selReady.value) return []
  const ballots = data.ballots(selIdx.value).sort((x, y) =>
    partyRank(x.label) - partyRank(y.label) || x.label.localeCompare(y.label) || VOTE_ORDER[x.voto] - VOTE_ORDER[y.voto]
  )
  const { seats: pos } = seatLayout(ballots.length)
  return ballots.map((b, i) => ({ ...b, x: pos[i].x, y: pos[i].y }))
})
const seatR = computed(() => (seats.value.length ? seatLayout(seats.value.length).radius : 0))
const halfDefs = computed(() => {
  const seen = new Map()
  for (const s of seats.value) if (!seen.has(s.label)) seen.set(s.label, s.color)
  return [...seen.entries()].map(([label, color], i) => ({ label, color, id: `va-half-${i}` }))
})
const halfId = computed(() => Object.fromEntries(halfDefs.value.map((d) => [d.label, d.id])))

function seatStyle(s) {
  if (s.voto === 1) return { fill: s.color, stroke: s.color }
  if (s.voto === 3) return { fill: `url(#${halfId.value[s.label]})`, stroke: s.color }
  if (s.voto === 2) return { fill: 'var(--paper)', stroke: s.color }
  return { fill: 'var(--paper)', stroke: 'var(--vacant)' }
}

function voteWord(code, n) {
  if (code === 3) return n === 1 ? 'abstención' : 'abstenciones'
  return VOTE_WORD[code].toLowerCase()
}

function partyLine(p) {
  if (!p.position) return { main: 'dividido', note: summarize(p.counts, null) }
  return { main: `${p.counts[p.position]} ${voteWord(p.position, p.counts[p.position])}`, note: summarize(p.counts, p.position) }
}

function summarize(counts, skip) {
  const parts = []
  for (const code of [1, 2, 3]) {
    if (code !== skip && counts[code]) parts.push(`${counts[code]} ${voteWord(code, counts[code])}`)
  }
  if (counts[4]) parts.push(`${counts[4]} sin votar`)
  return parts.join(', ')
}

const verdict = computed(() => {
  const v = sel.value
  if (!v) return ''
  const head = v.result === 'Empate' ? 'Empate' : `${v.result} por ${v.margin} ${v.margin === 1 ? 'voto' : 'votos'}`
  return `${head}: ${v.favor} a favor, ${v.contra} en contra${v.abstencion ? ` y ${v.abstencion} abstenciones` : ''}.`
})

// ── Rest of the page ──
const topics = computed(() =>
  (props.manifest?.topTags || []).filter(([t]) => !HIDDEN_TAGS.has(t) && t !== 'procedimiento_parlamentario').slice(0, 14)
)
const query = ref('')
function search() {
  router.push({ path: '/votaciones', query: query.value ? { q: query.value } : {} })
}
function barStyle(v) {
  return { favor: v.favor, contra: v.contra, abst: v.abstencion }
}
const updated = computed(() => longDate(String(props.manifest?.updatedAt || '').slice(0, 10)))
</script>

<template>
  <div class="va">
    <header class="va-top">
      <router-link to="/" class="va-brand">
        <svg viewBox="-1.1 -1.1 2.2 1.2" aria-hidden="true">
          <circle v-for="i in 9" :key="i" :cx="Math.cos(Math.PI - (i - 1) * Math.PI / 8)" :cy="-Math.sin(Math.PI - (i - 1) * Math.PI / 8)" r="0.17" />
          <circle v-for="i in 5" :key="'b' + i" :cx="0.5 * Math.cos(Math.PI - (i - 1) * Math.PI / 4)" :cy="-0.5 * Math.sin(Math.PI - (i - 1) * Math.PI / 4)" r="0.17" />
        </svg>
        Lo Que Votan
      </router-link>
      <nav class="va-nav" aria-label="Secciones">
        <router-link to="/votaciones">Votaciones</router-link>
        <router-link to="/diputados">Diputados</router-link>
        <router-link to="/grupos">Partidos</router-link>
        <router-link to="/quiz">Test de afinidad</router-link>
      </nav>
      <label class="va-scope">
        <span class="va-sr">Parlamento</span>
        <select :value="currentScopeId" @change="setScope($event.target.value)">
          <option v-for="a in ambitos" :key="a.id" :value="a.id">{{ a.nombre }}</option>
        </select>
      </label>
    </header>

    <div class="va-band">
    <section class="va-hero" v-if="sel">
      <div class="va-chamber">
        <div class="va-arc">
        <svg class="va-hemi" viewBox="-1.03 -1.03 2.06 1.08" role="img" :aria-label="`Hemiciclo: ${verdict}`">
          <defs>
            <linearGradient v-for="d in halfDefs" :id="d.id" :key="d.id">
              <stop offset="50%" :stop-color="d.color" />
              <stop offset="50%" stop-color="#fff" />
            </linearGradient>
          </defs>
          <circle
            v-for="(s, i) in seats"
            :key="i"
            class="va-seat"
            :cx="s.x"
            :cy="s.y"
            :r="seatR"
            :stroke-width="seatR * 0.42"
            :style="seatStyle(s)"
          />
        </svg>
        <div class="va-center">
          <p class="va-score">{{ sel.favor }}<span>–</span>{{ sel.contra }}</p>
          <p class="va-result">{{ sel.result }}</p>
        </div>
        </div>
        <ul class="va-legend">
          <li><svg viewBox="-1 -1 2 2"><circle r="0.7" class="lg lg--si" /></svg>A favor</li>
          <li><svg viewBox="-1 -1 2 2"><circle r="0.7" class="lg lg--no" /></svg>En contra</li>
          <li>
            <svg viewBox="-1 -1 2 2">
              <defs><linearGradient id="va-lg-half"><stop offset="50%" stop-color="currentColor" /><stop offset="50%" stop-color="#fff" /></linearGradient></defs>
              <circle r="0.7" class="lg lg--abs" fill="url(#va-lg-half)" />
            </svg>Abstención
          </li>
          <li><svg viewBox="-1 -1 2 2"><circle r="0.7" class="lg lg--nv" /></svg>No vota</li>
        </ul>
      </div>

      <div class="va-story">
        <p class="va-date">{{ longDate(sel.fecha) }}</p>
        <h1>{{ sel.titulo_ciudadano }}</h1>
        <p class="va-verdict">{{ verdict }}</p>
        <p v-if="resumen" class="va-resumen">{{ resumen }}</p>
        <ul class="va-parties" v-if="tally.length">
          <li v-for="p in tally" :key="p.label">
            <span class="va-sw" :style="{ background: p.color }"></span>
            <span class="va-pname">{{ p.label }}</span>
            <span class="va-pmain">{{ partyLine(p).main }}</span>
            <span class="va-pnote">{{ partyLine(p).note }}</span>
          </li>
        </ul>
        <p v-else class="va-loading">Cargando el voto de cada diputado…</p>
        <router-link :to="'/votacion/' + sel.id" class="va-more">Ver cómo votó cada diputado</router-link>
      </div>
    </section>

    <nav class="va-picker" aria-label="Votaciones destacadas" v-if="featured.length > 1">
      <button
        v-for="v in featured"
        :key="v.id"
        type="button"
        :class="{ 'is-on': v.id === selectedId }"
        :aria-pressed="v.id === selectedId"
        @click="selectedId = v.id"
      >
        <span class="va-pdate">{{ shortDate(v.fecha) }}</span>
        {{ v.titulo_ciudadano }}
      </button>
    </nav>
    </div>

    <section class="va-find">
      <form class="va-search" role="search" @submit.prevent="search">
        <label for="va-q">Busca entre {{ manifest?.stats?.votaciones?.toLocaleString('es-ES') }} votaciones</label>
        <div class="va-searchrow">
          <input id="va-q" v-model="query" type="search" placeholder="Vivienda, pensiones, amnistía, un diputado…" />
          <button type="submit">Buscar</button>
        </div>
      </form>
      <ul class="va-topics" aria-label="Temas más votados">
        <li v-for="[tag, count] in topics" :key="tag">
          <router-link :to="{ path: '/votaciones', query: { tag } }">{{ fmt(tag) }} <span>{{ count.toLocaleString('es-ES') }}</span></router-link>
        </li>
      </ul>
    </section>

    <section class="va-lists">
      <div v-for="block in [
        { title: 'Últimas votaciones', items: manifest?.latestVotes || [] },
        { title: 'Decididas por un puñado de votos', items: manifest?.tightVotes || [] },
      ]" :key="block.title" class="va-list">
        <h2>{{ block.title }}</h2>
        <ol>
          <li v-for="v in block.items.slice(0, 7)" :key="v.id">
            <router-link :to="'/votacion/' + v.id" class="va-row">
              <span class="va-rdate">{{ shortDate(v.fecha) }}</span>
              <span class="va-rtitle">{{ v.titulo_ciudadano }}</span>
              <span class="va-bar" :aria-label="`${v.favor} a favor, ${v.contra} en contra, ${v.abstencion} abstenciones`">
                <i class="b-si" :style="{ flex: barStyle(v).favor }"></i>
                <i class="b-abs" :style="{ flex: barStyle(v).abst }"></i>
                <i class="b-no" :style="{ flex: barStyle(v).contra }"></i>
              </span>
              <span class="va-rscore">{{ v.favor }}–{{ v.contra }}</span>
            </router-link>
          </li>
        </ol>
        <router-link to="/votaciones" class="va-more">Todas las votaciones</router-link>
      </div>
    </section>

    <section class="va-quiz">
      <div>
        <h2>¿Con qué partido coincides?</h2>
        <p>Vota a ciegas propuestas que ya pasaron por el pleno y compara tus respuestas con lo que votó cada grupo.</p>
      </div>
      <router-link to="/quiz" class="va-btn">Hacer el test</router-link>
    </section>

    <footer class="va-foot">
      <p>Datos oficiales del Congreso y de los parlamentos autonómicos, actualizados el {{ updated }}. Títulos y temas resumidos con IA.</p>
      <p><router-link to="/metodologia">Metodología</router-link> <a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">Código abierto en GitHub</a></p>
    </footer>
  </div>
</template>

<style scoped>
.va {
  --bg: #f2f3f5;
  --paper: #ffffff;
  --ink: #18212b;
  --ink-2: #525c69;
  --rule: #d6dbe1;
  --vacant: #c3c9d1;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Schibsted Grotesk', system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.5;
}
.va a { color: inherit; }
.va a:hover { color: inherit; }
.va h1, .va h2 { font-family: inherit; color: var(--ink); }
.va-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

/* Header */
.va-top {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 0 32px;
  height: 60px;
  background: var(--paper);
  border-bottom: 1px solid var(--rule);
}
.va-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-weight: 800;
  font-size: 1.1rem;
  letter-spacing: -0.02em;
  text-decoration: none;
  white-space: nowrap;
}
.va-brand:hover { text-decoration: none; }
.va-brand svg { width: 30px; fill: var(--ink); }
.va-nav { display: flex; gap: 1.5rem; margin-right: auto; }
.va-nav a { font-size: 0.95rem; font-weight: 500; color: var(--ink-2); text-decoration: none; }
.va-nav a:hover { color: var(--ink); text-decoration: underline; text-underline-offset: 4px; }
.va-scope select {
  appearance: none;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--paper) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2318212b'/%3E%3C/svg%3E") no-repeat right 10px center;
  padding: 0.4rem 2rem 0.4rem 0.7rem;
  font: 500 0.9rem/1.2 inherit;
  font-family: inherit;
  color: var(--ink);
}

/* Hero */
.va-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 56px;
  padding: 48px 32px 40px;
  max-width: 1320px;
  margin: 0 auto;
}
.va-chamber { position: relative; align-self: start; }
.va-hemi { display: block; width: 100%; height: auto; overflow: visible; }
.va-seat { transition: fill 0.45s ease, stroke 0.45s ease; }
.va-arc { position: relative; }
/* Sits in the empty middle of the arc, on its baseline */
.va-center {
  position: absolute;
  left: 50%;
  bottom: 4%;
  transform: translateX(-50%);
  text-align: center;
  pointer-events: none;
}
.va-score {
  font-size: clamp(1.7rem, 3.6vw, 3rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.va-score span { color: var(--vacant); padding: 0 0.08em; }
.va-result { margin-top: 0.3rem; font-size: 1rem; font-weight: 600; color: var(--ink-2); }
.va-legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.4rem 1.25rem;
  list-style: none;
  margin-top: 1.5rem;
  font-size: 0.85rem;
  color: var(--ink-2);
}
.va-legend li { display: inline-flex; align-items: center; gap: 0.4rem; }
.va-legend svg { width: 14px; height: 14px; color: var(--ink); }
.lg { stroke: var(--ink); stroke-width: 0.28; }
.lg--si { fill: var(--ink); }
.lg--no { fill: #fff; }
.lg--nv { fill: #fff; stroke: var(--vacant); }

.va-story { max-width: 34rem; }
.va-date { font-size: 0.95rem; color: var(--ink-2); margin-bottom: 0.6rem; }
.va-story h1 {
  font-size: clamp(1.9rem, 3.2vw, 2.85rem);
  font-weight: 750;
  line-height: 1.04;
  letter-spacing: -0.03em;
  margin-bottom: 1rem;
  text-wrap: balance;
}
.va-verdict { font-size: 1.15rem; font-weight: 600; margin-bottom: 0.75rem; }
.va-resumen { color: var(--ink-2); margin-bottom: 1.5rem; max-width: 60ch; }
.va-parties { list-style: none; border-top: 1px solid var(--ink); margin-bottom: 1.25rem; }
.va-parties li {
  display: grid;
  grid-template-columns: 12px 7.5rem 8.5rem 1fr;
  align-items: baseline;
  gap: 0.6rem;
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--rule);
  font-size: 0.95rem;
}
.va-sw { width: 12px; height: 12px; border-radius: 50%; align-self: center; }
.va-pname { font-weight: 700; }
.va-pmain { font-variant-numeric: tabular-nums; }
.va-pnote { color: var(--ink-2); font-size: 0.85rem; }
.va-loading { color: var(--ink-2); margin-bottom: 1.25rem; }
.va-more {
  display: inline-block;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 5px;
}

/* Picker */
.va-band { background: var(--paper); border-bottom: 1px solid var(--rule); }
.va-picker {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  max-width: 1320px;
  margin: 0 auto;
  border-top: 1px solid var(--rule);
}
.va-picker button {
  text-align: left;
  border: 0;
  border-top: 3px solid transparent;
  margin-top: -1px;
  background: none;
  padding: 1rem 1.25rem 1.4rem;
  font: inherit;
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.3;
  color: var(--ink-2);
  cursor: pointer;
}
.va-picker button + button { border-left: 1px solid var(--rule); }
.va-picker button:hover { color: var(--ink); }
.va-picker button.is-on { border-top-color: var(--ink); color: var(--ink); }
.va-picker button:focus-visible { outline: 2px solid var(--ink); outline-offset: -2px; }
.va-pdate { display: block; font-weight: 400; font-size: 0.8rem; margin-bottom: 0.25rem; }

/* Find */
.va-find {
  max-width: 1320px;
  margin: 56px auto 0;
  padding: 0 32px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: 56px;
  align-items: start;
}
.va-search label { display: block; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.75rem; }
.va-searchrow { display: flex; }
.va-searchrow input {
  flex: 1;
  min-width: 0;
  border: 2px solid var(--ink);
  border-right: 0;
  border-radius: 4px 0 0 4px;
  padding: 0.75rem 1rem;
  font: inherit;
  background: var(--paper);
  color: var(--ink);
}
.va-searchrow input:focus { outline: 3px solid #9fb3c8; outline-offset: 0; }
.va-searchrow button, .va-btn {
  border: 2px solid var(--ink);
  border-radius: 0 4px 4px 0;
  background: var(--ink);
  color: #fff;
  font: inherit;
  font-weight: 700;
  padding: 0 1.25rem;
  cursor: pointer;
}
.va-topics { list-style: none; display: flex; flex-wrap: wrap; gap: 0.25rem 1.4rem; padding-top: 0.4rem; }
.va-topics a { font-size: 1.05rem; font-weight: 500; text-decoration: none; }
.va-topics a::first-letter { text-transform: uppercase; }
.va-topics a:hover { text-decoration: underline; text-underline-offset: 4px; }
.va-topics span { color: var(--ink-2); font-size: 0.8rem; font-variant-numeric: tabular-nums; }

/* Lists */
.va-lists {
  max-width: 1320px;
  margin: 56px auto 0;
  padding: 0 32px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 56px;
}
.va-list h2 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; padding-bottom: 0.6rem; border-bottom: 2px solid var(--ink); }
.va-list ol { list-style: none; margin-bottom: 1rem; }
.va-row {
  display: grid;
  grid-template-columns: 4.6rem minmax(0, 1fr) 5rem 5rem;
  gap: 0.9rem;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--rule);
  text-decoration: none;
}
.va-row:hover .va-rtitle { text-decoration: underline; text-underline-offset: 3px; }
.va-rdate { font-size: 0.8rem; color: var(--ink-2); }
.va-rtitle { font-weight: 600; line-height: 1.3; }
.va-rscore { font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.va-bar { display: flex; height: 10px; gap: 2px; }
.va-bar i { display: block; min-width: 0; }
.b-si { background: var(--ink); }
.b-no { box-shadow: inset 0 0 0 1.5px var(--ink); background: var(--paper); }
.b-abs { background: repeating-linear-gradient(135deg, var(--ink) 0 1.5px, transparent 1.5px 4px); }

/* Quiz */
.va-quiz {
  max-width: 1256px;
  margin: 64px auto 0;
  padding: 36px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  background: var(--paper);
  border: 2px solid var(--ink);
  border-radius: 4px;
}
.va-quiz h2 { font-size: 1.75rem; font-weight: 750; letter-spacing: -0.025em; margin-bottom: 0.3rem; }
.va-quiz p { color: var(--ink-2); max-width: 56ch; }
.va-btn { border-radius: 4px; padding: 0.85rem 1.5rem; text-decoration: none; white-space: nowrap; color: #fff !important; }
.va-btn:hover { background: #2c3846; text-decoration: none; }

.va-foot {
  max-width: 1320px;
  margin: 64px auto 0;
  padding: 24px 32px 96px;
  border-top: 1px solid var(--rule);
  font-size: 0.9rem;
  color: var(--ink-2);
  display: flex;
  justify-content: space-between;
  gap: 2rem;
}
.va-foot a { text-decoration: underline; text-underline-offset: 3px; margin-left: 1rem; }

@media (max-width: 960px) {
  .va-top { gap: 1rem; padding: 0 16px; }
  .va-nav { display: none; }
  .va-scope { margin-left: auto; }
  .va-scope select { max-width: 52vw; }
  .va-hero { grid-template-columns: 1fr; gap: 28px; padding: 24px 16px; }
  .va-picker { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; }
  .va-picker button { flex: 0 0 72%; scroll-snap-align: start; }
  .va-find, .va-lists { grid-template-columns: 1fr; gap: 36px; padding: 0 16px; margin-top: 40px; }
  .va-parties li { grid-template-columns: 12px 6rem 1fr; }
  .va-pnote { grid-column: 3; }
  .va-row { grid-template-columns: minmax(0, 1fr) 4rem; }
  .va-rdate { grid-column: 1 / -1; margin-bottom: -0.6rem; }
  .va-bar { display: none; }
  .va-quiz { margin: 40px 16px 0; padding: 24px; flex-direction: column; align-items: flex-start; }
  .va-foot { flex-direction: column; padding: 24px 16px 96px; }
  .va-foot a { margin: 0 1rem 0 0; }
}
</style>
