<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import HeroSearch from './HeroSearch.vue'
import { useData } from '../composables/useData'

const { ambitos, currentScopeId, setScope } = useData()
const route = useRoute()
const menuOpen = ref(false)
const isDark = ref(false)

function initTheme() {
  const saved = localStorage.getItem('lqv-theme')
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
  localStorage.setItem('lqv-theme', next)
  isDark.value = next === 'dark'
}

const themeIcon = computed(() => isDark.value ? '\u2600\uFE0F' : '\uD83C\uDF19')

function closeMenu() {
  menuOpen.value = false
}

function handleScopeChange(e) {
  setScope(e.target.value)
}

initTheme()
</script>

<template>
  <nav class="nav-bar">
    <div class="nav-inner">
      <div class="nav-left">
        <router-link to="/" class="nav-brand" @click="closeMenu">Lo Que Votan</router-link>
        <select 
          v-if="ambitos.length > 1"
          class="scope-select" 
          :value="currentScopeId" 
          @change="handleScopeChange"
          aria-label="Cambiar ámbito"
        >
          <option v-for="a in ambitos" :key="a.id" :value="a.id">
            {{ a.id === 'nacional' ? '🇪🇸' : '🚩' }} {{ a.nombre }}
          </option>
        </select>
      </div>
      <button class="nav-hamburger" aria-label="Menu" @click="menuOpen = !menuOpen">
        &#9776;
      </button>
      <ul class="nav-links" :class="{ open: menuOpen }">
        <li>
          <router-link
            to="/votaciones"
            :class="{ active: route.path === '/votaciones' }"
            @click="closeMenu"
          >
            Votaciones
          </router-link>
        </li>
        <li>
          <router-link
            to="/diputados"
            :class="{ active: route.path === '/diputados' }"
            @click="closeMenu"
          >
            Diputados
          </router-link>
        </li>
        <li>
          <router-link
            to="/grupos"
            :class="{ active: route.path === '/grupos' }"
            @click="closeMenu"
          >
            Partidos
          </router-link>
        </li>
      </ul>
      <div v-if="route.path !== '/'" class="nav-search">
        <HeroSearch />
      </div>
      <button
        class="theme-toggle"
        aria-label="Cambiar tema"
        title="Cambiar tema"
        @click="toggleTheme"
      >
        {{ themeIcon }}
      </button>
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
  backdrop-filter: blur(8px);
  background: rgba(255,255,255,0.85);
}

[data-theme="dark"] .nav-bar {
  background: rgba(30,41,59,0.85);
}

.nav-inner {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 0 1.25rem;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.scope-select {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.2rem 0.4rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
  outline: none;
  max-width: 150px;
  text-overflow: ellipsis;
}

.scope-select:hover {
  border-color: var(--color-primary);
}

.nav-brand {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text);
  text-decoration: none;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.nav-brand:hover { color: var(--color-primary); text-decoration: none; }

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  list-style: none;
}

.nav-links a {
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}

.nav-links a:hover,
.nav-links a.active {
  background: var(--color-primary-light);
  color: var(--color-primary);
  text-decoration: none;
}

.theme-toggle {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.4rem 0.6rem;
  cursor: pointer;
  font-size: 1.1rem;
  line-height: 1;
  color: var(--color-text);
  transition: border-color 0.15s;
}

.theme-toggle:hover { border-color: var(--color-border-hover); }

.nav-search {
  flex: 1;
  max-width: 300px;
}

.nav-search :deep(.hero-search-wrap) {
  max-width: 100%;
  margin: 0;
}

.nav-search :deep(.hero-search) {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 0.45rem 0.75rem 0.45rem 2.25rem;
  font-size: 0.85rem;
  border-radius: var(--radius-sm);
}

.nav-search :deep(.hero-search::placeholder) {
  color: var(--color-muted);
}

.nav-search :deep(.hero-search:focus) {
  border-color: var(--color-primary);
  background: var(--color-bg);
}

.nav-search :deep(.hero-search-icon) {
  font-size: 0.9rem;
  left: 0.7rem;
}

.nav-hamburger {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.4rem;
  color: var(--color-text);
  font-size: 1.5rem;
  line-height: 1;
}

@media (max-width: 768px) {
  .nav-search { display: none; }
  .nav-hamburger { display: block; }
  .nav-links {
    display: none;
    position: absolute;
    top: var(--nav-height);
    left: 0;
    right: 0;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow-md);
    flex-direction: column;
    padding: 0.5rem 0;
    z-index: 99;
  }
  .nav-links.open { display: flex; }
  .nav-links a { padding: 0.75rem 1.25rem; width: 100%; }
}
</style>
