<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import HeroSearch from './HeroSearch.vue'
import { useData, storageGet, storageSet } from '../composables/useData'

const { ambitos, currentScopeId, setScope, manifest } = useData()
const route = useRoute()
const menuOpen = ref(false)
const isDark = ref(false)
const scopeMenuOpen = ref(false)
const baseUrl = import.meta.env.BASE_URL

const LINKS = [
  { to: '/votaciones', label: 'Votaciones' },
  { to: '/diputados', label: 'Diputados' },
  { to: '/grupos', label: 'Partidos' },
  { to: '/rankings', label: 'Rankings' },
  { to: '/quiz', label: 'Test de afinidad' },
]

// Brand mark: two rows of seats, a tiny hemicycle.
const MARK = [
  ...Array.from({ length: 9 }, (_, i) => ({ r: 1, a: Math.PI - (i * Math.PI) / 8 })),
  ...Array.from({ length: 5 }, (_, i) => ({ r: 0.5, a: Math.PI - (i * Math.PI) / 4 })),
].map(({ r, a }) => ({ x: r * Math.cos(a), y: -r * Math.sin(a) }))

const currentScope = computed(() => {
  return ambitos.value.find(a => a.id === currentScopeId.value) || ambitos.value[0]
})

const currentScopeWipLabel = computed(() => {
  if (!currentScope.value?.wip) return null
  return currentScope.value.wipLabel || 'Datos en actualización'
})

const lastUpdate = computed(() => {
  if (!manifest.value?.updatedAt) return null
  try {
    // Pipelines emit UTC; older manifests have no offset (same rule as Home).
    const raw = manifest.value.updatedAt
    const hasTimezone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(raw)
    const date = new Date(hasTimezone ? raw : `${raw}Z`)
    return new Intl.DateTimeFormat('es-ES', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Madrid',
    }).format(date)
  } catch (e) {
    return null
  }
})

function initTheme() {
  const saved = storageGet('lqv-theme')
  if (saved) {
    document.documentElement.dataset.theme = saved
  } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.dataset.theme = 'dark'
  }
  isDark.value = document.documentElement.dataset.theme === 'dark'
}

function toggleTheme() {
  const next = isDark.value ? 'light' : 'dark'
  document.documentElement.dataset.theme = next
  storageSet('lqv-theme', next)
  isDark.value = next === 'dark'
}

function isActive(to) {
  return route.path === to || route.path.startsWith(`${to}/`)
}

function selectScope(id) {
  setScope(id)
  scopeMenuOpen.value = false
}

function closeScopeMenu(e) {
  if (!e.target.closest('.scope-dropdown')) {
    scopeMenuOpen.value = false
  }
}

watch(() => route.fullPath, () => { menuOpen.value = false })

