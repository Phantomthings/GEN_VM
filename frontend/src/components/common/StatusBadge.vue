<script setup lang="ts">
defineProps<{
  alert: boolean | null | undefined
}>()
</script>

<template>
  <span v-if="alert === null || alert === undefined"></span>
  <span v-else-if="alert" class="status-alert">
    <i class="pi pi-exclamation-triangle"></i> Alerte
  </span>
  <span v-else class="status-ok">
    <i class="pi pi-check-circle"></i> OK
  </span>
</template>
