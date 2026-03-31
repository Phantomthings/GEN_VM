<script setup lang="ts">
import { ref, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import SiteSelector from '@/components/common/SiteSelector.vue'
import DateRangeFilter from '@/components/common/DateRangeFilter.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import { fetchAlarmDates, fetchAlarmData } from '@/api/alarms'

// Extract HH:MM from strings like "0 days 08:30:00" or "08:30:00"
function fmtTime(v: unknown): string {
  if (!v) return '-'
  const m = String(v).match(/(\d{1,2}:\d{2})/)
  return m ? m[1] : String(v)
}

const sites = ref<string[]>([])
const dateRange = ref<Date[] | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const rows = ref<Record<string, unknown>[]>([])

watch(sites, async (s) => {
  if (!s.length) return
  availableDates.value = await fetchAlarmDates(s)
  if (availableDates.value.length) {
    const end = new Date(availableDates.value[availableDates.value.length - 1])
    const start = new Date(end)
    start.setDate(start.getDate() - 30)
    dateRange.value = [start, end]
  }
})

watch(dateRange, async (range) => {
  if (!range || range.length < 2 || !sites.value.length) return
  const start = range[0].toISOString().split('T')[0]
  const end = range[1].toISOString().split('T')[0]

  // Filter available dates within range
  const filtered = availableDates.value.filter(d => d >= start && d <= end)
  if (!filtered.length) {
    rows.value = []
    return
  }

  loading.value = true
  try {
    const data = await fetchAlarmData(sites.value, filtered)
    rows.value = data.rows
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-header"><h1>Alertes</h1></div>

  <div class="filter-bar">
    <SiteSelector v-model="sites" />
    <DateRangeFilter v-model="dateRange" />
  </div>

  <LoadingOverlay v-if="loading" />

  <div class="section" v-else>
    <div v-if="!rows.length" style="color: #94a3b8; padding: 1rem;">
      Aucune alerte trouvee pour la periode selectionnee.
    </div>

    <DataTable v-else :value="rows" stripedRows size="small" paginator :rows="20" sortField="date" :sortOrder="-1">
      <Column field="date" header="Date" sortable />
      <Column field="site" header="Site" sortable />
      <Column header="SOC bas" sortable field="soc_bas">
        <template #body="{ data }"><StatusBadge :alert="data.soc_bas" /></template>
      </Column>
      <Column header="ΔSOC > 8%" sortable field="soc_diff_gt_8">
        <template #body="{ data }"><StatusBadge :alert="data.soc_diff_gt_8" /></template>
      </Column>
      <Column field="soc_diff_time" header="Heure ΔSOC" sortable>
        <template #body="{ data }">{{ fmtTime(data.soc_diff_time) }}</template>
      </Column>
      <Column header="SOC Mgt" sortable field="soc_mgt_missing">
        <template #body="{ data }"><StatusBadge :alert="data.soc_mgt_missing" /></template>
      </Column>
      <Column header="SOC 5h10" field="soc_5h10" sortable>
        <template #body="{ data }">{{ data.soc_5h10 != null ? `${data.soc_5h10}%` : '' }}</template>
      </Column>
      <Column header="Eau KKT" sortable field="water_level_low">
        <template #body="{ data }"><StatusBadge :alert="data.water_level_low" /></template>
      </Column>
      <Column field="water_level_time" header="Heure KKT" sortable>
        <template #body="{ data }">{{ fmtTime(data.water_level_time) }}</template>
      </Column>
      <Column header="EV < 35 kWh" sortable field="energy_ev_low">
        <template #body="{ data }"><StatusBadge :alert="data.energy_ev_low" /></template>
      </Column>
      <Column header="Temp > 28°C" sortable field="temp_over_28">
        <template #body="{ data }"><StatusBadge :alert="data.temp_over_28" /></template>
      </Column>
      <Column field="temp_time" header="Heure temp" sortable>
        <template #body="{ data }">{{ fmtTime(data.temp_time) }}</template>
      </Column>
    </DataTable>
  </div>
</template>
