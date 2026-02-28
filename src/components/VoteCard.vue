<script setup>
import { computed } from 'vue'
import { useData } from '../composables/useData'
import { fmt, subTipoLabel, subTipoBadgeClass } from '../utils'
import VoteBar from './VoteBar.vue'
import ResultBadge from './ResultBadge.vue'

const props = defineProps({
  idx: Number,
  votData: Object,
  votResult: Object,
})

const { votaciones, votResults, categorias } = useData()

const vot = computed(() => props.votData || votaciones.value[props.idx])
const r = computed(() => props.votResult || votResults.value[props.idx])
const catLabel = computed(() => {
  if (props.votData) return props.votData.categoria
  return categorias.value[vot.value?.categoria]
})
const linkIdx = computed(() => props.votData?.idx ?? props.idx)
</script>

<template>
  <router-link :to="'/votacion/' + linkIdx" class="card vote-card card-link">
    <div class="vote-card-header">
      <span class="vote-card-title">{{ vot.titulo_ciudadano }}</span>
      <ResultBadge :result="r.result" />
    </div>
    <div class="vote-card-meta">
      <span>{{ vot.fecha }}</span>
      <span v-if="vot.subTipo" class="badge badge--sm" :class="subTipoBadgeClass(vot.subTipo)">{{ subTipoLabel(vot.subTipo) }}</span>
      <span class="badge badge--cat">{{ fmt(catLabel) }}</span>
      <span v-if="vot.proponente" class="badge badge--proponente">{{ vot.proponente }}</span>
    </div>
    <VoteBar :favor="r.favor" :contra="r.contra" :abstencion="r.abstencion" :total="r.total" small />
    <div v-if="vot.etiquetas?.length" class="vote-card-tags">
      <span v-for="tag in vot.etiquetas.slice(0, 4)" :key="tag" class="chip">{{ fmt(tag) }}</span>
      <span v-if="vot.etiquetas.length > 4" class="chip">+{{ vot.etiquetas.length - 4 }}</span>
    </div>
  </router-link>
</template>
