<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useData } from '../composables/useData'
import ViewState from '../components/ViewState.vue'

const { ambitos, currentScopeId } = useData()

const auditIndex = ref(null)
const auditDetail = ref(null)
const auditLoading = ref(true)
const auditError = ref('')

const METRIC_LABELS = {
  genericTitlesPct: 'Titulos genericos',
  unknownGroupsPct: 'Grupos desconocidos',
  dateAnomaliesPct: 'Fechas anomalias',
  rawTotalsMismatchPct: 'Totales inconsistentes',
  emptySummaryPct: 'Resumen vacio',
  nominalCoveragePct: 'Cobertura nominal',
  votesWithoutNominalDetailPct: 'Sin detalle nominal',
}

const currentScope = computed(() =>
  ambitos.value.find((scope) => scope.id === currentScopeId.value) || null
)

const currentScopeLabel = computed(() => currentScope.value?.nombre || currentScopeId.value)

const currentIndexItem = computed(() =>
  auditIndex.value?.scopes?.find((scope) => scope.scope === currentScopeId.value) || null
)

const detailMetrics = computed(() => {
  const metrics = auditDetail.value?.metrics || {}
  return Object.entries(metrics).map(([key, value]) => ({
    key,
    label: METRIC_LABELS[key] || key,
    value: formatPercent(value),
  }))
})

watch(currentScopeLabel, (label) => {
  document.title = `Audit | ${label} | Lo Que Votan`
}, { immediate: true })

watch(currentScopeId, () => {
  loadAuditDetail()
}, { immediate: true })

onMounted(() => {
  setRobotsNoindex()
  loadAuditIndex()
})

onUnmounted(() => {
  restoreRobotsMeta()
})

async function loadAuditIndex() {
  try {
    const resp = await fetch(`${import.meta.env.BASE_URL}data/quality_status_index.json`)
    if (!resp.ok) return
    auditIndex.value = await resp.json()
  } catch (error) {
    console.warn('Error loading audit index:', error)
  }
}

async function loadAuditDetail() {
  auditLoading.value = true
  auditError.value = ''
  auditDetail.value = null

  try {
    const scopePath = currentScopeId.value === 'nacional' ? '' : `${currentScopeId.value}/`
    const resp = await fetch(`${import.meta.env.BASE_URL}data/${scopePath}quality_status.json`)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    auditDetail.value = await resp.json()
  } catch (error) {
    console.error('Error loading audit detail:', error)
    auditError.value = 'No se pudo cargar la auditoria de calidad de este ambito.'
  } finally {
    auditLoading.value = false
  }
}

function statusLabel(status) {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'critical') return 'Incidencias'
  if (normalized === 'warn') return 'Avisos'
  return 'Estable'
}

function statusClass(status) {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'critical') return 'status-pill--critical'
  if (normalized === 'warn') return 'status-pill--warn'
  return 'status-pill--ok'
}

function incidentClass(severity) {
  const normalized = String(severity || '').toLowerCase()
  if (normalized === 'critical' || normalized === 'error') return 'incident-card--critical'
  if (normalized === 'warn' || normalized === 'warning') return 'incident-card--warn'
  return 'incident-card--info'
}

function formatDate(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  return new Intl.DateTimeFormat('es-ES', {
    dateStyle: 'long',
    timeStyle: 'short',
    timeZone: 'Europe/Madrid',
  }).format(parsed)
}

function formatPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '0%'
  return `${numeric.toLocaleString('es-ES', { maximumFractionDigits: 2 })}%`
}

function ensureRobotsMeta() {
  let meta = document.querySelector('meta[name="robots"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute('name', 'robots')
    document.head.appendChild(meta)
  }
  return meta
}

function setRobotsNoindex() {
  const meta = ensureRobotsMeta()
  meta.dataset.previousContent = meta.getAttribute('content') || ''
  meta.setAttribute('content', 'noindex, nofollow')
}

function restoreRobotsMeta() {
  const meta = document.querySelector('meta[name="robots"]')
  if (!meta) return
  const previous = meta.dataset.previousContent || ''
  if (previous) {
    meta.setAttribute('content', previous)
  } else {
    meta.removeAttribute('content')
  }
  delete meta.dataset.previousContent
}
</script>

