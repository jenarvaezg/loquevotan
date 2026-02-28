<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import { fmt } from '../utils'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'

const route = useRoute()
const { votaciones, votResults, loading, error, votIdById, loadVotosForLeg } = useData()

const votIdx = computed(() => {
  const id = route.params.id
  return votIdById.value[id]
})

const v = computed(() => votIdx.value !== undefined ? votaciones.value[votIdx.value] : null)
const res = computed(() => votIdx.value !== undefined ? votResults.value[votIdx.value] : null)

watch(v, (newV) => {
  if (newV && newV.legislatura) {
    loadVotosForLeg(newV.legislatura)
  }
}, { immediate: true })
</script>

<template>
  <div class="widget-container">
    <div v-if="loading" class="widget-loading">Cargando datos...</div>
    <div v-else-if="error" class="widget-error">Error al cargar datos</div>
    <div v-else-if="v && res" class="widget-content">
      <div class="widget-header">
        <h1 class="widget-title">{{ v.titulo_ciudadano }}</h1>
        <div class="widget-meta">
          <span class="widget-date">{{ v.fecha }}</span>
          <ResultBadge :result="res.result" size="sm" />
        </div>
      </div>
      
      <div class="widget-body">
        <VoteBar :favor="res.favor" :contra="res.contra" :abstencion="res.abstencion" :show-labels="true" />
      </div>
      
      <div class="widget-footer">
        <a href="https://jenarvaezg.github.io/loquevotan/" target="_blank" class="widget-branding">
          Lo Que Votan &bull; Ver detalle completo &rarr;
        </a>
      </div>
    </div>
    <div v-else class="widget-not-found">Votación no encontrada</div>
  </div>
</template>

<style scoped>
.widget-container {
  padding: 1rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-family: 'Source Sans 3', sans-serif;
  overflow: hidden;
  max-width: 500px;
}

[data-theme="dark"] .widget-container {
  background: #1e293b;
  border-color: #334155;
  color: white;
}

.widget-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  line-height: 1.3;
  font-family: 'DM Serif Display', serif;
}

.widget-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.widget-date {
  font-size: 0.75rem;
  color: #64748b;
}

.widget-body {
  margin-bottom: 1rem;
}

.widget-footer {
  border-top: 1px solid #f1f5f9;
  padding-top: 0.75rem;
  text-align: right;
}

[data-theme="dark"] .widget-footer {
  border-top-color: #334155;
}

.widget-branding {
  font-size: 0.7rem;
  font-weight: 700;
  color: #4f46e5;
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.widget-branding:hover {
  text-decoration: underline;
}

.widget-loading, .widget-error, .widget-not-found {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  color: #64748b;
}
</style>
