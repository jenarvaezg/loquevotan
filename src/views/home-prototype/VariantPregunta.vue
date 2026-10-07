<script setup>
// PROTOTYPE — Variante B «La pregunta». La portada es una frase editable que se
// responde con datos: «¿Votó [el PP] a favor de [subir pensiones]?». El color de
// acento es siempre el del partido elegido; la web no tiene color propio.
import { computed, ref, watch } from 'vue'
import { fmt } from '../../utils'
import { usePrototypeData, loadFonts, shortDate, VOTE_WORD } from './usePrototype'

const props = defineProps({ manifest: Object })
loadFonts('https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&display=swap')

const data = usePrototypeData()
const {
  ambitos, currentScopeId, setScope, votaciones, votosReady, legParties, legTopics, legVotIdx, partyPosition,
} = data

const ARTICLE = { PP: 'el PP', PSOE: 'el PSOE', PNV: 'el PNV', 'PSC-PSOE': 'el PSC', VOX: 'Vox', CS: 'Ciudadanos' }
const named = (label) => ARTICLE[label] || label

const partyKey = ref('PP')
const topic = ref('subir_pensiones')
watch(legParties, (list) => {
  if (list.length && !list.some((p) => p.label === partyKey.value)) {
    partyKey.value = (list.find((p) => p.label === 'PP') || list[0]).label
  }
}, { immediate: true })
watch(legTopics, (list) => {
  if (list.length && !list.some(([t]) => t === topic.value)) topic.value = list[0][0]
}, { immediate: true })

const party = computed(() => legParties.value.find((p) => p.label === partyKey.value) || null)
const accent = computed(() => party.value?.color || '#000')
const topicVotes = computed(() =>
  legVotIdx.value.filter((i) => (votaciones.value[i].etiquetas || []).includes(topic.value))
)

function tallyFor(p) {
  const counts = { 1: 0, 2: 0, 3: 0 }
  let n = 0
  for (const i of topicVotes.value) {
    const pos = partyPosition(i, p)
    if (pos >= 1 && pos <= 3) { counts[pos]++; n++ }
  }
  return { counts, n }
}

const answer = computed(() => (party.value ? tallyFor(party.value) : null))
const lead = computed(() => {
  const a = answer.value
  if (!a?.n) return 'No hay votaciones suficientes sobre este tema.'
  const f = a.counts[1] / a.n
  if (f >= 0.85) return 'Sí, casi siempre.'
  if (f >= 0.6) return 'La mayoría de las veces.'
  if (f > 0.4) return 'Depende de la votación.'
  if (f > 0.15) return 'Pocas veces.'
  return 'No, casi nunca.'
})
const detail = computed(() => {
  const a = answer.value
  if (!a?.n) return ''
  const times = (k) => `${k} ${k === 1 ? 'vez' : 'veces'}`
  const parts = [
    a.counts[1] && `votó a favor ${times(a.counts[1])}`,
    a.counts[2] && `${a.counts[1] ? "" : "votó "}en contra ${times(a.counts[2])}`,
    a.counts[3] && `se abstuvo ${times(a.counts[3])}`,
  ].filter(Boolean)
  const list = parts.length > 1 ? `${parts.slice(0, -1).join(', ')} y ${parts.at(-1)}` : parts[0]
  return `En ${a.n} votaciones de esta legislatura sobre ${fmt(topic.value)}, ${named(partyKey.value)} ${list}.`
})
const rows = computed(() => {
  if (!party.value) return []
  return topicVotes.value.slice(0, 12).map((i) => ({ i, v: votaciones.value[i], pos: partyPosition(i, party.value) }))
})
const others = computed(() =>
  legParties.value.map((p) => ({ p, ...tallyFor(p) })).filter((o) => o.n > 0)
)
const shortcuts = computed(() => legTopics.value.slice(0, 7).map(([t]) => t).filter((t) => t !== topic.value).slice(0, 6))
</script>

