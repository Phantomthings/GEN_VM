<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const menuItems = [
  {
    label: 'Vue principale',
    icon: 'pi pi-home',
    route: '/',
  },
  {
    label: 'Analyse journalière',
    icon: 'pi pi-calendar',
    items: [
      { label: 'SOC', icon: 'pi pi-bolt', route: '/daily/soc' },
      { label: 'Régulation', icon: 'pi pi-cog', route: '/daily/regu' },
      { label: 'Énergies', icon: 'pi pi-chart-line', route: '/daily/energy' },
      { label: 'Power Limitation', icon: 'pi pi-sliders-v', route: '/daily/power-limitation' },
    ],
  },
  {
    label: 'Analyse multi-journée',
    icon: 'pi pi-calendar-plus',
    items: [
      { label: 'Comparaison', icon: 'pi pi-arrows-h', route: '/multi/comparison' },
      { label: 'Intervalle', icon: 'pi pi-sliders-h', route: '/multi/interval' },
      { label: 'Statistiques', icon: 'pi pi-chart-bar', route: '/multi/stats' },
    ],
  },
  {
    label: 'Alertes',
    icon: 'pi pi-exclamation-triangle',
    route: '/alarms',
  },
  {
    label: 'Signaux',
    icon: 'pi pi-chart-line',
    route: '/signals',
  },
]

function navigate(route: string) {
  router.push(route)
}
</script>

<template>
  <aside class="app-sidebar">
    <div class="sidebar-logo">
      <img src="@/assets/logo.png" alt="Logo" />
    </div>
    <nav class="sidebar-menu" style="padding: 0.5rem 0;">
      <template v-for="item in menuItems" :key="item.label">
        <!-- Simple item (no children) -->
        <div
          v-if="!item.items"
          class="menu-item"
          :class="{ active: $route.path === item.route }"
          @click="navigate(item.route!)"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </div>

        <!-- Group with children -->
        <div v-else class="menu-group">
          <div class="menu-group-header">
            <i :class="item.icon"></i>
            <span>{{ item.label }}</span>
          </div>
          <div
            v-for="child in item.items"
            :key="child.label"
            class="menu-item sub"
            :class="{ active: $route.path === child.route }"
            @click="navigate(child.route!)"
          >
            <i :class="child.icon"></i>
            <span>{{ child.label }}</span>
          </div>
        </div>
      </template>
    </nav>
  </aside>
</template>

<style scoped>
.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 1.25rem;
  cursor: pointer;
  color: #ffffff;
  border-radius: 8px;
  margin: 2px 8px;
  transition: background 0.15s;
  font-size: 0.9rem;
}

.menu-item:hover {
  background: rgba(0, 0, 0, 0.18);
  color: #fff;
}

.menu-item.active {
  background: rgba(0, 0, 0, 0.30);
  color: #fff;
  font-weight: 600;
}

.menu-item.sub {
  padding-left: 2.5rem;
  font-size: 0.85rem;
}

.menu-group-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 1.25rem;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.75rem;
  text-transform: uppercase;
  font-weight: 700;
  margin-top: 0.75rem;
  letter-spacing: 0.05em;
}
</style>
