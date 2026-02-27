<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

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

initTheme()
</script>

<template>
  <nav class="nav-bar">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand" @click="closeMenu">Lo Que Votan</router-link>
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
