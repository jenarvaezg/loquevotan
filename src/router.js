import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("./views/HomeView.vue"),
    },
    {
      path: "/votaciones",
      name: "votaciones",
      component: () => import("./views/VotacionesView.vue"),
    },
    {
      path: "/diputados",
      name: "diputados",
      component: () => import("./views/DiputadosView.vue"),
    },
    {
      path: "/votacion/:id",
      name: "votacion",
      component: () => import("./views/VotacionDetail.vue"),
    },
    {
      path: "/diputado/:name",
      name: "diputado",
      component: () => import("./views/DiputadoDetail.vue"),
    },
    {
      path: "/grupos",
      name: "grupos",
      component: () => import("./views/GruposView.vue"),
    },
    {
      path: "/grupo/:grupo",
      name: "grupo",
      component: () => import("./views/GrupoDetail.vue"),
    },
    {
      path: "/comparar",
      name: "comparar",
      component: () => import("./views/ComparadorView.vue"),
    },
    {
      path: "/rankings",
      name: "rankings",
      component: () => import("./views/RankingsView.vue"),
    },
    {
      path: "/widget/:id",
      name: "widget",
      component: () => import("./views/WidgetView.vue"),
    },
    {
      path: "/widget/:scope/:id",
      name: "widget-scoped",
      component: () => import("./views/WidgetView.vue"),
    },
    {
      path: "/afinidad",
      name: "afinidad",
      component: () => import("./views/AffinityDetail.vue"),
    },
    {
      path: "/quiz",
      name: "quiz",
      component: () => import("./views/QuizView.vue"),
    },
    {
      path: "/metodologia",
      name: "metodologia",
      component: () => import("./views/MethodologyView.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("./views/NotFoundView.vue"),
    },
  ],
  scrollBehavior() {
    return { top: 0 };
  },
});

export default router;
