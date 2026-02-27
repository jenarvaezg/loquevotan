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
