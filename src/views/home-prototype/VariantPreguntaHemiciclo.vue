<script setup>
// PROTOTYPE — Variante E «Pregunta → hemiciclo». Manda la frase de B; la
// respuesta se dibuja en el hemiciclo de A con el partido elegido en color y el
// resto en gris. Tocar un escaño cambia la pregunta a ese partido.
import { computed, ref, watch } from 'vue'
import { fmt } from '../../utils'
import { usePrototypeData, loadFonts, shortDate, longDate, VOTE_WORD } from './usePrototype'
import { useTopicQuestion, named } from './useTopicQuestion'
import ProtoHemicycle from './ProtoHemicycle.vue'

const props = defineProps({ manifest: Object })
loadFonts('https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&display=swap')

const data = usePrototypeData()
const { ambitos, currentScopeId, setScope, votaciones, votResults, votosReady, legParties, partyPosition } = data
const { partyKey, topic, party, accent, topicVotes, answer, lead, detail, others, shortcuts } = useTopicQuestion(data)

const selected = ref(null)
watch(topicVotes, (list) => {
  // Prefer a contested vote: a unanimous chamber says little about the party.
  if (!list.includes(selected.value)) selected.value = list.find((i) => votResults.value[i].contra >= 15) ?? list[0] ?? null
}, { immediate: true })

const selVote = computed(() => (selected.value == null ? null : votaciones.value[selected.value]))
const selResult = computed(() => (selected.value == null ? null : votResults.value[selected.value]))
const selBallots = computed(() => (votosReady.value && selected.value != null ? data.ballots(selected.value) : []))
const selPos = computed(() => (party.value && selected.value != null ? partyPosition(selected.value, party.value) : null))
const rows = computed(() =>
  party.value ? topicVotes.value.slice(0, 12).map((i) => ({ i, v: votaciones.value[i], pos: partyPosition(i, party.value) })) : []
)

const POS_PHRASE = { 1: 'votó a favor', 2: 'votó en contra', 3: 'se abstuvo' }
const caption = computed(() => {
  const who = named(partyKey.value)
  const text = `${who} ${POS_PHRASE[selPos.value] || 'votó dividido'}`
  return text.charAt(0).toUpperCase() + text.slice(1)
})

function pickParty(label) {
  if (legParties.value.some((p) => p.label === label)) partyKey.value = label
}
</script>