<template>
  <div class="vb" :style="{ '--accent': accent }">
    <header class="vb-top">
      <router-link to="/" class="vb-brand">Lo Que Votan</router-link>
      <nav class="vb-nav" aria-label="Secciones">
        <router-link to="/votaciones">Votaciones</router-link>
        <router-link to="/diputados">Diputados</router-link>
        <router-link to="/grupos">Partidos</router-link>
        <router-link to="/quiz">Test</router-link>
      </nav>
      <label class="vb-scope">
        <span class="vb-sr">Parlamento</span>
        <select :value="currentScopeId" @change="setScope($event.target.value)">
          <option v-for="a in ambitos" :key="a.id" :value="a.id">{{ a.nombre }}</option>
        </select>
      </label>
    </header>

    <section class="vb-hero">
      <h1 class="vb-q">
        ¿Votó
        <span class="vb-slot">
          <span aria-hidden="true">{{ named(partyKey) }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="partyKey" aria-label="Partido">
            <option v-for="p in legParties" :key="p.label" :value="p.label">{{ named(p.label) }}</option>
          </select>
        </span>
        a favor de
        <span class="vb-slot">
          <span aria-hidden="true">{{ fmt(topic) }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="topic" aria-label="Tema">
            <option v-for="[t, n] in legTopics" :key="t" :value="t">{{ fmt(t) }} ({{ n }})</option>
          </select>
        </span>?
      </h1>
      <p class="vb-try" v-if="shortcuts.length">
        Prueba con
        <button v-for="t in shortcuts" :key="t" type="button" @click="topic = t">{{ fmt(t) }}</button>
      </p>
    </section>

    <section class="vb-answer" aria-live="polite">
      <template v-if="votosReady && answer">
        <div class="vb-figure">
          <p class="vb-big"><strong>{{ answer.counts[1] }}</strong> de {{ answer.n }}</p>
          <p class="vb-lead">{{ lead }}</p>
          <p class="vb-detail">{{ detail }}</p>
        </div>
        <ol class="vb-rows">
          <li v-for="r in rows" :key="r.i">
            <router-link :to="'/votacion/' + r.v.id">
              <span class="vb-rdate">{{ shortDate(r.v.fecha) }}</span>
              <span class="vb-rtitle">{{ r.v.titulo_ciudadano }}</span>
              <span class="vb-rpos" :class="'is-' + (r.pos || 0)">{{ r.pos ? VOTE_WORD[r.pos] : 'Dividido' }}</span>
            </router-link>
          </li>
        </ol>
      </template>
      <p v-else class="vb-wait">Cargando las votaciones de esta legislatura…</p>
    </section>

    <section class="vb-others" v-if="votosReady && others.length">
      <h2>Los demás partidos, sobre {{ fmt(topic) }}</h2>
      <ul>
        <li v-for="o in others" :key="o.p.label" :class="{ 'is-on': o.p.label === partyKey }">
          <button type="button" @click="partyKey = o.p.label">{{ o.p.label }}</button>
          <span class="vb-obar" :style="{ '--c': o.p.color }">
            <i class="f" :style="{ flex: o.counts[1] }"></i>
            <i class="a" :style="{ flex: o.counts[3] }"></i>
            <i class="c" :style="{ flex: o.counts[2] }"></i>
          </span>
          <span class="vb-on">{{ o.counts[1] }} de {{ o.n }} a favor</span>
        </li>
      </ul>
      <p class="vb-key">Barra: a favor en color sólido, abstención en tono claro, en contra en gris.</p>
    </section>

    <section class="vb-quiz">
      <p>¿Y tú, qué habrías votado?</p>
      <p class="vb-quiz-sub">Responde a ciegas a propuestas reales del pleno y descubre con qué partido coincides más.</p>
      <router-link to="/quiz" class="vb-btn">Hacer el test</router-link>
    </section>

    <footer class="vb-foot">
      <p>Lo Que Votan reúne {{ manifest?.stats?.votaciones?.toLocaleString('es-ES') }} votaciones oficiales del Congreso y los parlamentos autonómicos. Los temas se asignan con IA y se pueden revisar en la <router-link to="/metodologia">metodología</router-link>.</p>
      <a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">GitHub</a>
    </footer>
  </div>
</template>

<style scoped>
.vb {
  --ink: #000;
  --ink-2: #5a5a5a;
  --rule: #e3e3e3;
  --soft: #f4f4f4;
  min-height: 100vh;
  background: #fff;
  color: var(--ink);
  font-family: 'Archivo', system-ui, sans-serif;
  font-size: 17px;
  line-height: 1.5;
}
.vb a, .vb a:hover { color: inherit; }
.vb h1, .vb h2 { font-family: inherit; color: inherit; }
.vb-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.vb-top {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 20px 40px;
}
.vb-brand {
  font-weight: 800;
  font-stretch: 125%;
  font-size: 1rem;
  letter-spacing: -0.01em;
  text-decoration: none;
  margin-right: auto;
}
.vb-nav { display: flex; gap: 1.5rem; }
.vb-nav a { text-decoration: none; font-weight: 500; }
.vb-nav a:hover { text-decoration: underline; text-decoration-color: var(--accent); text-decoration-thickness: 2px; text-underline-offset: 5px; }
.vb-scope select {
  appearance: none;
  border: 0;
  border-bottom: 1px solid var(--ink);
  background: transparent;
  font: inherit;
  font-size: 0.9rem;
  padding: 2px 0;
  color: var(--ink);
  cursor: pointer;
}

.vb-hero { padding: 7vh 40px 48px; max-width: 1400px; }
.vb-q {
  font-size: clamp(2.6rem, 7.4vw, 7rem);
  font-weight: 800;
  font-stretch: 72%;
  line-height: 0.98;
  letter-spacing: -0.025em;
  text-wrap: balance;
}
.vb-slot {
  position: relative;
  display: inline-flex;
  align-items: baseline;
  gap: 0.12em;
  color: var(--accent);
  border-bottom: 0.08em solid var(--accent);
  line-height: 1;
  transition: color 0.3s, border-color 0.3s;
}
.vb-slot svg { width: 0.28em; height: 0.18em; fill: currentColor; align-self: center; }
.vb-slot select {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  cursor: pointer;
  font-size: 16px;
}
.vb-slot:focus-within { outline: 3px solid var(--ink); outline-offset: 6px; }
.vb-try { margin-top: 2rem; color: var(--ink-2); display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; align-items: baseline; }
.vb-try button {
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--rule);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
  cursor: pointer;
}
.vb-try button:hover { text-decoration-color: var(--accent); }

.vb-answer {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  gap: 64px;
  padding: 48px 40px 64px;
  border-top: 1px solid var(--ink);
  margin: 0 40px;
  padding-left: 0;
  padding-right: 0;
}
.vb-big { font-size: clamp(3rem, 6vw, 5.5rem); font-weight: 300; font-stretch: 72%; line-height: 1; letter-spacing: -0.03em; }
.vb-big strong { font-weight: 800; color: var(--accent); }
.vb-lead { font-size: 1.6rem; font-weight: 700; margin: 1rem 0 0.5rem; line-height: 1.2; }
.vb-detail { color: var(--ink-2); max-width: 40ch; }
.vb-rows { list-style: none; }
.vb-rows a {
  display: grid;
  grid-template-columns: 6rem minmax(0, 1fr) 7rem;
  gap: 1rem;
  align-items: baseline;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--rule);
  text-decoration: none;
}
.vb-rows li:first-child a { padding-top: 0; }
.vb-rows a:hover .vb-rtitle { text-decoration: underline; text-underline-offset: 3px; }
.vb-rdate { font-size: 0.85rem; color: var(--ink-2); }
.vb-rtitle { font-weight: 500; line-height: 1.3; }
.vb-rpos { font-weight: 700; text-align: right; font-stretch: 85%; }
.vb-rpos.is-1 { color: var(--accent); }
.vb-rpos.is-0, .vb-rpos.is-3 { color: var(--ink-2); }
.vb-wait { color: var(--ink-2); grid-column: 1 / -1; }

