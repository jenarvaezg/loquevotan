<script setup>
// PROTOTYPE — Variante D «La orla». La portada empieza por las personas: eliges
// tu provincia, ves a tus diputados como en una orla y debajo una matriz con lo
// que votó cada uno en las últimas votaciones disputadas.
import { computed, ref, watch } from 'vue'
import { dipPhotoUrl, avatarInitials } from '../../utils'
import { usePrototypeData, loadFonts, shortDate, displayName, partyRank, VOTE_WORD } from './usePrototype'

defineProps({ manifest: Object })
loadFonts('https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,300..800;1,7..72,300..700&family=Atkinson+Hyperlegible+Next:wght@300..700&display=swap')

const data = usePrototypeData()
const {
  ambitos, currentScopeId, setScope, diputados, dipFotos, dipProvincias, votaciones, votResults,
  votosReady, latestLeg, legVotIdx, currentDips,
} = data

function provinceOf(dip) {
  const p = dipProvincias.value[dip]
  if (!p) return ''
  if (typeof p === 'string') return p
  return p[latestLeg.value] || ''
}

// Party of each seated deputy, taken from their latest ballot.
const dipParty = computed(() => {
  const map = new Map()
  for (const v of legVotIdx.value.slice(0, 6)) {
    for (const b of data.ballots(v)) if (!map.has(b.dip)) map.set(b.dip, { label: b.label, color: b.color })
  }
  return map
})

const provinces = computed(() => {
  const counts = new Map()
  for (const dip of currentDips.value) {
    const p = provinceOf(dip)
    if (p) counts.set(p, (counts.get(p) || 0) + 1)
  }
  return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es'))
})
const province = ref('Madrid')
watch(provinces, (list) => {
  if (list.length && !list.some(([p]) => p === province.value)) {
    province.value = [...list].sort((a, b) => b[1] - a[1])[0][0]
  }
}, { immediate: true })

const members = computed(() =>
  currentDips.value
    .filter((dip) => provinceOf(dip) === province.value)
    .map((dip) => ({
      dip,
      raw: diputados.value[dip],
      name: displayName(diputados.value[dip]),
      photo: dipPhotoUrl(dipFotos.value[dip]),
      party: dipParty.value.get(dip) || { label: 'Sin grupo', color: '#888' },
    }))
)
const byParty = computed(() => {
  const groups = new Map()
  for (const m of members.value) {
    if (!groups.has(m.party.label)) groups.set(m.party.label, { ...m.party, members: [] })
    groups.get(m.party.label).members.push(m)
  }
  return [...groups.values()]
    .map((g) => ({ ...g, members: g.members.sort((a, b) => a.raw.localeCompare(b.raw, 'es')) }))
    .sort((a, b) => b.members.length - a.members.length || partyRank(a.label) - partyRank(b.label))
})
const columns = computed(() => byParty.value.flatMap((g) => g.members))

// Latest votes where the chamber actually disagreed.
const matrixVotes = computed(() =>
  legVotIdx.value.filter((i) => votResults.value[i].favor >= 15 && votResults.value[i].contra >= 15).slice(0, 12)
)
const cells = computed(() => {
  if (!votosReady.value) return []
  return matrixVotes.value.map((i) => {
    const byDip = new Map()
    const partyCounts = new Map()
    for (const b of data.ballots(i)) {
      byDip.set(b.dip, b.voto)
      if (b.voto <= 3) {
        const c = partyCounts.get(b.label) || { 1: 0, 2: 0, 3: 0 }
        c[b.voto]++
        partyCounts.set(b.label, c)
      }
    }
    const line = new Map([...partyCounts.entries()].map(([label, c]) => [label, [1, 2, 3].reduce((best, k) => (c[k] > c[best] ? k : best), 1)]))
    return {
      i,
      v: votaciones.value[i],
      votes: columns.value.map((m) => {
        const voto = byDip.get(m.dip) || 0
        return { voto, rebel: voto >= 1 && voto <= 3 && line.get(m.party.label) !== voto && m.party.label !== 'Mixto' }
      }),
    }
  })
})

const seatWord = (n) => (n === 1 ? '1 escaño' : `${n} escaños`)
</script>

