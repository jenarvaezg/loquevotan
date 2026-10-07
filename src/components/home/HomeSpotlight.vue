<script setup>
// Featured votes, each drawn as the chamber and read as the question it
// answered: "¿Garantizar educación sexual integral en escuelas? No."
import { computed, ref, watch } from 'vue'
import Hemicycle from '../Hemicycle.vue'
import { getGroupInfo, majorityPosition, formatFecha, voteQuestion, RESULT_ANSWER } from '../../utils'
import { partyRank } from '../../hemicycle'

const props = defineProps({
  votes: { type: Array, required: true },
})

const selectedId = ref(null)
watch(() => props.votes, (list) => {
  if (!list.some((v) => v.id === selectedId.value)) selectedId.value = list[0]?.id ?? null
}, { immediate: true })
const vote = computed(() => props.votes.find((v) => v.id === selectedId.value) || null)

const WORD = { 1: 'a favor', 2: 'en contra' }
function voteWord(code, n) {
  if (code === 3) return n === 1 ? 'abstención' : 'abstenciones'
  return WORD[code]
}

const parties = computed(() => {
  const byLabel = new Map()
  for (const [group, counts] of Object.entries(vote.value?.groups || {})) {
    const { label, color } = getGroupInfo(group)
    const party = byLabel.get(label) || { label, color, counts: { 1: 0, 2: 0, 3: 0, 4: 0 } }
    counts.forEach((n, k) => { party.counts[k + 1] += n })
    byLabel.set(label, party)
  }
  return [...byLabel.values()]
    .map((p) => {
      const position = majorityPosition(p.counts)
      const others = [1, 2, 3]
        .filter((code) => code !== position && p.counts[code])
        .map((code) => `${p.counts[code]} ${voteWord(code, p.counts[code])}`)
      if (p.counts[4]) others.push(`${p.counts[4]} sin votar`)
      return {
        ...p,
        main: position ? `${p.counts[position]} ${voteWord(position, p.counts[position])}` : 'dividido',
        note: others.join(', '),
      }
    })
    .sort((a, b) => partyRank(a.label) - partyRank(b.label))
})

function verdict(v) {
  const abst = v.abstencion ? ` y ${v.abstencion} ${voteWord(3, v.abstencion)}` : ''
  const counts = `${v.favor} a favor, ${v.contra} en contra${abst}.`
  if (v.result === 'Empate') return counts.charAt(0).toUpperCase() + counts.slice(1)
  return `${v.result} por ${v.margin} ${v.margin === 1 ? 'voto' : 'votos'}: ${counts}`
}

const answer = (v) => RESULT_ANSWER[v.result] || v.result
</script>

<template>
  <section v-if="vote" class="spotlight" aria-labelledby="spotlight-question" data-testid="home-spotlight">
    <div class="spotlight-main">
      <Hemicycle :groups="vote.groups" :totals="vote" :label="`Hemiciclo de la votación. ${verdict(vote)}`">
        <p class="spotlight-score" aria-hidden="true">{{ vote.favor }}<span>–</span>{{ vote.contra }}</p>
      </Hemicycle>

      <div class="spotlight-story">
        <p class="spotlight-date">Votado el {{ formatFecha(vote.fecha) }}</p>
        <h2 id="spotlight-question">{{ voteQuestion(vote.titulo) }}</h2>
        <p class="spotlight-answer"><strong>{{ answer(vote) }}.</strong> {{ verdict(vote) }}</p>
        <p v-if="vote.resumen" class="spotlight-resumen">{{ vote.resumen }}</p>
        <ul v-if="parties.length" class="spotlight-parties" aria-label="Voto de cada grupo">
          <li v-for="p in parties" :key="p.label">
            <span class="party-dot" :style="{ background: p.color }"></span>
            <span class="party-name">{{ p.label }}</span>
            <span class="party-main">{{ p.main }}</span>
            <span class="party-note">{{ p.note }}</span>
          </li>
        </ul>
        <router-link :to="'/votacion/' + vote.id" class="spotlight-more">Ver cómo votó cada diputado</router-link>
      </div>
    </div>

    <nav v-if="votes.length > 1" class="spotlight-picker" aria-label="Otras votaciones destacadas" data-testid="home-featured-votes">
      <button
        v-for="v in votes"
        :key="v.id"
        type="button"
        :class="{ 'is-on': v.id === selectedId }"
        :aria-pressed="v.id === selectedId"
        @click="selectedId = v.id"
      >
        <span class="picker-question">{{ voteQuestion(v.titulo) }}</span>
        <span class="picker-answer">{{ answer(v) }}. {{ v.favor }}–{{ v.contra }}</span>
      </button>
    </nav>
  </section>
