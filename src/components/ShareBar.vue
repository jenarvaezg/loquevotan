<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  title: String,
  result: { type: String, default: null },
  shareUrl: { type: String, default: '' },
})

const copyLabel = ref('Copiar enlace')
const resolvedShareUrl = computed(() => props.shareUrl || window.location.href)

function shareText() {
  if (props.result) {
    return `${props.title} \u2192 ${props.result}. Mira como voto cada diputado:`
  }
  return `${props.title} \u2014 Lo Que Votan:`
}

function twitterUrl() {
  const url = resolvedShareUrl.value
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText())}&url=${encodeURIComponent(url)}`
}

function whatsappUrl() {
  const url = resolvedShareUrl.value
  return `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText() + ' ' + url)}`
}

async function copyUrl() {
  const url = resolvedShareUrl.value
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = url
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copyLabel.value = 'Copiado!'
  setTimeout(() => { copyLabel.value = 'Copiar enlace' }, 2000)
}
</script>

<template>
  <div class="share-bar">
    <button class="share-btn share-btn--copy" @click="copyUrl">&#128279; {{ copyLabel }}</button>
    <a class="share-btn share-btn--twitter" :href="twitterUrl()" target="_blank" rel="noopener">
      &#120143; Compartir
    </a>
    <a class="share-btn share-btn--whatsapp" :href="whatsappUrl()" target="_blank" rel="noopener">
      &#128172; WhatsApp
    </a>
  </div>
</template>

<style scoped>
.share-bar {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 1rem;
}

.share-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.85rem;
  border-radius: 50px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  text-decoration: none;
  transition: background 0.15s;
}

.share-btn:hover { background: var(--color-bg); text-decoration: none; color: inherit; }
.share-btn--twitter { border-color: #1da1f2; color: #1da1f2; }
.share-btn--twitter:hover { background: #1da1f2; color: #fff; }
.share-btn--whatsapp { border-color: #25d366; color: #25d366; }
.share-btn--whatsapp:hover { background: #25d366; color: #fff; }
.share-btn--copy:hover { background: var(--color-primary-light); color: var(--color-primary); }
</style>