<template>
  <div class="ve" :style="{ '--accent': accent }">
    <header class="ve-top">
      <router-link to="/" class="ve-brand">Lo Que Votan</router-link>
      <nav class="ve-nav" aria-label="Secciones">
        <router-link to="/votaciones">Votaciones</router-link>
        <router-link to="/diputados">Diputados</router-link>
        <router-link to="/grupos">Partidos</router-link>
        <router-link to="/quiz">Test</router-link>
      </nav>
      <label class="ve-scope">
        <span class="ve-sr">Parlamento</span>
        <select :value="currentScopeId" @change="setScope($event.target.value)">
          <option v-for="a in ambitos" :key="a.id" :value="a.id">{{ a.nombre }}</option>
        </select>
      </label>
    </header>

    <section class="ve-hero">
      <h1 class="ve-q">
        ¿Votó
        <span class="ve-slot">
          <span aria-hidden="true">{{ named(partyKey) }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="partyKey" aria-label="Partido">
            <option v-for="p in legParties" :key="p.label" :value="p.label">{{ named(p.label) }}</option>
          </select>
        </span>
        a favor de
        <span class="ve-slot">
          <span aria-hidden="true">{{ fmt(topic) }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="topic" aria-label="Tema">
            <option v-for="[t, n] in data.legTopics.value" :key="t" :value="t">{{ fmt(t) }} ({{ n }})</option>
          </select>
        </span>?
      </h1>
      <p class="ve-try" v-if="shortcuts.length">
        Prueba con
        <button v-for="t in shortcuts" :key="t" type="button" @click="topic = t">{{ fmt(t) }}</button>
      </p>
    </section>

    <section class="ve-answer" aria-live="polite">
      <template v-if="votosReady && answer && selVote">
        <div class="ve-chamber">
          <ProtoHemicycle
            :ballots="selBallots"
            :focus="partyKey"
            pickable
            :label="`Hemiciclo de la votación: ${selVote.titulo_ciudadano}`"
            @pick="pickParty"
          >
            <p class="ve-score">{{ selResult.favor }}<span>–</span>{{ selResult.contra }}</p>
            <p class="ve-res">{{ selResult.result }}</p>
          </ProtoHemicycle>
          <div class="ve-caption">
            <p class="ve-cdate">{{ longDate(selVote.fecha) }}</p>
            <h2><router-link :to="'/votacion/' + selVote.id">{{ selVote.titulo_ciudadano }}</router-link></h2>
            <p class="ve-cpos"><strong>{{ caption }}.</strong> Toca un escaño para preguntar por otro partido.</p>
          </div>
        </div>

        <div class="ve-side">
          <p class="ve-big"><strong>{{ answer.counts[1] }}</strong> de {{ answer.n }}</p>
          <p class="ve-lead">{{ lead }}</p>
          <p class="ve-detail">{{ detail }}</p>
          <ol class="ve-rows">
            <li v-for="r in rows" :key="r.i">
              <button type="button" :class="{ 'is-on': r.i === selected }" :aria-pressed="r.i === selected" @click="selected = r.i">
                <span class="ve-rdate">{{ shortDate(r.v.fecha) }}</span>
                <span class="ve-rtitle">{{ r.v.titulo_ciudadano }}</span>
                <span class="ve-rpos" :class="'is-' + (r.pos || 0)">{{ r.pos ? VOTE_WORD[r.pos] : 'Dividido' }}</span>
              </button>
            </li>
          </ol>
        </div>
      </template>
      <p v-else-if="votosReady && answer" class="ve-wait">No hay votaciones sobre este tema en esta legislatura.</p>
      <p v-else class="ve-wait">Cargando las votaciones de esta legislatura…</p>
    </section>

    <section class="ve-others" v-if="votosReady && others.length">
      <h2>Los demás partidos, sobre {{ fmt(topic) }}</h2>
      <ul>
        <li v-for="o in others" :key="o.p.label" :class="{ 'is-on': o.p.label === partyKey }">
          <button type="button" @click="partyKey = o.p.label">{{ o.p.label }}</button>
          <span class="ve-obar" :style="{ '--c': o.p.color }">
            <i class="f" :style="{ flex: o.counts[1] }"></i>
            <i class="a" :style="{ flex: o.counts[3] }"></i>
            <i class="c" :style="{ flex: o.counts[2] }"></i>
          </span>
          <span class="ve-on">{{ o.counts[1] }} de {{ o.n }} a favor</span>
        </li>
      </ul>
    </section>

    <section class="ve-quiz">
      <p>¿Y tú, qué habrías votado?</p>
      <p class="ve-quiz-sub">Responde a ciegas a propuestas reales del pleno y descubre con qué partido coincides más.</p>
      <router-link to="/quiz" class="ve-btn">Hacer el test</router-link>
    </section>

    <footer class="ve-foot">
      <p>Lo Que Votan reúne {{ props.manifest?.stats?.votaciones?.toLocaleString('es-ES') }} votaciones oficiales del Congreso y los parlamentos autonómicos. Los temas se asignan con IA y se pueden revisar en la <router-link to="/metodologia">metodología</router-link>.</p>
      <a href="https://github.com/jenarvaezg/loquevotan" target="_blank" rel="noopener">GitHub</a>
    </footer>
  </div>
</template>

<style scoped>
.ve {
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
.ve a, .ve a:hover { color: inherit; }
.ve h1, .ve h2 { font-family: inherit; color: inherit; }
.ve-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.ve-top { display: flex; align-items: center; gap: 2rem; padding: 20px 40px; }
.ve-brand { font-weight: 800; font-stretch: 125%; font-size: 1rem; text-decoration: none; margin-right: auto; white-space: nowrap; }
.ve-nav { display: flex; gap: 1.5rem; }
.ve-nav a { text-decoration: none; font-weight: 500; }
.ve-nav a:hover { text-decoration: underline; text-decoration-color: var(--accent); text-decoration-thickness: 2px; text-underline-offset: 5px; }
.ve-scope select { appearance: none; border: 0; border-bottom: 1px solid var(--ink); background: transparent; font: inherit; font-size: 0.9rem; padding: 2px 0; color: var(--ink); cursor: pointer; }

.ve-hero { padding: 6vh 40px 40px; max-width: 1400px; }
.ve-q { font-size: clamp(2.4rem, 6.4vw, 6rem); font-weight: 800; font-stretch: 72%; line-height: 0.98; letter-spacing: -0.025em; text-wrap: balance; }
.ve-slot {
  position: relative;
  display: inline-flex;
  align-items: baseline;
  gap: 0.12em;
  color: var(--accent);
  border-bottom: 0.08em solid var(--accent);
  line-height: 1;
  transition: color 0.3s, border-color 0.3s;
}
.ve-slot svg { width: 0.28em; height: 0.18em; fill: currentColor; align-self: center; }
.ve-slot select { position: absolute; inset: 0; width: 100%; opacity: 0; cursor: pointer; font-size: 16px; }
.ve-slot:focus-within { outline: 3px solid var(--ink); outline-offset: 6px; }
.ve-try { margin-top: 1.75rem; color: var(--ink-2); display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; align-items: baseline; }
.ve-try button { border: 0; background: none; padding: 0; font: inherit; color: var(--ink); text-decoration: underline; text-decoration-color: var(--rule); text-decoration-thickness: 2px; text-underline-offset: 4px; cursor: pointer; }
.ve-try button:hover { text-decoration-color: var(--accent); }

.ve-answer {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
  gap: 64px;
  margin: 0 40px;
  padding: 48px 0 64px;
  border-top: 1px solid var(--ink);
}
.ve-score { font-size: clamp(1.6rem, 3.2vw, 2.8rem); font-weight: 800; font-stretch: 80%; line-height: 1; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.ve-score span { color: #c3c9d1; padding: 0 0.06em; }
.ve-res { font-weight: 600; color: var(--ink-2); margin-top: 0.2rem; }
.ve-caption { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--rule); }
.ve-cdate { font-size: 0.9rem; color: var(--ink-2); }
.ve-caption h2 { font-size: 1.5rem; font-weight: 700; font-stretch: 85%; line-height: 1.15; margin: 0.15rem 0 0.5rem; }
.ve-caption h2 a { text-decoration: none; }
.ve-caption h2 a:hover { text-decoration: underline; text-underline-offset: 4px; }
.ve-cpos { color: var(--ink-2); }
.ve-cpos strong { color: var(--ink); box-shadow: inset 0 -0.35em 0 color-mix(in srgb, var(--accent) 28%, transparent); }

.ve-big { font-size: clamp(3rem, 5.6vw, 5.2rem); font-weight: 300; font-stretch: 72%; line-height: 1; letter-spacing: -0.03em; }
.ve-big strong { font-weight: 800; color: var(--accent); }
.ve-lead { font-size: 1.5rem; font-weight: 700; margin: 0.9rem 0 0.4rem; line-height: 1.2; }
.ve-detail { color: var(--ink-2); max-width: 44ch; margin-bottom: 1.75rem; }
.ve-rows { list-style: none; border-top: 1px solid var(--ink); }
.ve-rows button {
  display: grid;
  grid-template-columns: 5.4rem minmax(0, 1fr) 6.2rem;
  gap: 0.8rem;
  align-items: baseline;
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
.ve-rows button:hover { background: var(--soft); }
.ve-rows button.is-on { background: var(--soft); box-shadow: inset 4px 0 0 var(--accent); }
.ve-rows button:focus-visible { outline: 2px solid var(--ink); outline-offset: -2px; }
.ve-rdate { font-size: 0.82rem; color: var(--ink-2); }
.ve-rtitle { font-weight: 500; line-height: 1.3; font-size: 0.95rem; }
.ve-rpos { font-weight: 700; text-align: right; font-stretch: 85%; font-size: 0.95rem; }
.ve-rpos.is-1 { color: var(--accent); }
.ve-rpos.is-0, .ve-rpos.is-3 { color: var(--ink-2); }
.ve-wait { color: var(--ink-2); grid-column: 1 / -1; }

.ve-others { background: var(--soft); padding: 56px 40px; }
.ve-others h2 { font-size: 2rem; font-weight: 800; font-stretch: 80%; letter-spacing: -0.02em; margin-bottom: 1.5rem; }
.ve-others ul { list-style: none; max-width: 900px; }
.ve-others li { display: grid; grid-template-columns: 8rem minmax(0, 1fr) 9rem; gap: 1.25rem; align-items: center; padding: 0.35rem 0; }
.ve-others button { border: 0; background: none; padding: 0; text-align: left; font: inherit; font-weight: 700; cursor: pointer; }
.ve-others li.is-on button { text-decoration: underline; text-decoration-thickness: 3px; text-decoration-color: var(--accent); text-underline-offset: 5px; }
.ve-obar { display: flex; height: 14px; background: #fff; }
.ve-obar i { display: block; }
.ve-obar .f { background: var(--c); }
.ve-obar .a { background: color-mix(in srgb, var(--c) 35%, #fff); }
.ve-obar .c { background: #cfcfcf; }
.ve-on { font-size: 0.9rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }

.ve-quiz { padding: 72px 40px; background: var(--ink); color: #fff; }
.ve-quiz p:first-child { font-size: clamp(2.2rem, 5vw, 4.5rem); font-weight: 800; font-stretch: 72%; line-height: 1; letter-spacing: -0.02em; }
.ve-quiz-sub { margin: 1rem 0 2rem; max-width: 44ch; color: #cfcfcf; }
.ve-btn { display: inline-block; background: #fff; color: #000 !important; font-weight: 700; padding: 0.9rem 1.6rem; text-decoration: none; }
.ve-btn:hover { background: #e6e6e6; text-decoration: none; }

.ve-foot { display: flex; justify-content: space-between; gap: 2rem; padding: 28px 40px 96px; font-size: 0.9rem; color: var(--ink-2); }
.ve-foot p { max-width: 70ch; }
.ve-foot a { text-decoration: underline; text-underline-offset: 3px; }

@media (max-width: 900px) {
  .ve-top { padding: 16px; gap: 1rem; flex-wrap: wrap; }
  .ve-nav { order: 3; width: 100%; gap: 1.1rem; font-size: 0.95rem; }
  .ve-scope select { max-width: 48vw; }
  .ve-hero { padding: 32px 16px; }
  .ve-answer { grid-template-columns: 1fr; gap: 36px; margin: 0 16px; padding: 28px 0 48px; }
  .ve-rows button { grid-template-columns: minmax(0, 1fr) auto; }
  .ve-rdate { grid-column: 1 / -1; margin-bottom: -0.5rem; }
  .ve-others { padding: 40px 16px; }
  .ve-others li { grid-template-columns: 5.5rem minmax(0, 1fr); }
  .ve-on { grid-column: 2; margin-top: -0.4rem; }
  .ve-quiz { padding: 48px 16px; }
  .ve-foot { flex-direction: column; padding: 24px 16px 96px; }
}
</style>
