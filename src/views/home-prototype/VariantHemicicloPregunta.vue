<script setup>
// PROTOTYPE — Variante F «Hemiciclo → pregunta». Manda el hemiciclo de A, pero
// cada votación se presenta como la pregunta que responde («¿…? No.») y la
// herramienta de B queda como segunda sección: «Pregúntale a un partido».
import { computed, ref, watch } from 'vue'
import { fmt } from '../../utils'
import { usePrototypeData, loadFonts, longDate, shortDate, VOTE_WORD } from './usePrototype'
import { useTopicQuestion, named } from './useTopicQuestion'
import ProtoHemicycle from './ProtoHemicycle.vue'

const props = defineProps({ manifest: Object })
loadFonts('https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&display=swap')

const data = usePrototypeData()
const { ambitos, currentScopeId, setScope, votaciones, votacionDetail, votosLoaded, loadVotosForLeg, votosReady, legParties, legTopics, partyPosition } = data
const { partyKey, topic, accent, topicVotes, answer, lead, detail, others, shortcuts, party } = useTopicQuestion(data)

// ── Featured vote as a question ──
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
const selBallots = computed(() => (selReady.value ? data.ballots(selIdx.value) : []))
const tally = computed(() => (selReady.value ? data.partyTally(selIdx.value) : []))
const resumen = computed(() => (selIdx.value == null ? '' : votacionDetail.value[selIdx.value]?.resumen || ''))

const ANSWER = { Aprobada: 'Sí.', Rechazada: 'No.', Empate: 'Empate.' }
const verdict = computed(() => {
  const v = sel.value
  if (!v) return ''
  const head = v.result === 'Empate' ? 'Empate' : `${v.result} por ${v.margin} ${v.margin === 1 ? 'voto' : 'votos'}`
  return `${head}: ${v.favor} a favor, ${v.contra} en contra${v.abstencion ? ` y ${v.abstencion} abstenciones` : ''}.`
})

function voteWord(code, n) {
  if (code === 3) return n === 1 ? 'abstención' : 'abstenciones'
  return VOTE_WORD[code].toLowerCase()
}
function partyLine(p) {
  const parts = []
  for (const code of [1, 2, 3]) {
    if (code !== p.position && p.counts[code]) parts.push(`${p.counts[code]} ${voteWord(code, p.counts[code])}`)
  }
  if (p.counts[4]) parts.push(`${p.counts[4]} sin votar`)
  return {
    main: p.position ? `${p.counts[p.position]} ${voteWord(p.position, p.counts[p.position])}` : 'dividido',
    note: parts.join(', '),
  }
}

// ── Ask a party ──
const askRows = computed(() =>
  party.value ? topicVotes.value.slice(0, 6).map((i) => ({ i, v: votaciones.value[i], pos: partyPosition(i, party.value) })) : []
)
const updated = computed(() => longDate(String(props.manifest?.updatedAt || '').slice(0, 10)))
</script>