<template>
  <div class="vd">
    <header class="vd-top">
      <router-link to="/" class="vd-brand">Lo Que Votan</router-link>
      <nav class="vd-nav" aria-label="Secciones">
        <router-link to="/votaciones">Votaciones</router-link>
        <router-link to="/diputados">Diputados</router-link>
        <router-link to="/grupos">Partidos</router-link>
        <router-link to="/quiz">Test de afinidad</router-link>
      </nav>
      <label class="vd-scope">
        <span class="vd-sr">Parlamento</span>
        <select :value="currentScopeId" @change="setScope($event.target.value)">
          <option v-for="a in ambitos" :key="a.id" :value="a.id">{{ a.nombre }}</option>
        </select>
      </label>
    </header>

    <section class="vd-intro">
      <h1>
        Quién vota por
        <span class="vd-slot">
          <span aria-hidden="true">{{ province }}</span><svg viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          <select v-model="province" aria-label="Provincia">
            <option v-for="[p, n] in provinces" :key="p" :value="p">{{ p }} ({{ n }})</option>
          </select>
        </span>
      </h1>
      <p v-if="members.length">
        {{ province }} elige {{ members.length }} {{ members.length === 1 ? 'diputado' : 'diputados' }} en el {{ ambitos.find((a) => a.id === currentScopeId)?.nombre || 'parlamento' }}.
        Abajo tienes lo que votó cada uno en las últimas votaciones reñidas.
      </p>
      <p v-else>Cargando los escaños de esta legislatura…</p>
    </section>

    <section class="vd-orla" v-if="byParty.length" aria-label="Diputados de la provincia">
      <div v-for="g in byParty" :key="g.label" class="vd-group">
        <h2><span class="vd-gsw" :style="{ background: g.color }"></span>{{ g.label }} <small>{{ seatWord(g.members.length) }}</small></h2>
        <ul>
          <li v-for="m in g.members" :key="m.dip">
            <router-link :to="'/diputado/' + encodeURIComponent(m.raw)">
              <span class="vd-oval">
                <img v-if="m.photo" :src="m.photo" :alt="''" loading="lazy" />
                <span v-else class="vd-ini">{{ avatarInitials(m.raw) }}</span>
              </span>
              <span class="vd-name">{{ m.name }}</span>
            </router-link>
          </li>
        </ul>
      </div>
    </section>

    <section class="vd-matrix" v-if="cells.length && columns.length">
      <div class="vd-mhead">
        <h2>Lo que votaron</h2>
        <ul class="vd-key">
          <li><svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="6" class="g-si" /></svg>A favor</li>
          <li><svg viewBox="0 0 20 20"><path d="M5 5l10 10M15 5L5 15" class="g-no" /></svg>En contra</li>
          <li><svg viewBox="0 0 20 20"><path d="M5 10h10" class="g-abs" /></svg>Abstención</li>
          <li><span class="vd-rebel-key"></span>Votó distinto a su grupo</li>
        </ul>
      </div>
      <div class="vd-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col" class="vd-vcol">Votación</th>
              <th v-for="m in columns" :key="m.dip" scope="col" class="vd-dcol" :title="m.name" :style="{ '--c': m.party.color }">
                <span class="vd-mini">
                  <img v-if="m.photo" :src="m.photo" alt="" loading="lazy" />
                  <span v-else>{{ avatarInitials(m.raw) }}</span>
                </span>
                <span class="vd-sr">{{ m.name }}, {{ m.party.label }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in cells" :key="row.i">
              <th scope="row" class="vd-vcol">
                <router-link :to="'/votacion/' + row.v.id">
                  <span class="vd-vdate">{{ shortDate(row.v.fecha) }}</span>
                  {{ row.v.titulo_ciudadano }}
                </router-link>
              </th>
              <td v-for="(c, k) in row.votes" :key="k" :class="{ 'is-rebel': c.rebel }" :title="`${columns[k].name}: ${VOTE_WORD[c.voto] || 'sin registro'}`">
                <svg v-if="c.voto === 1" viewBox="0 0 20 20"><circle cx="10" cy="10" r="6" class="g-si" /></svg>
                <svg v-else-if="c.voto === 2" viewBox="0 0 20 20"><path d="M5 5l10 10M15 5L5 15" class="g-no" /></svg>
                <svg v-else-if="c.voto === 3" viewBox="0 0 20 20"><path d="M5 10h10" class="g-abs" /></svg>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="vd-quiz">
      <h2>¿Y tú con quién coincides?</h2>
      <p>Vota a ciegas propuestas que ya pasaron por el pleno y compara tus respuestas con las de cada grupo.</p>
      <router-link to="/quiz" class="vd-btn">Hacer el test de afinidad</router-link>
    </section>

    <footer class="vd-foot">
      <p>Fotografías y votaciones oficiales del Congreso y de los parlamentos autonómicos. Títulos resumidos con IA. <router-link to="/metodologia">Metodología</router-link></p>
    </footer>
  </div>
</template>

<style scoped>
.vd {
  --ink: #23272c;
  --ink-2: #5f6670;
  --rule: #dde0e4;
  --paper: #ffffff;
  --orla: #24272b;
  --gilt: #c4ad78;
  min-height: 100vh;
  background: var(--paper);
  color: var(--ink);
  font-family: 'Atkinson Hyperlegible Next', system-ui, sans-serif;
  font-size: 17px;
  line-height: 1.55;
}
.vd a, .vd a:hover { color: inherit; }
.vd h1, .vd h2 { font-family: 'Literata', Georgia, serif; color: inherit; font-weight: 500; }
.vd-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }

.vd-top { display: flex; align-items: center; gap: 2rem; padding: 20px 48px; border-bottom: 1px solid var(--rule); }
.vd-brand { font-family: 'Literata', serif; font-weight: 600; font-size: 1.25rem; text-decoration: none; margin-right: auto; }
.vd-nav { display: flex; gap: 1.5rem; }
.vd-nav a { text-decoration: none; color: var(--ink-2) !important; }
.vd-nav a:hover { color: var(--ink) !important; text-decoration: underline; text-underline-offset: 4px; }
.vd-scope select { appearance: none; border: 1px solid var(--rule); border-radius: 999px; padding: 0.35rem 0.9rem; font: inherit; font-size: 0.9rem; background: var(--paper); color: var(--ink); }

.vd-intro { padding: 64px 48px 48px; max-width: 980px; }
.vd-intro h1 { font-size: clamp(2.4rem, 5.5vw, 4.6rem); line-height: 1.05; letter-spacing: -0.02em; font-weight: 400; margin-bottom: 1.25rem; }
.vd-slot { position: relative; display: inline-flex; align-items: baseline; gap: 0.15em; font-style: italic; border-bottom: 2px solid var(--ink); line-height: 1.1; }
.vd-slot svg { width: 0.3em; height: 0.2em; align-self: center; fill: currentColor; }
.vd-slot select { position: absolute; inset: 0; width: 100%; opacity: 0; cursor: pointer; font-size: 16px; }
.vd-slot:focus-within { outline: 3px solid #7aa7d8; outline-offset: 4px; }
.vd-intro p { color: var(--ink-2); font-size: 1.15rem; max-width: 52ch; }

.vd-orla { background: var(--orla); color: #ecebe6; padding: 56px 48px 48px; display: flex; flex-direction: column; gap: 44px; }
.vd-group h2 { display: flex; align-items: center; gap: 0.6rem; font-size: 1.5rem; margin-bottom: 1.25rem; padding-bottom: 0.6rem; border-bottom: 1px solid rgba(196, 173, 120, 0.35); }
.vd-group h2 small { font-family: 'Atkinson Hyperlegible Next', sans-serif; font-size: 0.9rem; color: #a9a59a; font-weight: 400; margin-left: 0.3rem; }
.vd-gsw { width: 14px; height: 14px; border-radius: 50%; box-shadow: 0 0 0 2px var(--orla), 0 0 0 3px rgba(255, 255, 255, 0.35); }
.vd-group ul { list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 28px 20px; }
.vd-group a { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.6rem; text-decoration: none; }
.vd-oval {
  width: 96px;
  height: 124px;
  border-radius: 50%;
  overflow: hidden;
  background: #3a3e44;
  box-shadow: 0 0 0 1px var(--gilt), 0 0 0 5px var(--orla), 0 0 0 6px rgba(196, 173, 120, 0.45);
  display: grid;
  place-items: center;
}
.vd-oval img { width: 100%; height: 100%; object-fit: cover; filter: grayscale(1) contrast(1.05); transition: filter 0.3s; }
.vd-group a:hover img { filter: none; }
.vd-ini { font-family: 'Literata', serif; font-size: 1.6rem; color: var(--gilt); }
.vd-name { font-family: 'Literata', serif; font-size: 0.92rem; line-height: 1.25; max-width: 13ch; }
.vd-group a:hover .vd-name { text-decoration: underline; text-underline-offset: 3px; }

.vd-matrix { padding: 56px 48px 0; }
.vd-mhead { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem 2rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.vd-mhead h2 { font-size: 2.2rem; letter-spacing: -0.015em; }
.vd-key { list-style: none; display: flex; flex-wrap: wrap; gap: 0.4rem 1.25rem; font-size: 0.9rem; color: var(--ink-2); }
.vd-key li { display: inline-flex; align-items: center; gap: 0.35rem; }
.vd-key svg { width: 18px; height: 18px; }
.vd-rebel-key { width: 16px; height: 16px; background: #ffe58a; border-radius: 2px; }
.g-si { fill: var(--ink); }
.g-no, .g-abs { stroke: var(--ink); stroke-width: 2.4; stroke-linecap: round; fill: none; }

.vd-scroll { position: relative; overflow-x: auto; border-top: 2px solid var(--ink); }
.vd table { border-collapse: collapse; }
.vd-vcol { position: sticky; left: 0; background: var(--paper); text-align: left; font-weight: 400; min-width: 20rem; max-width: 20rem; padding: 0.55rem 1.25rem 0.55rem 0; border-bottom: 1px solid var(--rule); z-index: 1; }
thead .vd-vcol { font-size: 0.85rem; color: var(--ink-2); vertical-align: bottom; }
.vd-vcol a { text-decoration: none; font-size: 0.92rem; line-height: 1.3; display: block; }
.vd-vcol a:hover { text-decoration: underline; text-underline-offset: 3px; }
.vd-vdate { display: block; font-size: 0.78rem; color: var(--ink-2); }
.vd-dcol { padding: 10px 2px 6px; border-bottom: 3px solid var(--c); vertical-align: bottom; }
.vd-mini { display: block; width: 26px; height: 34px; border-radius: 50%; overflow: hidden; margin: 0 auto; background: #e6e7e9; font-size: 0.6rem; line-height: 34px; text-align: center; }
.vd-mini img { width: 100%; height: 100%; object-fit: cover; filter: grayscale(1); }
.vd td { width: 32px; height: 40px; text-align: center; border-bottom: 1px solid var(--rule); padding: 0; }
.vd td svg { width: 18px; height: 18px; display: block; margin: 0 auto; }
.vd td.is-rebel { background: #ffe58a; }
.vd tbody tr:hover td, .vd tbody tr:hover th { background-color: #f4f5f6; }
.vd tbody tr:hover td.is-rebel { background: #ffd84d; }

.vd-quiz { margin: 72px 48px 0; padding: 40px 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); display: grid; grid-template-columns: 1fr auto; gap: 0.5rem 2rem; align-items: center; }
.vd-quiz h2 { font-size: 2rem; }
.vd-quiz p { color: var(--ink-2); grid-column: 1; max-width: 56ch; }
.vd-btn { grid-column: 2; grid-row: 1 / span 2; background: var(--ink); color: #fff !important; padding: 0.85rem 1.4rem; border-radius: 999px; text-decoration: none; font-weight: 700; white-space: nowrap; }
.vd-btn:hover { background: #3a4049; text-decoration: none; }
.vd-foot { padding: 28px 48px 96px; font-size: 0.9rem; color: var(--ink-2); }
.vd-foot a { text-decoration: underline; text-underline-offset: 3px; margin-left: 0.5rem; }

@media (max-width: 860px) {
  .vd-top { padding: 14px 16px; gap: 1rem; flex-wrap: wrap; }
  .vd-nav { order: 3; width: 100%; gap: 1rem; font-size: 0.95rem; }
  .vd-scope select { max-width: 50vw; }
  .vd-intro { padding: 36px 16px 32px; }
  .vd-orla { padding: 36px 16px; gap: 32px; }
  .vd-group ul { grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); gap: 20px 10px; }
  .vd-oval { width: 76px; height: 98px; }
  .vd-matrix { padding: 40px 16px 0; }
  .vd-vcol { min-width: 11rem; max-width: 11rem; }
  .vd-quiz { margin: 48px 16px 0; grid-template-columns: 1fr; }
  .vd-btn { grid-column: 1; grid-row: auto; justify-self: start; margin-top: 0.75rem; }
  .vd-foot { padding: 24px 16px 96px; }
}
</style>