</template>

<style scoped>
.spotlight { background: var(--color-surface); border-bottom: 1px solid var(--color-border); }

.spotlight-main {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 56px;
  align-items: start;
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 48px 1.25rem 40px;
}

.spotlight-score {
  font-size: clamp(1.7rem, 3.6vw, 3rem);
  font-weight: 800;
  font-stretch: 80%;
  letter-spacing: -0.02em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.spotlight-score span { color: var(--color-vacant); padding: 0 0.06em; }

.spotlight-story { max-width: 36rem; }
.spotlight-date { color: var(--color-muted); margin-bottom: 0.5rem; }
.spotlight-story h2 {
  font-size: clamp(2.2rem, 4vw, 3.6rem);
  font-stretch: 72%;
  line-height: 0.98;
  margin-bottom: 1rem;
}
.spotlight-answer { font-size: 1.15rem; margin-bottom: 0.8rem; }
.spotlight-answer strong {
  font-size: 2.6rem;
  font-weight: 800;
  font-stretch: 72%;
  line-height: 1;
  margin-right: 0.3rem;
  vertical-align: -0.12em;
}
.spotlight-resumen { color: var(--color-muted); margin-bottom: 1.5rem; max-width: 60ch; }

.spotlight-parties { list-style: none; border-top: 1px solid var(--color-text); margin-bottom: 1.25rem; }
.spotlight-parties li {
  display: grid;
  grid-template-columns: 12px 7rem 8.5rem 1fr;
  align-items: baseline;
  gap: 0.6rem;
  padding: 0.42rem 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.95rem;
}
.party-dot { width: 12px; height: 12px; border-radius: 50%; align-self: center; }
.party-name { font-weight: 700; }
.party-main { font-variant-numeric: tabular-nums; }
.party-note { color: var(--color-muted); font-size: 0.85rem; }

.spotlight-more {
  display: inline-block;
  color: var(--color-text);
  font-weight: 600;
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 5px;
}
.spotlight-more:hover { color: var(--color-text); text-decoration-color: var(--color-muted); }

.spotlight-picker {
  display: grid;
  grid-auto-columns: minmax(0, 1fr);
  grid-auto-flow: column;
  max-width: var(--container-max);
  margin: 0 auto;
  border-top: 1px solid var(--color-border);
}
.spotlight-picker button {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  text-align: left;
  border: 0;
  border-top: 3px solid transparent;
  margin-top: -1px;
  background: none;
  padding: 1rem 1.25rem 1.4rem;
  color: var(--color-muted);
  cursor: pointer;
}
.spotlight-picker button + button { border-left: 1px solid var(--color-border); }
.spotlight-picker button:hover { color: var(--color-text); }
.spotlight-picker button.is-on { border-top-color: var(--color-text); color: var(--color-text); }
.spotlight-picker button:focus-visible { outline-offset: -2px; }
.picker-question { font-weight: 700; font-stretch: 85%; font-size: 1.02rem; line-height: 1.2; }
.picker-answer { font-size: 0.85rem; font-variant-numeric: tabular-nums; }

@media (max-width: 900px) {
  .spotlight-main { grid-template-columns: 1fr; gap: 28px; padding: 24px 16px; }
  .spotlight-parties li { grid-template-columns: 12px 6rem 1fr; }
  .party-note { grid-column: 3; }
  .spotlight-picker { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; }
  .spotlight-picker button { flex: 0 0 72%; scroll-snap-align: start; }
}
</style>
