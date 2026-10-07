<script setup>
// Compact list of votes: date, title, how the chamber split and the score.
// The split bar uses the seat grammar: solid yes, hatched abstention, hollow no.
import { formatFecha } from '../../utils'

defineProps({
  title: { type: String, required: true },
  votes: { type: Array, required: true },
})
</script>

<template>
  <div class="vote-rows">
    <h2>{{ title }}</h2>
    <ol>
      <li v-for="v in votes" :key="v.id">
        <router-link :to="'/votacion/' + v.id" class="vote-row" data-testid="home-vote-row">
          <span class="vote-row-date">{{ formatFecha(v.fecha, 'short') }}</span>
          <span class="vote-row-title">{{ v.titulo_ciudadano }}</span>
          <span class="vote-row-bar" role="img" :aria-label="`${v.favor} a favor, ${v.contra} en contra, ${v.abstencion} abstenciones`">
            <i class="si" :style="{ flex: v.favor }"></i>
            <i class="abs" :style="{ flex: v.abstencion }"></i>
            <i class="no" :style="{ flex: v.contra }"></i>
          </span>
          <span class="vote-row-score">{{ v.favor }}–{{ v.contra }}</span>
        </router-link>
      </li>
    </ol>
    <router-link to="/votaciones" class="vote-rows-more">Todas las votaciones</router-link>
  </div>
</template>

<style scoped>
.vote-rows h2 { font-size: 1.6rem; padding-bottom: 0.6rem; border-bottom: 2px solid var(--color-text); }
.vote-rows ol { list-style: none; margin-bottom: 1rem; }
.vote-row {
  display: grid;
  grid-template-columns: 5.2rem minmax(0, 1fr) 5rem 5rem;
  gap: 0.9rem;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
  text-decoration: none;
}
.vote-row:hover { color: var(--color-text); text-decoration: none; }
.vote-row:hover .vote-row-title { text-decoration: underline; text-underline-offset: 3px; }
.vote-row-date { font-size: 0.8rem; color: var(--color-muted); }
.vote-row-title { font-weight: 600; line-height: 1.3; }
.vote-row-score { font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.vote-row-bar { display: flex; height: 10px; gap: 2px; }
.vote-row-bar i { display: block; min-width: 0; }
.vote-row-bar .si { background: var(--color-text); }
.vote-row-bar .no { box-shadow: inset 0 0 0 1.5px var(--color-text); }
.vote-row-bar .abs { background: repeating-linear-gradient(135deg, var(--color-text) 0 1.5px, transparent 1.5px 4px); }
.vote-rows-more {
  font-weight: 600;
  color: var(--color-text);
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 5px;
}
.vote-rows-more:hover { color: var(--color-text); text-decoration-color: var(--color-muted); }

@media (max-width: 900px) {
  .vote-row { grid-template-columns: minmax(0, 1fr) 4.5rem; }
  .vote-row-date { grid-column: 1 / -1; margin-bottom: -0.6rem; }
  .vote-row-bar { display: none; }
}
</style>
