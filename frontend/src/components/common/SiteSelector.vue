<script setup lang="ts">
import { computed, watch } from 'vue'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import { useProjectsStore } from '@/stores/projects'

const model = defineModel<string[]>({ default: () => [] })

const projectsStore = useProjectsStore()

const options = computed(() =>
  projectsStore.projects.map(p => ({
    label: p.label,
    value: p.code,
  }))
)

const allCodes = computed(() => options.value.map(o => o.value))

const selectAll = computed({
  get: () => model.value.length === allCodes.value.length && allCodes.value.length > 0,
  set: (val: boolean) => {
    model.value = val ? [...allCodes.value] : []
  },
})

// Initialize with all selected
watch(allCodes, (codes) => {
  if (codes.length > 0 && model.value.length === 0) {
    model.value = [...codes]
  }
}, { immediate: true })
</script>

<template>
  <div class="filter-group">
    <label>Sites</label>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
      <Checkbox v-model="selectAll" :binary="true" />
      <span style="font-size: 0.85rem; color: #64748b;">Tout</span>
      <MultiSelect
        v-model="model"
        :options="options"
        optionLabel="label"
        optionValue="value"
        placeholder="Sites"
        display="chip"
        :filter="true"
        class="site-multiselect"
      />
    </div>
  </div>
</template>

<style scoped>
:deep(.site-multiselect) {
  min-width: 280px;
  max-width: 600px;
}
:deep(.site-multiselect .p-multiselect-label) {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px 8px;
  min-height: 34px;
  height: auto;
}
</style>
