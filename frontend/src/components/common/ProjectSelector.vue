<script setup lang="ts">
import { computed } from 'vue'
import Select from 'primevue/select'
import { useProjectsStore } from '@/stores/projects'

const model = defineModel<string>()

const projectsStore = useProjectsStore()

const options = computed(() =>
  projectsStore.projects.map(p => ({
    label: p.label,
    value: p.code,
  }))
)
</script>

<template>
  <div class="filter-group">
    <label>Site</label>
    <Select
      v-model="model"
      :options="options"
      optionLabel="label"
      optionValue="value"
      placeholder="Choisir un site"
      style="min-width: 220px"
    />
  </div>
</template>
