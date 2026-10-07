<script setup>
// PROTOTYPE — barra flotante para alternar variantes de diseño (?variant=).
// Solo se monta en dev; no forma parte de ningún diseño.
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  variants: { type: Array, required: true },
})

const route = useRoute()
const router = useRouter()

const index = computed(() => {
  const i = props.variants.findIndex((v) => v.key === route.query.variant)
  return i === -1 ? 0 : i
})

function go(delta) {
  const n = props.variants.length
  const next = props.variants[(index.value + delta + n) % n]
  router.replace({ query: { ...route.query, variant: next.key } })
}

function onKey(e) {
  if (e.target.closest?.('input, textarea, select, [contenteditable]')) return
  if (e.key === 'ArrowLeft') go(-1)
  if (e.key === 'ArrowRight') go(1)
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="proto-switcher" role="toolbar" aria-label="Variantes del prototipo">
    <button type="button" aria-label="Variante anterior" @click="go(-1)">&#8249;</button>
    <span class="proto-switcher__label">{{ variants[index].name }}</span>
    <button type="button" aria-label="Variante siguiente" @click="go(1)">&#8250;</button>
  </div>
</template>

<style scoped>
.proto-switcher {
  position: fixed;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: #ff2d87;
  color: #fff;
  font: 600 13px/1 system-ui, sans-serif;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35);
}

.proto-switcher button {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  color: inherit;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.proto-switcher button:hover { background: rgba(255, 255, 255, 0.32); }
.proto-switcher button:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

.proto-switcher__label {
  min-width: 150px;
  padding: 0 8px;
  text-align: center;
  white-space: nowrap;
}
</style>