<template>
  <div class="vf">
    <header class="vf-top">
      <router-link to="/" class="vf-brand">
        <svg viewBox="-1.1 -1.1 2.2 1.2" aria-hidden="true">
          <circle v-for="i in 9" :key="i" :cx="Math.cos(Math.PI - (i - 1) * Math.PI / 8)" :cy="-Math.sin(Math.PI - (i - 1) * Math.PI / 8)" r="0.17" />
          <circle v-for="i in 5" :key="'b' + i" :cx="0.5 * Math.cos(Math.PI - (i - 1) * Math.PI / 4)" :cy="-0.5 * Math.sin(Math.PI - (i - 1) * Math.PI / 4)" r="0.17" />
        </svg>
        Lo Que Votan
      </router-link>
      <nav class="vf-nav" aria-label="Secciones">
        <router-link to="/votaciones">Votaciones</router-link>
        <router-link to="/diputados">Diputados</router-link>
        <router-link to="/grupos">Partidos</router-link>
        <router-link to="/quiz">Test de afinidad</router-link>
      </nav>
      <label class="vf-scope">
        <span class="vf-sr">Parlamento</span>
        <select :value="currentScopeId" @change="setScope($event.target.value)">
          <option v-for="a in ambitos" :key="a.id" :value="a.id">{{ a.nombre }}</option>
        </select>
      </label>
    </header>

    <div class="vf-band">
      <section class="vf-hero" v-if="sel">
        <ProtoHemicycle :ballots="selBallots" :label="`Hemiciclo: ${verdict}`">
          <p class="vf-score">{{ sel.favor }}<span>–</span>{{ sel.contra }}</p>
        </ProtoHemicycle>

        <div class="vf-story">
          <p class="vf-date">Votado el {{ longDate(sel.fecha) }}</p>
          <h1>¿{{ sel.titulo_ciudadano }}?</h1>
          <p class="vf-answer"><strong>{{ ANSWER[sel.result] || sel.result }}</strong> {{ verdict }}</p>
          <p v-if="resumen" class="vf-resumen">{{ resumen }}</p>
          <ul class="vf-parties" v-if="tally.length">
            <li v-for="p in tally" :key="p.label">
              <span class="vf-sw" :style="{ background: p.color }"></span>
              <span class="vf-pname">{{ p.label }}</span>
              <span class="vf-pmain">{{ partyLine(p).main }}</span>
              <span class="vf-pnote">{{ partyLine(p).note }}</span>
            </li>
          </ul>
          <p v-else class="vf-muted">Cargando el voto de cada diputado…</p>
          <router-link :to="'/votacion/' + sel.id" class="vf-more">Ver cómo votó cada diputado</router-link>
        </div>
      </section>

      <nav class="vf-picker" aria-label="Otras preguntas que ha respondido el pleno" v-if="featured.length > 1">
        <button
          v-for="v in featured"
          :key="v.id"
          type="button"
          :class="{ 'is-on': v.id === selectedId }"
          :aria-pressed="v.id === selectedId"
          @click="selectedId = v.id"
        >
          <span class="vf-pq">¿{{ v.titulo_ciudadano }}?</span>
          <span class="vf-pa">{{ ANSWER[v.result] || v.result }} {{ v.favor }}–{{ v.contra }}</span>
        </button>
      </nav>
    </div>

    <section class="vf-ask" :style="{ '--accent': accent }">
      <h2 class="vf-ask-title">Pregúntale a un partido</h2>
      <p class="vf-q">
        ¿Votó
        <span class="vf-slot">
          <span aria-hidden="true">{{ named(partyKey) }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="partyKey" aria-label="Partido">
            <option v-for="p in legParties" :key="p.label" :value="p.label">{{ named(p.label) }}</option>
          </select>
        </span>
        a favor de
        <span class="vf-slot">
          <span aria-hidden="true">{{ fmt(topic) }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="topic" aria-label="Tema">
            <option v-for="[t, n] in legTopics" :key="t" :value="t">{{ fmt(t) }} ({{ n }})</option>
          </select>
        </span>?
      </p>
      <p class="vf-try" v-if="shortcuts.length">
        Otros temas:
        <button v-for="t in shortcuts.slice(0, 5)" :key="t" type="button" @click="topic = t">{{ fmt(t) }}</button>
      </p>

      <div class="vf-ask-grid" v-if="votosReady && answer" aria-live="polite">
        <div>
          <p class="vf-big"><strong>{{ answer.counts[1] }}</strong> de {{ answer.n }}</p>
          <p class="vf-lead">{{ lead }}</p>
          <p class="vf-detail">{{ detail }}</p>
        </div>
        <ol class="vf-arows">
          <li v-for="r in askRows" :key="r.i">
            <router-link :to="'/votacion/' + r.v.id">
              <span class="vf-adate">{{ shortDate(r.v.fecha) }}</span>
              <span class="vf-atitle">{{ r.v.titulo_ciudadano }}</span>
              <span class="vf-apos" :class="'is-' + (r.pos || 0)">{{ r.pos ? VOTE_WORD[r.pos] : 'Dividido' }}</span>
            </router-link>
          </li>
        </ol>
        <ul class="vf-others">
          <li v-for="o in others" :key="o.p.label" :class="{ 'is-on': o.p.label === partyKey }">
            <button type="button" @click="partyKey = o.p.label">{{ o.p.label }}</button>
            <span class="vf-obar" :style="{ '--c': o.p.color }">
              <i class="f" :style="{ flex: o.counts[1] }"></i>
              <i class="a" :style="{ flex: o.counts[3] }"></i>
              <i class="c" :style="{ flex: o.counts[2] }"></i>
            </span>
            <span class="vf-on">{{ o.counts[1] }}/{{ o.n }}</span>
          </li>
        </ul>
      </div>
      <p v-else class="vf-muted">Cargando las votaciones de esta legislatura…</p>
    </section>

    <section class="vf-lists">
      <div v-for="block in [
        { title: 'Últimas votaciones', items: manifest?.latestVotes || [] },
        { title: 'Decididas por un puñado de votos', items: manifest?.tightVotes || [] },
      ]" :key="block.title" class="vf-list">
        <h2>{{ block.title }}</h2>
        <ol>
          <li v-for="v in block.items.slice(0, 6)" :key="v.id">
            <router-link :to="'/votacion/' + v.id" class="vf-row">
              <span class="vf-rdate">{{ shortDate(v.fecha) }}</span>
              <span class="vf-rtitle">{{ v.titulo_ciudadano }}</span>
              <span class="vf-bar" :aria-label="`${v.favor} a favor, ${v.contra} en contra, ${v.abstencion} abstenciones`">
                <i class="b-si" :style="{ flex: v.favor }"></i>
                <i class="b-abs" :style="{ flex: v.abstencion }"></i>
                <i class="b-no" :style="{ flex: v.contra }"></i>
              </span>
              <span class="vf-rscore">{{ v.favor }}–{{ v.contra }}</span>
            </router-link>
          </li>
        </ol>
        <router-link to="/votaciones" class="vf-more">Todas las votaciones</router-link>
      </div>
    </section>

    <section class="vf-quiz">
      <div>
        <h2>¿Y tú, qué habrías votado?</h2>
        <p>Vota a ciegas propuestas que ya pasaron por el pleno y compara tus respuestas con lo que votó cada grupo.</p>
      </div>
      <router-link to="/quiz" class="vf-btn">Hacer el test</router-link>
    </section>

    <footer class="vf-foot">
      <p>Datos oficiales del Congreso y de los parlamentos autonómicos, actualizados el {{ updated }}. Títulos y temas resumidos con IA.</p>
      <p><router-link to="/metodologia">Metodología</router-link> <a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">Código abierto en GitHub</a></p>
    </footer>
  </div>
</template>

<style scoped>
.vf {
  --bg: #f2f3f5;
  --paper: #fff;
  --ink: #18212b;
  --ink-2: #525c69;
  --rule: #d6dbe1;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: 'Archivo', system-ui, sans-serif;
  font-size: 16.5px;
  line-height: 1.5;
}
.vf a, .vf a:hover { color: inherit; }
.vf h1, .vf h2 { font-family: inherit; color: inherit; }
.vf-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.vf-muted { color: var(--ink-2); margin-bottom: 1.25rem; }

.vf-top { display: flex; align-items: center; gap: 2rem; padding: 0 32px; height: 60px; background: var(--paper); border-bottom: 1px solid var(--rule); }
.vf-brand { display: inline-flex; align-items: center; gap: 0.55rem; font-weight: 800; font-stretch: 110%; font-size: 1.05rem; text-decoration: none; white-space: nowrap; }
.vf-brand svg { width: 30px; fill: var(--ink); }
.vf-nav { display: flex; gap: 1.5rem; margin-right: auto; }
.vf-nav a { font-size: 0.95rem; font-weight: 500; color: var(--ink-2) !important; text-decoration: none; }
.vf-nav a:hover { color: var(--ink) !important; text-decoration: underline; text-underline-offset: 4px; }
.vf-scope select {
  appearance: none;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--paper) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2318212b'/%3E%3C/svg%3E") no-repeat right 10px center;
  padding: 0.4rem 2rem 0.4rem 0.7rem;
  font: inherit;
  font-size: 0.9rem;
  color: var(--ink);
}

