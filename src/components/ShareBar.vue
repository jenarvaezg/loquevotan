<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: String,
  result: { type: String, default: null },
})

const copyLabel = ref('Copiar enlace')

function shareText() {
  if (props.result) {
    return `${props.title} \u2192 ${props.result}. Mira como voto cada diputado:`
  }
  return `${props.title} \u2014 Lo Que Votan:`
}

function twitterUrl() {
  const url = window.location.href
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText())}&url=${encodeURIComponent(url)}`
}

function whatsappUrl() {
  const url = window.location.href
  return `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText() + ' ' + url)}`
}

async function copyUrl() {
  const url = window.location.href
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
