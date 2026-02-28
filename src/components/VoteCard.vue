<script setup>
import { computed } from 'vue'
import { useData } from '../composables/useData'
import { fmt, subTipoLabel, subTipoBadgeClass, getGroupInfo } from '../utils'
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
const linkId = computed(() => props.votData?.id ?? vot.value?.id)

const proponenteInfo = computed(() => {
  if (!vot.value?.proponente) return null
  return getGroupInfo(vot.value.proponente)
})
</script>

<template>
  <router-link :to="'/votacion/' + linkId" class="card vote-card card-link">
    <div class="vote-card-header">
      <span class="vote-card-title">{{ vot.titulo_ciudadano }}</span>
      <ResultBadge :result="r.result" />
    </div>
    <div class="vote-card-meta">
      <span>{{ vot.fecha }}</span>
      <span v-if="vot.subTipo" class="badge badge--sm" :class="subTipoBadgeClass(vot.subTipo)">{{ subTipoLabel(vot.subTipo) }}</span>
      <span class="badge badge--cat">{{ fmt(catLabel) }}</span>
      <span v-if="proponenteInfo" class="badge" :style="{ backgroundColor: proponenteInfo.color, color: 'white' }">{{ proponenteInfo.label }}</span>
    </div>
    <VoteBar :favor="r.favor" :contra="r.contra" :abstencion="r.abstencion" :total="r.total" small />
    <div v-if="vot.etiquetas?.length" class="vote-card-tags">
      <span v-for="tag in vot.etiquetas.slice(0, 4)" :key="tag" class="chip">{{ fmt(tag) }}</span>
      <span v-if="vot.etiquetas.length > 4" class="chip">+{{ vot.etiquetas.length - 4 }}</span>
    </div>
  </router-link>
</template>

<style scoped>
.vote-card { cursor: pointer; }

.vote-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.vote-card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.35;
  flex: 1;
}

.vote-card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  color: var(--color-muted);
}

.vote-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.5rem;
}
</style>
