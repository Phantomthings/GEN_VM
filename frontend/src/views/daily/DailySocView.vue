<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import DateFilter from '@/components/common/DateFilter.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import LineChart from '@/components/charts/LineChart.vue'
import { fetchSocDates, fetchSocData } from '@/api/daily'
import { useFiltersStore } from '@/stores/filters'
import type { EChartsOption } from 'echarts'
import { fmtNum } from '@/utils/format'

const filters = useFiltersStore()

const project = ref(filters.dailyProject ?? '')
const selectedDate = ref<Date | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const data = ref<Record<string, unknown> | null>(null)
let requestId = 0

watch(() => filters.dailyProject, (p) => {
  if (p && p !== project.value) project.value = p
})

watch(() => filters.dailyDate, (d) => {
  if (!d) return
  const next = new Date(`${d}T12:00:00`)
  if (!selectedDate.value || selectedDate.value.toISOString().slice(0, 10) !== d) selectedDate.value = next
})

// Load dates when project changes
watch(project, async (p) => {
  if (!p) return
  filters.setDailyProject(p)
  const currentRequest = ++requestId
  const dates = await fetchSocDates(p)
  if (currentRequest !== requestId) return
  availableDates.value = dates
  selectedDate.value = filters.resolveDailyDate(dates)
}, { immediate: true })

// Load data when date changes
watch(selectedDate, async (d) => {
  if (!d || !project.value) return
  const dateStr = d.toISOString().split('T')[0]
  filters.setDailyDate(dateStr)
  const currentRequest = ++requestId
  loading.value = true
  try {
    const payload = await fetchSocData(project.value, dateStr)
    if (currentRequest !== requestId) return
    data.value = payload
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
})

// SOC chart option
const socChartOption = computed<EChartsOption>(() => {
  const chart = (data.value?.soc_chart as Array<{ time: string; soc: number }>) ?? []
  if (!chart.length) return {}
  return {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: chart.map(p => p.time),
      axisLabel: {
        formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v,
        interval: 59,
      },
    },
    yAxis: { type: 'value', name: 'SOC (%)', min: 0, max: 100 },
    series: [{
      type: 'line',
      data: chart.map(p => p.soc),
      smooth: true,
      lineStyle: { color: '#1f77b4', width: 2 },
      itemStyle: { color: '#1f77b4' },
      showSymbol: false,
    }],
    grid: { left: 60, right: 20, bottom: 80, top: 40 },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  }
})

function fmtMinutes(m: number): string {
  const h = Math.floor(m / 60)
  const mn = Math.round(m % 60)
  return h > 0 ? `${h}h ${String(mn).padStart(2, '0')}min` : `${mn}min`
}
</script>

