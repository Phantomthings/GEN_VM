import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { title: 'Vue principale' },
    },
    {
      path: '/daily/soc',
      name: 'daily-soc',
      component: () => import('@/views/daily/DailySocView.vue'),
      meta: { title: 'Analyse SOC' },
    },
    {
      path: '/daily/regu',
      name: 'daily-regu',
      component: () => import('@/views/daily/DailyReguView.vue'),
      meta: { title: 'Analyse Régulation' },
    },
    {
      path: '/daily/energy',
      name: 'daily-energy',
      component: () => import('@/views/daily/DailyEnergyView.vue'),
      meta: { title: 'Analyse Énergie' },
    },
    {
      path: '/daily/power-limitation',
      name: 'daily-power-limitation',
      component: () => import('@/views/daily/DailyPowerLimitationView.vue'),
      meta: { title: 'Power Limitation' },
    },
    {
      path: '/multi/comparison',
      name: 'multi-comparison',
      component: () => import('@/views/multi/MultiComparisonView.vue'),
      meta: { title: 'Comparaison' },
    },
    {
      path: '/multi/interval',
      name: 'multi-interval',
      component: () => import('@/views/multi/MultiIntervalView.vue'),
      meta: { title: 'Intervalle' },
    },
    {
      path: '/multi/stats',
      name: 'multi-stats',
      component: () => import('@/views/multi/MultiStatsView.vue'),
      meta: { title: 'Statistiques' },
    },
    {
      path: '/alarms',
      name: 'alarms',
      component: () => import('@/views/AlarmsView.vue'),
      meta: { title: 'Alertes' },
    },
    {
      path: '/signals',
      name: 'signals',
      component: () => import('@/views/SignalsView.vue'),
      meta: { title: 'Signaux' },
    },
  ],
})

export default router
