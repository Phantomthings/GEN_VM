<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  subtitle?: string
  color?: 'blue' | 'green' | 'orange' | 'red' | 'purple'
}>()
</script>

<template>
  <div class="kpi-card" :class="color ?? 'blue'">
    <div class="kpi-title">{{ title }}</div>
    <div class="kpi-value">{{ value }}</div>
    <div v-if="subtitle" class="kpi-sub">{{ subtitle }}</div>
  </div>
</template>