.vf-band { background: var(--paper); border-bottom: 1px solid var(--rule); }
.vf-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 56px;
  padding: 48px 32px 40px;
  max-width: 1320px;
  margin: 0 auto;
  align-items: start;
}
.vf-score { font-size: clamp(1.7rem, 3.6vw, 3rem); font-weight: 800; font-stretch: 80%; letter-spacing: -0.02em; line-height: 1; font-variant-numeric: tabular-nums; }
.vf-score span { color: #c3c9d1; padding: 0 0.06em; }
.vf-story { max-width: 36rem; }
.vf-date { font-size: 0.95rem; color: var(--ink-2); margin-bottom: 0.5rem; }
.vf-story h1 { font-size: clamp(2.2rem, 4vw, 3.6rem); font-weight: 800; font-stretch: 72%; line-height: 0.98; letter-spacing: -0.02em; margin-bottom: 1rem; text-wrap: balance; }
.vf-answer { font-size: 1.15rem; margin-bottom: 0.8rem; }
.vf-answer strong { font-size: 2.6rem; font-weight: 800; font-stretch: 72%; line-height: 1; margin-right: 0.3rem; vertical-align: -0.12em; }
.vf-resumen { color: var(--ink-2); margin-bottom: 1.5rem; max-width: 60ch; }
.vf-parties { list-style: none; border-top: 1px solid var(--ink); margin-bottom: 1.25rem; }
.vf-parties li { display: grid; grid-template-columns: 12px 7rem 8.5rem 1fr; align-items: baseline; gap: 0.6rem; padding: 0.42rem 0; border-bottom: 1px solid var(--rule); font-size: 0.95rem; }
.vf-sw { width: 12px; height: 12px; border-radius: 50%; align-self: center; }
.vf-pname { font-weight: 700; }
.vf-pmain { font-variant-numeric: tabular-nums; }
.vf-pnote { color: var(--ink-2); font-size: 0.85rem; }
.vf-more { display: inline-block; font-weight: 600; text-decoration: underline; text-decoration-thickness: 2px; text-underline-offset: 5px; }

.vf-picker { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); max-width: 1320px; margin: 0 auto; border-top: 1px solid var(--rule); }
.vf-picker button {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  text-align: left;
  border: 0;
  border-top: 3px solid transparent;
  margin-top: -1px;
  background: none;
  padding: 1rem 1.25rem 1.4rem;
  font: inherit;
  color: var(--ink-2);
  cursor: pointer;
}
.vf-picker button + button { border-left: 1px solid var(--rule); }
.vf-picker button:hover { color: var(--ink); }
.vf-picker button.is-on { border-top-color: var(--ink); color: var(--ink); }
.vf-picker button:focus-visible { outline: 2px solid var(--ink); outline-offset: -2px; }
.vf-pq { font-weight: 700; font-stretch: 85%; font-size: 1.02rem; line-height: 1.2; }
.vf-pa { font-size: 0.85rem; font-variant-numeric: tabular-nums; }

