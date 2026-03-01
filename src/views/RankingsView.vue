<script setup>
import { computed, ref } from 'vue'
import { useData } from '../composables/useData'
import { pct, dipPhotoUrl, avatarInitials, avatarStyle, getGroupInfo } from '../utils'

const { diputados, grupos, dipStats, dipFotos, currentScopeId, loading } = useData()

const rankings = computed(() => {
  if (loading.value || !diputados.value.length) return { rebels: [], absents: [] }

  // Calculate the maximum possible votes any deputy has in the current dataset
  // to establish a dynamic baseline.
  let maxPossibleVotes = 0
  for (let i = 0; i < diputados.value.length; i++) {
    const ds = dipStats.value[i]
    if (!ds) continue
    const possible = ds.total + (ds.no_vota || 0)
    if (possible > maxPossibleVotes) maxPossibleVotes = possible
  }

  // Require at least 15% of the max votes (or 30 votes, whichever is higher)
  // This filters out deputies who were only in office very briefly before resigning.
  const dynamicMinVotes = Math.max(30, maxPossibleVotes * 0.15)

  const data = []
  for (let i = 0; i < diputados.value.length; i++) {
    const ds = dipStats.value[i]
    if (!ds) continue
    const allPossibleVotes = ds.total + (ds.no_vota || 0)
    
    if (allPossibleVotes < dynamicMinVotes) continue

    const gName = ds.mainGrupo >= 0 ? grupos.value[ds.mainGrupo] : 'Sin grupo'
    const gInfo = getGroupInfo(gName)

    data.push({
      idx: i,
      name: diputados.value[i],
      grupo: gInfo.label,
      grupoColor: gInfo.color,
      loyalty: ds.loyalty,
      absentismo: ds.no_vota / allPossibleVotes,
      photo: dipPhotoUrl(dipFotos.value[i]),
      total: ds.total,
      no_vota: ds.no_vota || 0
    })
  }

  const rebels = [...data]
    .sort((a, b) => a.loyalty - b.loyalty)
    .slice(0, 15)

  const absents = [...data]
    .sort((a, b) => b.absentismo - a.absentismo)
    .slice(0, 15)

  return { rebels, absents }
})
</script>

<template>
  <div class="container py-4">
    <div class="header-with-meta mb-4">
      <h1>Rankings de Comportamiento</h1>
      <p class="lead">Diputados que más se alejan de la norma de su grupo o de la asistencia a la cámara.</p>
    </div>

    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div></div>

    <div v-else class="ranking-layout">
      <!-- REBELS -->
      <div class="ranking-section">
        <div class="section-header">
          <h2>Más "Rebeldes"</h2>
          <span class="badge badge--contra">Menor lealtad</span>
        </div>
        <p class="text-muted small mb-3">Diputados que más veces han votado distinto a la mayoría de su propio partido.</p>
        
        <div class="ranking-list">
          <router-link 
            v-for="(d, i) in rankings.rebels" 
            :key="d.idx" 
            :to="'/diputado/' + encodeURIComponent(d.name)"
            class="ranking-item"
          >
            <span class="rank-num">{{ i + 1 }}</span>
            <img v-if="d.photo" :src="d.photo" class="rank-avatar" alt="">
            <div v-else class="rank-avatar avatar-mini" :style="avatarStyle(d.name)">{{ avatarInitials(d.name) }}</div>
            
            <div class="rank-info">
              <div class="rank-name">{{ d.name }}</div>
              <div class="rank-meta" :style="{ color: d.grupoColor, fontWeight: 600 }">{{ d.grupo }}</div>
            </div>
            
            <div class="rank-stat">
              <div class="rank-stat-value">{{ pct(d.loyalty) }}</div>
              <div class="rank-stat-label">lealtad</div>
            </div>
          </router-link>
        </div>
      </div>

      <!-- ABSENTS -->
      <div class="ranking-section">
        <div class="section-header">
          <h2>Más Absentistas</h2>
          <span class="badge badge--warning">No vota</span>
        </div>
        <p class="text-muted small mb-3">Diputados con mayor porcentaje de "No Vota" sobre el total de votaciones celebradas.</p>

        <div class="ranking-list">
          <router-link 
            v-for="(d, i) in rankings.absents" 
            :key="d.idx" 
            :to="'/diputado/' + encodeURIComponent(d.name)"
            class="ranking-item"
          >
            <span class="rank-num">{{ i + 1 }}</span>
            <img v-if="d.photo" :src="d.photo" class="rank-avatar" alt="">
            <div v-else class="rank-avatar avatar-mini" :style="avatarStyle(d.name)">{{ avatarInitials(d.name) }}</div>
            
            <div class="rank-info">
              <div class="rank-name">{{ d.name }}</div>
              <div class="rank-meta" :style="{ color: d.grupoColor, fontWeight: 600 }">{{ d.grupo }}</div>
            </div>
            
            <div class="rank-stat rank-stat--alt">
              <div class="rank-stat-value">{{ pct(d.absentismo) }}</div>
              <div class="rank-stat-label">absentismo</div>
            </div>
          </router-link>
        </div>
      </div>
    </div>

    <div class="mt-4 p-3 bg-light rounded small text-muted">
      <strong>Nota sobre los ránkings:</strong> Solo se incluyen diputados con una participación mínima (al menos el 15% del total de votaciones del periodo) para evitar distorsiones por bajas o sustituciones prematuras. El absentismo incluye tanto ausencias justificadas como no justificadas, ya que los datos abiertos no distinguen el motivo de la falta de voto.
    </div>
  </div>
</template>

<style scoped>
.ranking-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2.5rem;
}

.ranking-section {
  display: flex;
  flex-direction: column;
}

.ranking-list {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
}

.ranking-item:hover {
  background: var(--color-surface-muted);
}

.ranking-item:last-child {
  border-bottom: none;
}

.rank-num {
  width: 24px;
  font-weight: 800;
  color: var(--color-muted);
  font-size: 0.9rem;
}

.rank-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  margin: 0 1rem;
  flex-shrink: 0;
  border: 1px solid var(--color-border);
}

.avatar-mini {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
}

.rank-info {
  flex: 1;
  min-width: 0;
}

.rank-name {
  font-weight: 700;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-text);
}

.rank-meta {
  font-size: 0.75rem;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-stat {
  text-align: right;
  padding-left: 1rem;
}

.rank-stat-value {
  font-weight: 800;
  font-size: 1.1rem;
  color: var(--color-primary);
  line-height: 1;
}

.rank-stat--alt .rank-stat-value {
  color: var(--color-contra);
}

.rank-stat-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--color-muted);
  margin-top: 0.2rem;
}

@media (max-width: 900px) {
  .ranking-layout {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
}
</style>
