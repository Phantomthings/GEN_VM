<script setup lang="ts">
import DatePicker from 'primevue/datepicker'
import { computed } from 'vue'

const props = defineProps<{
  availableDates?: string[]
}>()

const model = defineModel<Date | null>()

const minDate = computed(() => {
  if (!props.availableDates?.length) return undefined
  return new Date(`${props.availableDates[0]}T12:00:00`)
})

const maxDate = computed(() => {
  if (!props.availableDates?.length) return undefined
  return new Date(`${props.availableDates[props.availableDates.length - 1]}T12:00:00`)
})
</script>

<template>
  <div class="filter-group">
    <label>Date</label>
    <DatePicker
      v-model="model"
      dateFormat="dd/mm/yy"
      :minDate="minDate"
      :maxDate="maxDate"
      showIcon
      style="min-width: 180px"
    />
  </div>
</template>
