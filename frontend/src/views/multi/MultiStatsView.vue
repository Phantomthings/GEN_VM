<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import SiteSelector from '@/components/common/SiteSelector.vue'
import DateRangeFilter from '@/components/common/DateRangeFilter.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import BarChart from '@/components/charts/BarChart.vue'
import { fetchStatsDates, fetchStatsData } from '@/api/multi'
import type { EChartsOption } from 'echarts'

const sites = ref<string[]>([])
const dateRange = ref<Date[] | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const data = ref<Record<string, unknown> | null>(null)

watch(sites, async (s) => {
  if (!s.length) return
  availableDates.value = await fetchStatsDates(s)
  if (availableDates.value.length) {
    const end = new Date(availableDates.value[availableDates.value.length - 1])
    const start = new Date(end)
    start.setDate(start.getDate() - 30)
    dateRange.value = [start, end]
  }
})

watch(dateRange, async (range) => {
  if (!range || range.length < 2 || !sites.value.length) return
  loading.value = true
  try {
    data.value = await fetchStatsData(
      sites.value,
      range[0].toISOString().split('T')[0],
      range[1].toISOString().split('T')[0],
    )
  } finally {
    loading.value = false
  }
})

const gkpi = computed(() => (data.value?.global_kpi as Record<string, unknown>) ?? {})
const perSite = computed(() => (data.value?.per_site as Array<Record<string, unknown>>) ?? [])
const charts = computed(() => (data.value?.charts as Record<string, Array<{ site: string; value: number }>>) ?? {})

function barOption(chartData: Array<{ site: string; value: number }>, title: string, color: string, unit: string): EChartsOption {
  if (!chartData.length) return {}
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const rawValue = point?.value
        const value = typeof rawValue === 'number' ? rawValue : Number(rawValue ?? 0)
        return `${point?.name ?? '-'}: ${value} ${unit}`.trim()
      },
    },
    xAxis: { type: 'category', data: chartData.map(d => d.site), axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', name: unit },
    series: [{
      type: 'bar',
      data: chartData.map(d => d.value),
      itemStyle: { color },
      label: {
        show: true,
        position: 'top',
        formatter: (params) => String(params.value ?? ''),
        fontSize: 10,
      },
    }],
    grid: { left: 60, right: 20, bottom: 80, top: 60 },
  }
}

function fmt(v: unknown, digits = 2): string {
  if (v == null) return '-'
  return Number(v).toFixed(digits)
}
</script>