<template>
  <section class="audit-page">
    <div class="container" style="padding-top: 2rem; padding-bottom: 4rem;">
      <div class="audit-header">
        <div>
          <p class="audit-kicker">Auditoria interna</p>
          <h1 data-testid="audit-page">Estado de calidad</h1>
          <p class="audit-subtitle">
            Resumen por ambito y detalle del ambito activo: {{ currentScopeLabel }}.
          </p>
        </div>
        <div v-if="auditDetail" class="status-pill" :class="statusClass(auditDetail.status)">
          {{ statusLabel(auditDetail.status) }} · {{ auditDetail.score }}/100
        </div>
      </div>

      <ViewState
        v-if="auditLoading"
        type="loading"
        message="Cargando auditoria de calidad..."
      />

      <div v-else-if="auditError" class="audit-state">
        <ViewState
          type="error"
          title="No pudimos cargar la auditoria"
          :message="auditError"
          action-label="Reintentar"
          @action="loadAuditDetail"
        />
      </div>

      <template v-else-if="auditDetail">
        <div v-if="auditIndex?.scopes?.length" class="scope-grid">
          <article
            v-for="scope in auditIndex.scopes"
            :key="scope.scope"
            class="scope-card"
            :class="{ 'scope-card--active': scope.scope === currentScopeId }"
          >
            <div class="scope-card__top">
              <strong>{{ ambitos.find((item) => item.id === scope.scope)?.nombre || scope.scope }}</strong>
              <span class="status-pill status-pill--small" :class="statusClass(scope.status)">
                {{ statusLabel(scope.status) }}
              </span>
            </div>
            <div class="scope-card__meta">
              <span>Score {{ scope.score }}/100</span>
              <span>{{ scope.incidents }} incidencias</span>
            </div>
          </article>
        </div>

        <div class="audit-grid">
          <article class="audit-card">
            <div class="audit-card__head">
              <h2>{{ currentScopeLabel }}</h2>
              <span v-if="auditDetail.generatedAt" class="audit-meta">
                Auditado {{ formatDate(auditDetail.generatedAt) }}
              </span>
            </div>
            <p class="audit-summary">{{ auditDetail.summary || 'Sin resumen de auditoria.' }}</p>
            <div class="stats-row">
              <div class="stat-box">
                <span class="stat-box__label">Score</span>
                <strong>{{ auditDetail.score }}/100</strong>
              </div>
              <div class="stat-box">
                <span class="stat-box__label">Votaciones</span>
                <strong>{{ auditDetail.votes ?? 0 }}</strong>
              </div>
              <div class="stat-box">
                <span class="stat-box__label">Estado</span>
                <strong>{{ statusLabel(auditDetail.status) }}</strong>
              </div>
            </div>
          </article>

          <article class="audit-card">
            <div class="audit-card__head">
              <h2>Metricas</h2>
              <span v-if="currentIndexItem" class="audit-meta">
                {{ currentIndexItem.incidents }} incidencias registradas
              </span>
            </div>
            <div class="metrics-list">
              <div v-for="metric in detailMetrics" :key="metric.key" class="metric-row">
                <span>{{ metric.label }}</span>
                <strong>{{ metric.value }}</strong>
              </div>
            </div>
          </article>
        </div>

        <article class="audit-card">
          <div class="audit-card__head">
            <h2>Incidencias</h2>
            <span class="audit-meta">{{ auditDetail.incidents?.length || 0 }} items</span>
          </div>

          <ViewState
            v-if="!auditDetail.incidents?.length"
            type="empty"
            icon="&#10003;"
            title="Sin incidencias"
            message="No hay avisos ni errores registrados para este ambito."
            :padded="false"
          />

          <div v-else class="incidents-list">
            <article
              v-for="incident in auditDetail.incidents"
              :key="incident.id"
              class="incident-card"
              :class="incidentClass(incident.severity)"
            >
              <div class="incident-card__head">
                <strong>{{ incident.id }}</strong>
                <span class="incident-severity">{{ incident.severity || 'info' }}</span>
              </div>
              <p>{{ incident.message }}</p>
            </article>
          </div>
        </article>
      </template>
    </div>
  </section>
</template>

<style scoped>
.audit-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.audit-kicker {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-primary);
}

.audit-subtitle {
  margin: 0.35rem 0 0;
  color: var(--color-muted);
}

.audit-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.scope-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.scope-card,
.audit-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.scope-card {
  padding: 1rem;
}

.scope-card--active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary-light);
}

.scope-card__top,
.audit-card__head,
.incident-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.scope-card__meta,
.stats-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.scope-card__meta {
  margin-top: 0.65rem;
  font-size: 0.9rem;
  color: var(--color-muted);
}

.audit-card {
  padding: 1.25rem;
}

.audit-meta {
  color: var(--color-muted);
  font-size: 0.9rem;
}

.audit-summary {
  margin: 0.8rem 0 1rem;
  line-height: 1.5;
}

.stats-row {
  margin-top: 1rem;
}

.stat-box {
  min-width: 120px;
  padding: 0.85rem 0.95rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
}

.stat-box__label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.8rem;
  color: var(--color-muted);
}

.metrics-list {
  display: grid;
  gap: 0.7rem;
  margin-top: 1rem;
}

.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--color-border);
}

.metric-row:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.incidents-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}

.incident-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface-muted);
}

.incident-card p {
  margin: 0.55rem 0 0;
  line-height: 1.5;
}

.incident-card--info {
  border-color: rgba(59, 130, 246, 0.25);
}

.incident-card--warn {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.08);
}

.incident-card--critical {
  border-color: rgba(239, 68, 68, 0.34);
  background: rgba(239, 68, 68, 0.08);
}

.incident-severity,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1px solid transparent;
  white-space: nowrap;
}

.status-pill--small {
  padding: 0.25rem 0.55rem;
  font-size: 0.72rem;
}

.status-pill--ok {
  color: #166534;
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.26);
}

.status-pill--warn {
  color: #92400e;
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.28);
}

.status-pill--critical {
  color: #991b1b;
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.28);
}

@media (max-width: 768px) {
  .audit-header,
  .audit-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .audit-header {
    gap: 0.85rem;
  }
}
</style>