.vb-others { background: var(--soft); padding: 56px 40px; }
.vb-others h2 { font-size: 2rem; font-weight: 800; font-stretch: 80%; letter-spacing: -0.02em; margin-bottom: 1.5rem; }
.vb-others ul { list-style: none; max-width: 900px; }
.vb-others li {
  display: grid;
  grid-template-columns: 8rem minmax(0, 1fr) 9rem;
  gap: 1.25rem;
  align-items: center;
  padding: 0.35rem 0;
}
.vb-others button {
  border: 0;
  background: none;
  padding: 0;
  text-align: left;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
.vb-others li.is-on button { text-decoration: underline; text-decoration-thickness: 3px; text-decoration-color: var(--accent); text-underline-offset: 5px; }
.vb-obar { display: flex; height: 14px; background: #fff; }
.vb-obar i { display: block; }
.vb-obar .f { background: var(--c); }
.vb-obar .a { background: color-mix(in srgb, var(--c) 35%, #fff); }
.vb-obar .c { background: #cfcfcf; }
.vb-on { font-size: 0.9rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.vb-key { margin-top: 1.25rem; font-size: 0.85rem; color: var(--ink-2); }

.vb-quiz { padding: 72px 40px; background: var(--ink); color: #fff; }
.vb-quiz p:first-child { font-size: clamp(2.2rem, 5vw, 4.5rem); font-weight: 800; font-stretch: 72%; line-height: 1; letter-spacing: -0.02em; }
.vb-quiz-sub { margin: 1rem 0 2rem; max-width: 44ch; color: #cfcfcf; }
.vb-btn {
  display: inline-block;
  background: #fff;
  color: #000 !important;
  font-weight: 700;
  padding: 0.9rem 1.6rem;
  text-decoration: none;
}
.vb-btn:hover { background: #e6e6e6; text-decoration: none; }

.vb-foot {
  display: flex;
  justify-content: space-between;
  gap: 2rem;
  padding: 28px 40px 96px;
  font-size: 0.9rem;
  color: var(--ink-2);
}
.vb-foot p { max-width: 70ch; }
.vb-foot a { text-decoration: underline; text-underline-offset: 3px; }

@media (max-width: 860px) {
  .vb-top { padding: 16px; gap: 1rem; flex-wrap: wrap; }
  .vb-nav { order: 3; width: 100%; gap: 1.1rem; font-size: 0.95rem; }
  .vb-scope select { max-width: 48vw; }
  .vb-hero { padding: 32px 16px 32px; }
  .vb-answer { grid-template-columns: 1fr; gap: 32px; margin: 0 16px; padding: 32px 0 48px; }
  .vb-rows a { grid-template-columns: minmax(0, 1fr) auto; }
  .vb-rdate { grid-column: 1 / -1; margin-bottom: -0.6rem; }
  .vb-others { padding: 40px 16px; }
  .vb-others li { grid-template-columns: 5.5rem minmax(0, 1fr); }
  .vb-on { grid-column: 2; margin-top: -0.4rem; }
  .vb-quiz { padding: 48px 16px; }
  .vb-foot { flex-direction: column; padding: 24px 16px 96px; }
}
</style>
