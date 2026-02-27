<script setup>
import { computed } from 'vue'
import { useData } from '../composables/useData'
import { pct, dipPhotoUrl, avatarInitials, avatarStyle } from '../utils'
import VoteBar from './VoteBar.vue'

const props = defineProps({
  idx: Number,
})

const { diputados, grupos, dipStats, dipFotos } = useData()

const name = computed(() => diputados.value[props.idx])
const ds = computed(() => dipStats.value[props.idx])
const grupoName = computed(() =>
  ds.value.mainGrupo >= 0 ? grupos.value[ds.value.mainGrupo] : 'Sin grupo'
)
const photoUrl = computed(() => dipPhotoUrl(dipFotos.value[props.idx]))
</script>

<template>
  <router-link :to="'/diputado/' + encodeURIComponent(name)" class="card dip-card card-link">
    <div class="dip-card-header">
      <img v-if="photoUrl" :src="photoUrl" :alt="name" class="dip-card-photo" loading="lazy">
      <span v-else class="dip-card-avatar" :style="avatarStyle(name)">{{ avatarInitials(name) }}</span>
      <div>
        <div class="dip-card-name">{{ name }}</div>
        <span class="badge badge--grupo">{{ grupoName }}</span>
      </div>
    </div>
    <div class="dip-card-stats">
      <span><strong>{{ ds.total }}</strong> votos</span>
      <span>Lealtad: <strong>{{ pct(ds.loyalty) }}</strong></span>
    </div>
    <VoteBar :favor="ds.favor" :contra="ds.contra" :abstencion="ds.abstencion" :total="ds.total" small />
  </router-link>
</template>