<template>
  <div class="page-header">
    <h1>Analyse journaliere - Batteries</h1>
  </div>

  <div class="filter-bar">
    <ProjectSelector v-model="project" />
    <DateFilter v-model="selectedDate" :availableDates="availableDates" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">
    <!-- SOC Chart -->
    <div class="section" v-if="(data.soc_chart as unknown[])?.length">
      <h3 class="section-title">Evolution du SOC % sur la journee</h3>
      <LineChart :option="socChartOption" height="400px" />
    </div>

    <!-- KPIs -->
    <div class="kpi-grid">
      <KpiCard
        title="Delta SOC decharge (cum.)"
        :value="`${(data.kpi as Record<string, unknown>)?.delta_soc_cum ?? '-'} %`"
        color="blue"
      />
      <KpiCard
        title="Energie de decharge"
        :value="`${(data.kpi as Record<string, unknown>)?.discharge_kwh ?? '-'} kWh`"
        color="green"
      />
    </div>

    <!-- Energie theorique vs reelle -->
    <div class="section">
      <h3 class="section-title">Analyse energetique theorique vs reelle</h3>
      <div class="kpi-grid">
        <KpiCard
          title="Energie nominale constructeur"
          :value="`${(data.energie_analysis as Record<string,unknown>)?.energie_nominale_constructeur ?? 745.6} kWh`"
          color="blue"
        />
        <KpiCard
          title="SOH (State of Health)"
          :value="(data.energie_analysis as Record<string,unknown>)?.soh_jour != null
            ? `${Number((data.energie_analysis as Record<string,unknown>).soh_jour).toFixed(2)} %`
            : '-'"
          color="orange"
        />
        <KpiCard
          title="Energie nominale theorique corrigee"
          :value="(data.energie_analysis as Record<string,unknown>)?.energie_nominale_theorique != null
            ? `${(data.energie_analysis as Record<string,unknown>).energie_nominale_theorique} kWh`
            : '-'"
          color="green"
        />
        <KpiCard
          title="Energie theorique dechargee"
          :value="(data.energie_analysis as Record<string,unknown>)?.energie_theorique_dechargee != null
            ? `${(data.energie_analysis as Record<string,unknown>).energie_theorique_dechargee} kWh`
            : '-'"
          color="purple"
        />
      </div>

      <template v-if="(data.energie_analysis as Record<string,unknown>)?.energie_theorique_dechargee != null
                   && (data.energie_analysis as Record<string,unknown>)?.energie_reelle != null">
        <h4 style="margin:1rem 0 0.5rem; color:#94a3b8">Comparaison energie reelle vs theorique</h4>
        <div class="kpi-grid">
          <KpiCard
            title="Energie reelle dechargee"
            :value="`${(data.energie_analysis as Record<string,unknown>).energie_reelle} kWh`"
            color="green"
          />
          <KpiCard
            title="Energie theorique dechargee"
            :value="`${(data.energie_analysis as Record<string,unknown>).energie_theorique_dechargee} kWh`"
            color="blue"
          />
          <KpiCard
            title="Ecart (reelle - theorique)"
            :value="(data.energie_analysis as Record<string,unknown>)?.ecart_kwh != null
              ? `${(data.energie_analysis as Record<string,unknown>).ecart_kwh} kWh`
              : '-'"
            :subtitle="(data.energie_analysis as Record<string,unknown>)?.ecart_pct != null
              ? `${Number((data.energie_analysis as Record<string,unknown>).ecart_pct) > 0 ? '+' : ''}${(data.energie_analysis as Record<string,unknown>).ecart_pct}%`
              : ''"
            :color="(data.energie_analysis as Record<string,unknown>)?.ecart_kwh != null && Math.abs(Number((data.energie_analysis as Record<string,unknown>).ecart_kwh)) < Number((data.energie_analysis as Record<string,unknown>).energie_theorique_dechargee) * 0.1 ? 'green' : 'red'"
          />
          <KpiCard
            title="Ratio energetique"
            :value="(data.energie_analysis as Record<string,unknown>)?.ratio_energie != null
              ? `${(data.energie_analysis as Record<string,unknown>).ratio_energie} %`
              : '-'"
            subtitle="reelle / theorique"
            color="orange"
          />
        </div>
      </template>
      <p v-else-if="(data.energie_analysis as Record<string,unknown>)?.soh_jour == null"
         style="color:#64748b; font-style:italic">
        SOH non disponible pour cette journee.
      </p>
    </div>

    <!-- SOC Management Duration -->
    <div class="section" v-if="(data.resume as unknown[])?.length">
      <h3 class="section-title">Duree SOC Management</h3>
      <div class="kpi-grid">
        <KpiCard
          v-for="r in (data.resume as Array<Record<string, unknown>>)"
          :key="String(r.soc_state)"
          :title="String(r.label)"
          :value="fmtMinutes(Number(r.minutes))"
          :subtitle="`${Number(r.pourcentage).toFixed(2)}% du temps`"
        />
      </div>
    </div>

    <!-- RUN Segments -->
    <div class="section" v-if="(data.runs as unknown[])?.length">
      <h3 class="section-title">Segments RUN (date + heure)</h3>
      <DataTable :value="(data.runs as Record<string, unknown>[])" stripedRows size="small">
        <Column field="start_time" header="Debut" sortable />
        <Column field="end_time" header="Fin" sortable />
        <Column field="soc_debut" header="SOC debut (%)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_debut) }}</template>
        </Column>
        <Column field="soc_fin" header="SOC fin (%)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_fin) }}</template>
        </Column>
      </DataTable>
    </div>

    <!-- Battery Temp -->
    <div class="section" v-if="(data.batt_temp as Record<string, unknown>)?.min_c != null">
      <h3 class="section-title">Data batteries</h3>
      <div class="kpi-grid">
        <KpiCard
          title="Min Temp (°C)"
          :value="String(Number((data.batt_temp as Record<string, unknown>).min_c).toFixed(2))"
          :subtitle="String((data.batt_temp as Record<string, unknown>).min_time ?? '')"
          color="blue"
        />
        <KpiCard
          title="Max Temp (°C)"
          :value="String(Number((data.batt_temp as Record<string, unknown>).max_c).toFixed(2))"
          :subtitle="String((data.batt_temp as Record<string, unknown>).max_time ?? '')"
          color="red"
        />
        <KpiCard
          title="Avg Temp (°C)"
          :value="String(Number((data.batt_temp as Record<string, unknown>).avg_c).toFixed(2))"
          color="orange"
        />
      </div>
    </div>

    <!-- Full SOC History -->
    <div class="section" v-if="(data.hist_soc as unknown[])?.length">
      <h3 class="section-title">Historique complet des etats SOC</h3>
      <DataTable :value="(data.hist_soc as Record<string, unknown>[])" stripedRows size="small" scrollable scrollHeight="400px">
        <Column field="start_time" header="Debut" sortable />
        <Column field="end_time" header="Fin" sortable />
        <Column field="soc_state" header="Etat" sortable />
        <Column field="delta_time_min" header="Duree (min)" sortable>
          <template #body="{ data }">{{ fmtNum(data.delta_time_min) }}</template>
        </Column>
        <Column field="soc_debut" header="SOC debut (%)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_debut) }}</template>
        </Column>
        <Column field="soc_fin" header="SOC fin (%)" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_fin) }}</template>
        </Column>
        <Column field="delta_soc" header="Delta SOC" sortable>
          <template #body="{ data }">{{ fmtNum(data.delta_soc) }}</template>
        </Column>
        <Column field="energie_pdc_kwh" header="E PDC (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energie_pdc_kwh) }}</template>
        </Column>
        <Column field="energie_ev_kwh" header="E EV (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energie_ev_kwh) }}</template>
        </Column>
      </DataTable>
    </div>
  </template>
</template>
