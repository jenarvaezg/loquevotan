<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  title: String,
  result: { type: String, default: null },
  shareUrl: { type: String, default: '' },
  shareText: { type: String, default: '' },
})

const copyLabel = ref('Copiar enlace')
const copyTextLabel = ref('Copiar texto')
const resolvedShareUrl = computed(() => props.shareUrl || window.location.href)
const resolvedShareText = computed(() => {
  if (props.shareText) return props.shareText
  if (props.result) {
    return `${props.title} \u2192 ${props.result}. Mira como voto cada diputado:`
  }
  return `${props.title} \u2014 Lo Que Votan:`
})

function twitterUrl() {
  const url = resolvedShareUrl.value
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(resolvedShareText.value)}&url=${encodeURIComponent(url)}`
}

function whatsappUrl() {
  const url = resolvedShareUrl.value
  return `https://api.whatsapp.com/send?text=${encodeURIComponent(resolvedShareText.value + ' ' + url)}`
}

async function copyToClipboard(value) {
  try {
    await navigator.clipboard.writeText(value)
    return true
  } catch {
    const ta = document.createElement('textarea')
    ta.value = value
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  }
}

async function copyUrl() {
  const url = resolvedShareUrl.value
  await copyToClipboard(url)
  copyLabel.value = 'Copiado!'
  setTimeout(() => { copyLabel.value = 'Copiar enlace' }, 2000)
}

async function copyShareText() {
  const payload = `${resolvedShareText.value} ${resolvedShareUrl.value}`.trim()
  await copyToClipboard(payload)
  copyTextLabel.value = 'Copiado!'
  setTimeout(() => { copyTextLabel.value = 'Copiar texto' }, 2000)
}
</script>

<template>
  <div class="share-bar">
    <button class="share-btn share-btn--copy-text" @click="copyShareText">&#9997;&#65039; {{ copyTextLabel }}</button>
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
.share-btn--copy-text {
  border-color: #0f766e;
  color: #0f766e;
}
.share-btn--copy-text:hover {
  background: #0f766e;
  color: #fff;
}
</style>