onMounted(() => {
  document.addEventListener('click', closeScopeMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', closeScopeMenu)
})

initTheme()
</script>

<template>
  <nav class="nav-bar" aria-label="Navegación principal">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand">
        <svg viewBox="-1.1 -1.1 2.2 1.2" aria-hidden="true">
          <circle v-for="(p, i) in MARK" :key="i" :cx="p.x" :cy="p.y" r="0.17" />
        </svg>
        Lo Que Votan
      </router-link>

      <ul id="nav-links" class="nav-links" :class="{ open: menuOpen }">
        <li v-for="link in LINKS" :key="link.to">
          <router-link :to="link.to" :class="{ active: isActive(link.to) }" :aria-current="isActive(link.to) ? 'page' : undefined">
            {{ link.label }}
          </router-link>
        </li>
        <li class="nav-search">
          <HeroSearch />
        </li>
      </ul>

      <div class="nav-tools">
        <div v-if="ambitos.length > 1" class="scope-dropdown">
          <button
            type="button"
            class="scope-btn"
            :aria-expanded="scopeMenuOpen"
            aria-haspopup="true"
            :aria-label="`Parlamento: ${currentScope?.nombre || 'cargando'}. Cambiar`"
            @click="scopeMenuOpen = !scopeMenuOpen"
          >
            <img :src="`${baseUrl}assets/flags/${currentScope?.id || 'nacional'}.svg`" class="scope-flag" alt="" />
            <span class="scope-info">
              <span class="scope-label">
                {{ currentScope?.nombre || 'Cargando…' }}
                <span v-if="currentScope?.wip" class="scope-wip-badge">En revisión</span>
              </span>
              <span v-if="currentScopeWipLabel" class="scope-sub">{{ currentScopeWipLabel }}</span>
              <span v-else-if="lastUpdate" class="scope-sub">Actualizado el {{ lastUpdate }}</span>
            </span>
            <svg class="scope-chevron" viewBox="0 0 10 6" aria-hidden="true"><path d="M0 0l5 6 5-6z" /></svg>
          </button>

          <div class="scope-menu" :class="{ 'scope-menu--open': scopeMenuOpen }">
            <button
              v-for="a in ambitos"
              :key="a.id"
              type="button"
              class="scope-menu-item"
              :class="{ active: a.id === currentScopeId }"
              :aria-current="a.id === currentScopeId ? 'true' : undefined"
              @click="selectScope(a.id)"
            >
              <img :src="`${baseUrl}assets/flags/${a.id}.svg`" class="scope-flag" alt="" />
              {{ a.nombre }}
              <span v-if="a.wip" class="scope-wip-badge">En revisión</span>
            </button>
          </div>
        </div>

        <button
          type="button"
          class="icon-btn"
          :aria-label="isDark ? 'Usar tema claro' : 'Usar tema oscuro'"
          :title="isDark ? 'Usar tema claro' : 'Usar tema oscuro'"
          @click="toggleTheme"
        >
          <svg v-if="isDark" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="4.5" />
            <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
          </svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" />
          </svg>
        </button>

        <button
          type="button"
          class="icon-btn nav-hamburger"
          :aria-expanded="menuOpen"
          aria-controls="nav-links"
          aria-label="Menú"
          @click="menuOpen = !menuOpen"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path v-if="menuOpen" d="M6 6l12 12M18 6L6 18" />
            <path v-else d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.nav-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--nav-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.nav-inner {
  max-width: var(--container-max);
  height: 100%;
  margin: 0 auto;
  padding: 0 1.25rem;
  display: flex;
  align-items: center;
  gap: 2rem;
}

.nav-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-weight: 800;
  font-stretch: 110%;
  font-size: 1.05rem;
  letter-spacing: -0.01em;
  color: var(--color-text);
  white-space: nowrap;
}
.nav-brand:hover { color: var(--color-text); text-decoration: none; }
.nav-brand svg { width: 30px; fill: currentColor; }

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.4rem;
  flex: 1;
  list-style: none;
}
.nav-links a {
  color: var(--color-muted);
  font-size: 0.95rem;
  font-weight: 500;
  white-space: nowrap;
}
.nav-links a:hover { color: var(--color-text); text-decoration: underline; text-underline-offset: 6px; }
.nav-links a.active {
  color: var(--color-text);
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 6px;
}

.nav-search { margin-left: auto; width: min(260px, 100%); }

.nav-tools { display: flex; align-items: center; gap: 0.5rem; }

.scope-dropdown { position: relative; }
.scope-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}
.scope-btn:hover { border-color: var(--color-border-hover); }
.scope-flag { width: 18px; height: 13px; object-fit: cover; border-radius: 1px; box-shadow: 0 0 0 1px var(--color-border); flex: none; }
.scope-info { display: flex; flex-direction: column; line-height: 1.15; }
.scope-label { font-size: 0.85rem; font-weight: 600; white-space: nowrap; }
.scope-sub { font-size: 0.72rem; color: var(--color-muted); white-space: nowrap; }
.scope-chevron { width: 9px; height: 6px; fill: currentColor; flex: none; }
.scope-wip-badge {
  margin-left: 0.3rem;
  padding: 0 0.35em;
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--color-muted);
}

.scope-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 260px;
  display: none;
  flex-direction: column;
  padding: 0.3rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
}
.scope-menu--open { display: flex; }
.scope-menu-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 0.7rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: none;
  color: var(--color-text);
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
}
.scope-menu-item:hover { background: var(--color-bg); }
.scope-menu-item.active { font-weight: 700; box-shadow: inset 3px 0 0 var(--color-text); }

.icon-btn {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}
.icon-btn:hover { border-color: var(--color-border-hover); }
.icon-btn svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }
.nav-hamburger { display: none; }

@media (max-width: 1100px) {
  .nav-inner { gap: 1.25rem; }
  .nav-links { gap: 1rem; }
  .scope-sub { display: none; }
}

@media (max-width: 960px) {
  .nav-inner { padding: 0 16px; }
  .nav-hamburger { display: grid; }
  .nav-tools { margin-left: auto; }
  .scope-info { display: none; }
  .nav-links {
    position: absolute;
    top: var(--nav-height);
    left: 0;
    right: 0;
    display: none;
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding: 0.5rem 16px 1rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow-lg);
  }
  .nav-links.open { display: flex; }
  .nav-links a { display: block; padding: 0.7rem 0; font-size: 1.05rem; border-bottom: 1px solid var(--color-border); }
  .nav-search { order: -1; width: 100%; margin: 0.25rem 0 0.5rem; }
}
</style>
