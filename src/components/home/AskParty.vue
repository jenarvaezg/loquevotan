<script setup>
// "¿Votó [partido] a favor de [tema]?": both blanks are selects, and the
// answer comes from the current legislature. The accent is the chosen party's
// colour; the page has none of its own.
import { computed, ref, watch } from 'vue'
import { fmt, formatFecha } from '../../utils'
import {
  questionParties, topicAnswer, positionOf, answerLead, answerDetail, partyName,
} from '../../partyQuestion'

const props = defineProps({
  questions: { type: Object, required: true },
  // Curated topics to open on (the manifest's heroExamples), in order.
  preferredTags: { type: Array, default: () => [] },
})

const parties = computed(() => questionParties(props.questions))
const topics = computed(() => props.questions.topics || [])

const partyLabel = ref('PP')
const tag = ref('')
watch(parties, (list) => {
  if (list.length && !list.some((p) => p.label === partyLabel.value)) {
    partyLabel.value = (list.find((p) => p.label === 'PP') || list[0]).label
  }
}, { immediate: true })
watch(topics, (list) => {
  if (!list.length || list.some((t) => t.tag === tag.value)) return
  const preferred = props.preferredTags.find((t) => list.some((topic) => topic.tag === t))
  tag.value = preferred || list[0].tag
}, { immediate: true })

const party = computed(() => parties.value.find((p) => p.label === partyLabel.value) || null)
const topic = computed(() => topics.value.find((t) => t.tag === tag.value) || null)
const answer = computed(() => topicAnswer(topic.value, party.value))
const rows = computed(() =>
  (topic.value?.recent || []).slice(0, 6).map((r) => {
    const vote = props.questions.votes[r]
    return { vote, pos: positionOf(vote, party.value) }
  })
)
const others = computed(() =>
  parties.value.map((p) => ({ p, ...topicAnswer(topic.value, p) })).filter((o) => o.n > 0)
)
const shortcuts = computed(() => topics.value.filter((t) => t.tag !== tag.value).slice(0, 5))

const POSITION = { 1: 'A favor', 2: 'En contra', 3: 'Abstención' }
</script>

<template>
  <section class="ask" :style="{ '--accent': party?.color || 'var(--color-text)' }" aria-labelledby="ask-title" data-testid="home-ask-party">
    <h2 id="ask-title" class="ask-title">Pregúntale a un partido</h2>
    <p class="ask-question">
      ¿Votó
      <span class="ask-slot">
        <span aria-hidden="true">{{ partyName(partyLabel) }}</span>
        <svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
        <select v-model="partyLabel" aria-label="Partido" data-testid="ask-party-select">
          <option v-for="p in parties" :key="p.label" :value="p.label">{{ partyName(p.label) }}</option>
        </select>
      </span>
      a favor de
      <span class="ask-slot">
        <span aria-hidden="true">{{ fmt(tag) }}</span>
        <svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
        <select v-model="tag" aria-label="Tema">
          <option v-for="t in topics" :key="t.tag" :value="t.tag">{{ fmt(t.tag) }} ({{ t.n }})</option>
        </select>
      </span>?
    </p>
    <p v-if="shortcuts.length" class="ask-shortcuts">
      Otros temas:
      <button v-for="t in shortcuts" :key="t.tag" type="button" @click="tag = t.tag">{{ fmt(t.tag) }}</button>
    </p>

    <div class="ask-grid" aria-live="polite">
      <div class="ask-answer">
        <p class="ask-figure" data-testid="ask-answer"><strong>{{ answer.counts[1] }}</strong> de {{ answer.n }}</p>
        <p class="ask-lead">{{ answerLead(answer) }}</p>
        <p class="ask-detail">{{ answerDetail(answer, tag, partyLabel) }}</p>
      </div>

      <ol class="ask-rows" aria-label="Votaciones de ejemplo">
        <li v-for="r in rows" :key="r.vote.id">
          <router-link :to="'/votacion/' + r.vote.id">
            <span class="ask-date">{{ formatFecha(r.vote.fecha, 'short') }}</span>
            <span class="ask-vote">{{ r.vote.titulo }}</span>
            <span class="ask-pos">
              <i :class="['mark', 'mark--' + (r.pos || 0)]" aria-hidden="true"></i>{{ POSITION[r.pos] || 'Dividido' }}
            </span>
          </router-link>
        </li>
      </ol>

      <ul class="ask-others" aria-label="A favor, partido a partido">
        <li v-for="o in others" :key="o.p.label" :class="{ 'is-on': o.p.label === partyLabel }">
          <button type="button" :aria-pressed="o.p.label === partyLabel" @click="partyLabel = o.p.label">{{ o.p.label }}</button>
          <span class="ask-bar" :style="{ '--c': o.p.color }" aria-hidden="true">
            <i class="f" :style="{ flex: o.counts[1] }"></i>
            <i class="a" :style="{ flex: o.counts[3] }"></i>
            <i class="c" :style="{ flex: o.counts[2] }"></i>
          </span>
          <span class="ask-share">{{ o.counts[1] }}/{{ o.n }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.ask {
  /* Party colours are bright; mixing in the ink keeps large text readable in both themes. */
  --accent-text: color-mix(in oklab, var(--accent) 72%, var(--color-text));
  max-width: var(--container-max);
  margin: 64px auto 0;
  padding: 0 1.25rem;
}
.ask-title { font-size: 1rem; font-weight: 600; font-stretch: 100%; letter-spacing: 0; color: var(--color-muted); margin-bottom: 0.4rem; }
.ask-question {
  font-size: clamp(2rem, 4.6vw, 4.2rem);
  font-weight: 800;
  font-stretch: 72%;
  line-height: 1;
  letter-spacing: -0.02em;
  text-wrap: balance;
}
.ask-slot {
  position: relative;
  display: inline-flex;
  align-items: baseline;
  gap: 0.12em;
  color: var(--accent-text);
  border-bottom: 0.08em solid var(--accent);
  line-height: 1;
  transition: color 0.3s, border-color 0.3s;
}
.ask-slot svg { width: 0.28em; height: 0.18em; fill: currentColor; align-self: center; }
.ask-slot select { position: absolute; inset: 0; width: 100%; opacity: 0; cursor: pointer; font-size: 16px; }
.ask-slot:focus-within { outline: 3px solid var(--color-text); outline-offset: 6px; }

.ask-shortcuts { margin-top: 1.25rem; color: var(--color-muted); display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; align-items: baseline; }
.ask-shortcuts button {
  border: 0;
  background: none;
  padding: 0;
  color: var(--color-text);
  text-decoration: underline;
  text-decoration-color: var(--color-border-hover);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
  cursor: pointer;
}
.ask-shortcuts button:hover { text-decoration-color: var(--accent); }

.ask-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr) minmax(0, 0.9fr);
  gap: 48px;
  margin-top: 32px;
  padding-top: 32px;
  border-top: 2px solid var(--color-text);
}
.ask-figure { font-size: clamp(2.8rem, 5vw, 4.6rem); font-weight: 300; font-stretch: 72%; line-height: 1; letter-spacing: -0.03em; }
.ask-figure strong { font-weight: 800; color: var(--accent-text); }
.ask-lead { font-size: 1.35rem; font-weight: 700; margin: 0.8rem 0 0.4rem; line-height: 1.2; }
.ask-detail { color: var(--color-muted); }

