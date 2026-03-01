<script setup>
import { computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useData } from '../composables/useData'
import VoteBar from '../components/VoteBar.vue'
import ResultBadge from '../components/ResultBadge.vue'

const route = useRoute()
const { votaciones, votResults, loading, error, votIdById, loadVotosForLeg } = useData()

const isEmbed = computed(() => route.query.embed === 'true')

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

onMounted(() => {
  if (isEmbed.value) {
    // In embed mode, we might want to force a specific theme or behavior
    document.documentElement.dataset.theme = 'light'
  }
})

const detailUrl = computed(() => {
  if (!v.value) return '#'
  return `https://jenarvaezg.github.io/loquevotan/#/votacion/${v.value.id}`
})
</script>

<template>
  <div class="widget-wrapper" :class="{ 'is-embed': isEmbed }">
    <div class="widget-container">
      <div v-if="loading" class="widget-status">
        <div class="spinner"></div>
        <p>Cargando datos...</p>
      </div>
      <div v-else-if="error" class="widget-status widget-status--error">
        <p>Error al cargar la votación</p>
      </div>
      <div v-else-if="v && res" class="widget-content">
        <div class="widget-header">
          <div class="widget-meta-top">
            <span class="widget-date">{{ v.fecha }}</span>
            <ResultBadge :result="res.result" size="sm" />
          </div>
          <h1 class="widget-title">{{ v.titulo_ciudadano }}</h1>
        </div>
        
        <div class="widget-body">
          <VoteBar 
            :favor="res.favor" 
            :contra="res.contra" 
            :abstencion="res.abstencion" 
            :total="res.total"
            show-labels 
          />
          <div class="widget-stats-grid">
            <div class="stat-item">
              <span class="stat-value color-favor">{{ res.favor }}</span>
              <span class="stat-label">A favor</span>
            </div>
            <div class="stat-item">
              <span class="stat-value color-contra">{{ res.contra }}</span>
              <span class="stat-label">En contra</span>
            </div>
            <div class="stat-item">
              <span class="stat-value color-abstencion">{{ res.abstencion }}</span>
              <span class="stat-label">Abstención</span>
            </div>
          </div>
        </div>
        
        <div class="widget-footer">
          <a :href="detailUrl" target="_blank" class="widget-branding">
            <span class="branding-logo">Lo Que Votan</span>
            <span class="branding-action">Ver análisis completo &rarr;</span>
          </a>
        </div>
      </div>
      <div v-else class="widget-status">
        <p>Votación no encontrada</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.widget-wrapper {
  padding: 10px;
  background: transparent;
}

.widget-wrapper.is-embed {
  padding: 0;
}

.widget-container {
  background: white;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  font-family: 'Source Sans 3', system-ui, -apple-system, sans-serif;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  max-width: 550px;
  margin: 0 auto;
}

.is-embed .widget-container {
  box-shadow: none;
  border-radius: 8px;
}

[data-theme="dark"] .widget-container {
  background: #1e293b;
  border-color: #334155;
  color: white;
}

.widget-content {
  display: flex;
  flex-direction: column;
}

.widget-header {
  padding: 1.25rem 1.25rem 0.75rem;
}

.widget-meta-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.widget-date {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-muted, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.widget-title {
  font-size: 1.15rem;
  font-weight: 800;
  margin: 0;
  line-height: 1.25;
  color: var(--color-text, #0f172a);
  font-family: 'DM Serif Display', serif;
}

[data-theme="dark"] .widget-title {
  color: #f8fafc;
}

.widget-body {
  padding: 0 1.25rem 1.25rem;
}

.widget-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-top: 1rem;
  text-align: center;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 800;
}

.stat-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-muted, #64748b);
  text-transform: uppercase;
}

.color-favor { color: #16a34a; }
.color-contra { color: #dc2626; }
.color-abstencion { color: #64748b; }

.widget-footer {
  background: var(--color-surface-muted, #f8fafc);
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--color-border, #e2e8f0);
}

[data-theme="dark"] .widget-footer {
  background: #0f172a;
  border-top-color: #334155;
}

.widget-branding {
  display: flex;
  justify-content: space-between;
  align-items: center;
  text-decoration: none;
  transition: opacity 0.2s;
}

.widget-branding:hover {
  opacity: 0.8;
}

.branding-logo {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--color-text, #0f172a);
}

[data-theme="dark"] .branding-logo {
  color: white;
}

.branding-action {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-primary, #2563eb);
}

.widget-status {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  font-size: 0.9rem;
  color: var(--color-muted, #64748b);
}

.widget-status--error {
  color: #dc2626;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid var(--color-border, #e2e8f0);
  border-top-color: var(--color-primary, #2563eb);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
