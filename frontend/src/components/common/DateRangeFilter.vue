<script setup lang="ts">
import DatePicker from 'primevue/datepicker'

const model = defineModel<Date[] | null>()
</script>

<template>
  <div class="filter-group">
    <label>Période</label>
    <DatePicker
      v-model="model"
      selectionMode="range"
      dateFormat="dd/mm/yy"
      showIcon
      style="min-width: 280px"
      placeholder="Début - Fin"
    />
  </div>
</template>