.ask-rows { list-style: none; }
.ask-rows a {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 7rem;
  gap: 0 0.8rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  text-decoration: none;
}
.ask-rows li:first-child a { padding-top: 0; }
.ask-rows a:hover .ask-vote { text-decoration: underline; text-underline-offset: 3px; }
.ask-date { grid-column: 1 / -1; font-size: 0.8rem; color: var(--color-muted); }
.ask-vote { font-weight: 500; line-height: 1.3; }
.ask-pos { display: inline-flex; align-items: center; justify-content: flex-end; gap: 0.4rem; font-weight: 700; font-stretch: 85%; white-space: nowrap; }

/* Same grammar as the hemicycle seats, in the party's colour. */
.mark { width: 11px; height: 11px; border-radius: 50%; border: 2px solid var(--accent); background: var(--color-surface); flex: none; }
.mark--1 { background: var(--accent); }
.mark--3 { background: linear-gradient(90deg, var(--accent) 50%, var(--color-surface) 50%); }
.mark--0 { border-color: var(--color-vacant); }

.ask-others { list-style: none; }
.ask-others li { display: grid; grid-template-columns: 5.2rem minmax(0, 1fr) 2.6rem; gap: 0.7rem; align-items: center; padding: 0.28rem 0; }
.ask-others button { border: 0; background: none; padding: 0; text-align: left; font-weight: 700; font-size: 0.92rem; color: var(--color-text); cursor: pointer; }
.ask-others li.is-on button { text-decoration: underline; text-decoration-thickness: 3px; text-decoration-color: var(--accent); text-underline-offset: 4px; }
.ask-bar { display: flex; height: 10px; background: var(--color-surface); }
.ask-bar i { display: block; }
.ask-bar .f { background: var(--c); }
.ask-bar .a { background: color-mix(in srgb, var(--c) 35%, var(--color-surface)); }
.ask-bar .c { background: var(--color-border); }
.ask-share { font-size: 0.82rem; color: var(--color-muted); font-variant-numeric: tabular-nums; text-align: right; }

@media (max-width: 1080px) {
  .ask-grid { grid-template-columns: 1fr 1fr; }
  .ask-others { grid-column: 1 / -1; max-width: 560px; }
}

@media (max-width: 900px) {
  .ask { padding: 0 16px; margin-top: 48px; }
  .ask-grid { grid-template-columns: 1fr; gap: 32px; }
}
</style>
