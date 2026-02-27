import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
    { path: '/votaciones', name: 'votaciones', component: () => import('./views/VotacionesView.vue') },
    { path: '/diputados', name: 'diputados', component: () => import('./views/DiputadosView.vue') },
    { path: '/votacion/:idx', name: 'votacion', component: () => import('./views/VotacionDetail.vue') },
    { path: '/diputado/:name', name: 'diputado', component: () => import('./views/DiputadoDetail.vue') },
    { path: '/grupos', name: 'grupos', component: () => import('./views/GruposView.vue') },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
