<script setup lang="ts">
import { ref, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import SiteSelector from '@/components/common/SiteSelector.vue'
import DateFilter from '@/components/common/DateFilter.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import { fetchComparisonDates, fetchComparisonData } from '@/api/multi'
import { fmtNum } from '@/utils/format'

const sites = ref<string[]>([])
const selectedDate = ref<Date | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const rows = ref<Record<string, unknown>[]>([])

watch(sites, async (s) => {
  if (!s.length) return
  availableDates.value = await fetchComparisonDates(s)
  if (availableDates.value.length) {
    selectedDate.value = new Date(availableDates.value[availableDates.value.length - 1])
  }
})

watch(selectedDate, async (d) => {
  if (!d || !sites.value.length) return
  loading.value = true
  try {
    const data = await fetchComparisonData(sites.value, d.toISOString().split('T')[0])
    rows.value = data.rows
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-header"><h1>Comparaison - Journalière</h1></div>

  <div class="filter-bar">
    <SiteSelector v-model="sites" />
    <DateFilter v-model="selectedDate" :availableDates="availableDates" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="rows.length">
    <!-- Batteries -->
    <div class="section">
      <h3 class="section-title">Batteries</h3>

      <h4 style="margin: 0.5rem 0 0.25rem">Indicateurs du SOC Management en mode RUN (2)</h4>
      <DataTable :value="rows" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="run_avg_start_time" header="Heure moy. passage RUN" sortable />
        <Column field="run_avg_soc_start_pct" header="SOC moyen début RUN (%)" sortable>
          <template #body="{ data }">{{ fmtNum(data.run_avg_soc_start_pct) }}</template>
        </Column>
        <Column field="run_avg_duration_min" header="Durée moyenne RUN→0 (min)" sortable>
          <template #body="{ data }">{{ fmtNum(data.run_avg_duration_min) }}</template>
        </Column>
      </DataTable>

      <h4 style="margin: 1rem 0 0.25rem">Moyenne du temps par mode - Batterie (%)</h4>
      <DataTable :value="rows" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="soc_disable_pct" header="Disable (0)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_disable_pct) }}</template>
        </Column>
        <Column field="soc_run1_pct" header="RUN+EV (1)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_run1_pct) }}</template>
        </Column>
        <Column field="soc_run2_pct" header="RUN (2)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_run2_pct) }}</template>
        </Column>
        <Column field="soc_standby_pct" header="Stand-by (3)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_standby_pct) }}</template>
        </Column>
        <Column field="soc_enable_pct" header="Enable (4)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_enable_pct) }}</template>
        </Column>
      </DataTable>
    </div>

    <!-- Regulation -->
    <div class="section">
      <h3 class="section-title">Régulation</h3>

      <h4 style="margin: 0.5rem 0 0.25rem">Moyenne du temps par mode - Régulation (%)</h4>
      <DataTable :value="rows" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="pm_off_pct" header="OFF (1)" sortable>
          <template #body="{ data }">{{ fmtNum(data.pm_off_pct) }}</template>
        </Column>
        <Column field="pm_standby_pct" header="Stand-by (2)" sortable>
          <template #body="{ data }">{{ fmtNum(data.pm_standby_pct) }}</template>
        </Column>
        <Column field="pm_ac_pct" header="AC (3)" sortable>
          <template #body="{ data }">{{ fmtNum(data.pm_ac_pct) }}</template>
        </Column>
        <Column field="pm_batt_pct" header="Batterie (4)" sortable>
          <template #body="{ data }">{{ fmtNum(data.pm_batt_pct) }}</template>
        </Column>
      </DataTable>

      <h4 style="margin: 1rem 0 0.25rem">Transitions 3 → 4</h4>
      <DataTable :value="rows" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="transitions_34_count" header="Nbr transitions 3→4" sortable />
      </DataTable>
    </div>

    <!-- Energy -->
    <div class="section">
      <h3 class="section-title">Énergies</h3>

      <h4 style="margin: 0.5rem 0 0.25rem">Indicateurs d'énergie</h4>
      <DataTable :value="rows" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="energy_ev_kwh" header="Énergie EV (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energy_ev_kwh) }}</template>
        </Column>
        <Column field="energy_aux_kwh" header="Énergie aux (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energy_aux_kwh) }}</template>
        </Column>
        <Column field="energy_charge_kwh" header="Énergie charge (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energy_charge_kwh) }}</template>
        </Column>
        <Column field="energy_decharge_kwh" header="Énergie décharge (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energy_decharge_kwh) }}</template>
        </Column>
      </DataTable>

      <h4 style="margin: 1rem 0 0.25rem">Indicateur puissance EV max</h4>
      <DataTable :value="rows" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="max_ev_kw" header="Puissance EV max (kW)" sortable>
          <template #body="{ data }">{{ fmtNum(data.max_ev_kw) }}</template>
        </Column>
        <Column field="ev_peak_time" header="Heure EV max" sortable />
      </DataTable>
    </div>
  </template>
</template>