<template>
  <div class="page-header"><h1>Statistiques générales</h1></div>

  <div class="filter-bar">
    <SiteSelector v-model="sites" />
    <DateRangeFilter v-model="dateRange" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">

    <!-- Global KPIs -->
    <div class="kpi-grid">
      <KpiCard
        title="Énergie EV totale (tous sites)"
        :value="`${Number(gkpi.total_ev_kwh ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} kWh`"
        color="blue"
      />
      <KpiCard
        title="Heures de charge cumulées"
        :value="`${fmt(gkpi.total_charge_hours, 1)} h`"
        :subtitle="gkpi.global_avg_power != null ? `P moyenne globale : ${fmt(gkpi.global_avg_power, 1)} kW` : undefined"
        color="purple"
      />
      <KpiCard
        title="Pmax EV"
        :value="`${fmt(gkpi.max_ev_kw, 0)} kW`"
        :subtitle="gkpi.max_ev_site ? `Site : ${gkpi.max_ev_site}` : undefined"
        color="orange"
      />
      <KpiCard
        title="Site le + énergivore"
        :value="String(gkpi.top_energy_site ?? '-')"
        :subtitle="gkpi.top_energy_kwh != null ? `${Number(gkpi.top_energy_kwh).toFixed(0)} kWh` : undefined"
        color="red"
      />
      <KpiCard
        title="Top cycles / jour"
        :value="String(gkpi.top_cycles_site ?? '-')"
        :subtitle="gkpi.top_cycles_per_day != null ? `${Number(gkpi.top_cycles_per_day).toFixed(3)} cyc/j` : undefined"
        color="green"
      />
    </div>

    <!-- KPI par site — cards -->
    <div class="section">
      <h3 class="section-title">KPI par site</h3>
      <div class="kpi-grid">
        <div v-for="s in perSite" :key="String(s.site)" class="site-kpi-card">
          <div class="site-kpi-name">{{ s.site }}</div>
          <div class="site-kpi-value">{{ Number(s.total_ev_kwh ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 }) }} kWh</div>
          <div class="site-kpi-row">
            <span>Charge <strong>{{ fmt(s.charge_total_hr, 1) }} h</strong></span>
            <span>P moy <strong>{{ s.pmoy_ev_kw != null ? fmt(s.pmoy_ev_kw) + ' kW' : '-' }}</strong></span>
            <span>P max <strong>{{ fmt(s.pmax_ev_kw, 0) }} kW</strong></span>
          </div>
          <div class="site-kpi-row">
            <span>Cyc/j <strong>{{ fmt(s.cycles_per_day, 3) }}</strong></span>
            <span>Cyc total <strong>{{ fmt(s.cycles_total) }}</strong></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Table KPI Charge EV -->
    <div class="section">
      <h3 class="section-title">KPI · Charge EV</h3>
      <DataTable :value="perSite" size="small" stripedRows scrollable>
        <Column field="site" header="Site" frozen sortable />
        <Column field="total_ev_kwh" header="Énergie EV (kWh)" sortable>
          <template #body="{ data }">{{ fmt(data.total_ev_kwh) }}</template>
        </Column>
        <Column field="avg_energy_per_day" header="Énergie moy. (kWh/j)" sortable>
          <template #body="{ data }">{{ fmt(data.avg_energy_per_day) }}</template>
        </Column>
        <Column field="pmoy_ev_kw" header="P moy. EV (kW/j)" sortable>
          <template #body="{ data }">{{ fmt(data.pmoy_ev_kw) }}</template>
        </Column>
        <Column field="pmax_ev_kw" header="P max EV (kW)" sortable>
          <template #body="{ data }">{{ fmt(data.pmax_ev_kw) }}</template>
        </Column>
        <Column field="charge_total_hr" header="Heures charge EV" sortable>
          <template #body="{ data }">{{ fmt(data.charge_total_hr) }}</template>
        </Column>
        <Column field="charge_batt_hr" header="Charge depuis batterie (h)" sortable>
          <template #body="{ data }">{{ fmt(data.charge_batt_hr) }}</template>
        </Column>
        <Column field="charge_grid_hr" header="Charge depuis réseau (h)" sortable>
          <template #body="{ data }">{{ fmt(data.charge_grid_hr) }}</template>
        </Column>
        <Column field="days_with_data" header="Jours avec données" sortable />
      </DataTable>
    </div>

    <!-- Table KPI Batteries -->
    <div class="section">
      <h3 class="section-title">KPI · Batteries</h3>
      <DataTable :value="perSite" size="small" stripedRows>
        <Column field="site" header="Site" sortable />
        <Column field="charge_batt_hr" header="Heures décharge (h)" sortable>
          <template #body="{ data }">{{ fmt(data.charge_batt_hr) }}</template>
        </Column>
        <Column field="batt_charge_hours" header="Heures charge (h)" sortable>
          <template #body="{ data }">{{ fmt(data.batt_charge_hours) }}</template>
        </Column>
        <Column field="cycles_total" header="Cycles totaux" sortable>
          <template #body="{ data }">{{ fmt(data.cycles_total) }}</template>
        </Column>
        <Column field="cycles_per_day" header="Cycles moyens / jour" sortable>
          <template #body="{ data }">{{ fmt(data.cycles_per_day, 3) }}</template>
        </Column>
      </DataTable>
    </div>

    <!-- Charts -->
    <div class="two-columns" v-if="charts.cycles_by_site?.length">
      <div class="section">
        <BarChart :option="barOption(charts.cycles_by_site, 'Cycles batterie — total par site', '#8b5cf6', '')" height="320px" />
      </div>
      <div class="section">
        <BarChart :option="barOption(charts.energy_by_site ?? [], 'Énergie EV — total par site', '#3b82f6', 'kWh')" height="320px" />
      </div>
    </div>

  </template>
</template>