.vf-ask { max-width: 1320px; margin: 64px auto 0; padding: 0 32px; }
.vf-ask-title { font-size: 1rem; font-weight: 600; color: var(--ink-2); margin-bottom: 0.4rem; }
.vf-q { font-size: clamp(2rem, 4.6vw, 4.2rem); font-weight: 800; font-stretch: 72%; line-height: 1; letter-spacing: -0.02em; text-wrap: balance; }
.vf-slot { position: relative; display: inline-flex; align-items: baseline; gap: 0.12em; color: var(--accent); border-bottom: 0.08em solid var(--accent); line-height: 1; transition: color 0.3s, border-color 0.3s; }
.vf-slot svg { width: 0.28em; height: 0.18em; fill: currentColor; align-self: center; }
.vf-slot select { position: absolute; inset: 0; width: 100%; opacity: 0; cursor: pointer; font-size: 16px; }
.vf-slot:focus-within { outline: 3px solid var(--ink); outline-offset: 6px; }
.vf-try { margin-top: 1.25rem; color: var(--ink-2); display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; align-items: baseline; }
.vf-try button { border: 0; background: none; padding: 0; font: inherit; color: var(--ink); text-decoration: underline; text-decoration-color: var(--rule); text-decoration-thickness: 2px; text-underline-offset: 4px; cursor: pointer; }
.vf-try button:hover { text-decoration-color: var(--accent); }
.vf-ask-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr) minmax(0, 0.9fr);
  gap: 48px;
  margin-top: 32px;
  padding-top: 32px;
  border-top: 2px solid var(--ink);
}
.vf-big { font-size: clamp(2.8rem, 5vw, 4.6rem); font-weight: 300; font-stretch: 72%; line-height: 1; letter-spacing: -0.03em; }
.vf-big strong { font-weight: 800; color: var(--accent); }
.vf-lead { font-size: 1.35rem; font-weight: 700; margin: 0.8rem 0 0.4rem; line-height: 1.2; }
.vf-detail { color: var(--ink-2); }
.vf-arows { list-style: none; }
.vf-arows a { display: grid; grid-template-columns: minmax(0, 1fr) 6rem; gap: 0 0.8rem; padding: 0.55rem 0; border-bottom: 1px solid var(--rule); text-decoration: none; }
.vf-arows li:first-child a { padding-top: 0; }
.vf-arows a:hover .vf-atitle { text-decoration: underline; text-underline-offset: 3px; }
.vf-adate { grid-column: 1 / -1; font-size: 0.8rem; color: var(--ink-2); }
.vf-atitle { font-weight: 500; line-height: 1.3; }
.vf-apos { font-weight: 700; text-align: right; font-stretch: 85%; }
.vf-apos.is-1 { color: var(--accent); }
.vf-apos.is-0, .vf-apos.is-3 { color: var(--ink-2); }
.vf-others { list-style: none; }
.vf-others li { display: grid; grid-template-columns: 5.2rem minmax(0, 1fr) 2.6rem; gap: 0.7rem; align-items: center; padding: 0.28rem 0; }
.vf-others button { border: 0; background: none; padding: 0; text-align: left; font: inherit; font-weight: 700; font-size: 0.92rem; cursor: pointer; }
.vf-others li.is-on button { text-decoration: underline; text-decoration-thickness: 3px; text-decoration-color: var(--accent); text-underline-offset: 4px; }
.vf-obar { display: flex; height: 10px; background: var(--paper); }
.vf-obar i { display: block; }
.vf-obar .f { background: var(--c); }
.vf-obar .a { background: color-mix(in srgb, var(--c) 35%, #fff); }
.vf-obar .c { background: #cfd3d8; }
.vf-on { font-size: 0.82rem; color: var(--ink-2); font-variant-numeric: tabular-nums; text-align: right; }

.vf-lists { max-width: 1320px; margin: 72px auto 0; padding: 0 32px; display: grid; grid-template-columns: 1fr 1fr; gap: 56px; }
.vf-list h2 { font-size: 1.6rem; font-weight: 800; font-stretch: 80%; letter-spacing: -0.01em; padding-bottom: 0.6rem; border-bottom: 2px solid var(--ink); }
.vf-list ol { list-style: none; margin-bottom: 1rem; }
.vf-row { display: grid; grid-template-columns: 4.6rem minmax(0, 1fr) 5rem 5rem; gap: 0.9rem; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid var(--rule); text-decoration: none; }
.vf-row:hover .vf-rtitle { text-decoration: underline; text-underline-offset: 3px; }
.vf-rdate { font-size: 0.8rem; color: var(--ink-2); }
.vf-rtitle { font-weight: 600; line-height: 1.3; }
.vf-rscore { font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.vf-bar { display: flex; height: 10px; gap: 2px; }
.vf-bar i { display: block; min-width: 0; }
.b-si { background: var(--ink); }
.b-no { box-shadow: inset 0 0 0 1.5px var(--ink); background: var(--paper); }
.b-abs { background: repeating-linear-gradient(135deg, var(--ink) 0 1.5px, transparent 1.5px 4px); }

.vf-quiz { max-width: 1256px; margin: 72px auto 0; padding: 36px 40px; display: flex; align-items: center; justify-content: space-between; gap: 2rem; background: var(--ink); color: #fff; border-radius: 4px; }
.vf-quiz h2 { font-size: 2.2rem; font-weight: 800; font-stretch: 72%; letter-spacing: -0.02em; margin-bottom: 0.3rem; color: #fff; }
.vf-quiz p { color: #c4cad2; max-width: 56ch; }
.vf-btn { background: #fff; color: var(--ink) !important; font-weight: 700; padding: 0.85rem 1.5rem; border-radius: 4px; text-decoration: none; white-space: nowrap; }
.vf-btn:hover { background: #e8ebee; text-decoration: none; }

.vf-foot { max-width: 1320px; margin: 64px auto 0; padding: 24px 32px 96px; border-top: 1px solid var(--rule); font-size: 0.9rem; color: var(--ink-2); display: flex; justify-content: space-between; gap: 2rem; }
.vf-foot a { text-decoration: underline; text-underline-offset: 3px; margin-left: 1rem; }

@media (max-width: 1080px) {
  .vf-ask-grid { grid-template-columns: 1fr 1fr; }
  .vf-others { grid-column: 1 / -1; max-width: 560px; }
}
@media (max-width: 900px) {
  .vf-top { gap: 1rem; padding: 0 16px; }
  .vf-nav { display: none; }
  .vf-scope { margin-left: auto; }
  .vf-scope select { max-width: 48vw; }
  .vf-brand { font-size: 0.95rem; }
  .vf-hero { grid-template-columns: 1fr; gap: 28px; padding: 24px 16px; }
  .vf-parties li { grid-template-columns: 12px 6rem 1fr; }
  .vf-pnote { grid-column: 3; }
  .vf-picker { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; }
  .vf-picker button { flex: 0 0 72%; scroll-snap-align: start; }
  .vf-ask { padding: 0 16px; margin-top: 48px; }
  .vf-ask-grid { grid-template-columns: 1fr; gap: 32px; }
  .vf-lists { grid-template-columns: 1fr; gap: 36px; padding: 0 16px; margin-top: 48px; }
  .vf-row { grid-template-columns: minmax(0, 1fr) 4rem; }
  .vf-rdate { grid-column: 1 / -1; margin-bottom: -0.6rem; }
  .vf-bar { display: none; }
  .vf-quiz { margin: 48px 16px 0; padding: 24px; flex-direction: column; align-items: flex-start; }
  .vf-foot { flex-direction: column; padding: 24px 16px 96px; }
  .vf-foot a { margin: 0 1rem 0 0; }
}
</style>
