<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useData } from '../composables/useData'
import { fmt, avatarStyle, avatarInitials } from '../utils'

const props = defineProps({
  dipIdx: Number,
  tag: String,
})

const emit = defineEmits(['close'])

const { diputados, grupos, dipStats, votos, votaciones, votosByDiputado } = useData()
const copyLabel = ref('Copiar enlace')

const name = computed(() => diputados.value[props.dipIdx])
const ds = computed(() => dipStats.value[props.dipIdx])
const grupoName = computed(() =>
  ds.value.mainGrupo >= 0 ? grupos.value[ds.value.mainGrupo] : 'Sin grupo'
)
const topicLabel = computed(() => fmt(props.tag))

const counts = computed(() => {
  const indices = votosByDiputado.value[props.dipIdx] || []
  let favor = 0, contra = 0, abstencion = 0
  for (let j = 0; j < indices.length; j++) {
    const v = votos.value[indices[j]]
    const votIdx = v[0]
    const code = v[3]
    const tags = votaciones.value[votIdx].etiquetas || []
    if (!tags.includes(props.tag)) continue
    if (code === 1) favor++
    else if (code === 2) contra++
    else if (code === 3) abstencion++
  }
  return { favor, contra, abstencion, total: favor + contra + abstencion }
})

const shareUrl = computed(() =>
  location.origin + location.pathname +
  '#/diputado/' + encodeURIComponent(name.value) +
  '?tag=' + encodeURIComponent(props.tag)
)

const twitterUrl = computed(() => {
  const text = `${name.value} (${grupoName.value}) ha votado ${counts.value.favor} veces A FAVOR de ${topicLabel.value}. Compruebalo: ${shareUrl.value}`
  return 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text)
})

const whatsappUrl = computed(() => {
  const text = `${name.value} (${grupoName.value}) ha votado ${counts.value.favor} veces A FAVOR de ${topicLabel.value}. Compruebalo: ${shareUrl.value}`
  return 'whatsapp://send?text=' + encodeURIComponent(text)
})

function barWidth(count) {
  return counts.value.total > 0 ? Math.round((count / counts.value.total) * 100) + '%' : '0%'
}

function veces(count) {
  return count === 1 ? '1 vez' : count + ' veces'
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = shareUrl.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copyLabel.value = 'Copiado!'
  setTimeout(() => { copyLabel.value = 'Copiar enlace' }, 2000)
}

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div
      class="acc-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Ficha de rendicion de cuentas"
      @click.self="emit('close')"
    >
      <div class="acc-card">
        <button class="acc-close" aria-label="Cerrar" @click="emit('close')">&times;</button>
        <div class="avatar" :style="avatarStyle(name)">{{ avatarInitials(name) }}</div>
        <div class="acc-name">{{ name }}</div>
        <div class="acc-grupo">{{ grupoName }}</div>
        <div class="acc-topic">{{ topicLabel }}</div>

        <div class="acc-votes">
          <div class="acc-vote-row">
            <span class="acc-vote-label">A FAVOR</span>
            <div class="acc-vote-bar">
              <div class="acc-vote-bar-fill" :style="{ width: barWidth(counts.favor), background: 'var(--color-favor)' }"></div>
            </div>
            <span class="acc-vote-count">{{ veces(counts.favor) }}</span>
          </div>
          <div class="acc-vote-row">
            <span class="acc-vote-label">EN CONTRA</span>
            <div class="acc-vote-bar">
              <div class="acc-vote-bar-fill" :style="{ width: barWidth(counts.contra), background: 'var(--color-contra)' }"></div>
            </div>
            <span class="acc-vote-count">{{ veces(counts.contra) }}</span>
          </div>
          <div class="acc-vote-row">
            <span class="acc-vote-label">ABSTENCI&Oacute;N</span>
            <div class="acc-vote-bar">
              <div class="acc-vote-bar-fill" :style="{ width: barWidth(counts.abstencion), background: 'var(--color-abstencion)' }"></div>
            </div>
            <span class="acc-vote-count">{{ veces(counts.abstencion) }}</span>
          </div>
        </div>

        <div class="acc-url">loquevotan.es</div>
        <div class="acc-share">
          <button class="acc-share-btn acc-share-btn--primary" @click="copyUrl">{{ copyLabel }}</button>
          <a class="acc-share-btn" :href="twitterUrl" target="_blank" rel="noopener">X / Twitter</a>
          <a class="acc-share-btn" :href="whatsappUrl" target="_blank" rel="noopener">WhatsApp</a>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.acc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.acc-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 420px;
  width: 100%;
  padding: 2rem;
  position: relative;
  text-align: center;
}

.acc-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-muted);
  line-height: 1;
}

.acc-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 0.25rem;
}

.acc-grupo {
  font-size: 0.9rem;
  color: var(--color-muted);
  margin-bottom: 1.25rem;
}

.acc-topic {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 1rem;
  padding: 0.5rem;
  background: var(--color-primary-light);
  border-radius: var(--radius-sm);
}

.acc-votes {
  text-align: left;
  margin-bottom: 1.5rem;
}

.acc-vote-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.acc-vote-label {
  width: 100px;
  font-size: 0.85rem;
  font-weight: 500;
  text-align: right;
}

.acc-vote-bar {
  flex: 1;
  height: 24px;
  border-radius: 4px;
  background: var(--color-border);
  position: relative;
}

.acc-vote-bar-fill {
  height: 100%;
  border-radius: 4px;
  min-width: 2px;
  transition: width 0.3s;
}

.acc-vote-count {
  width: 50px;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
}

.acc-url {
  font-size: 0.75rem;
  color: var(--color-muted);
  margin-bottom: 1rem;
}

.acc-share {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
}

.acc-share-btn {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  transition: background 0.15s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}

.acc-share-btn:hover {
  background: var(--color-bg);
  text-decoration: none;
  color: inherit;
}

.acc-share-btn--primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.acc-share-btn--primary:hover {
  background: var(--color-primary-hover);
}
</style>
