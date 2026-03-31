<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import DateFilter from '@/components/common/DateFilter.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import PieChart from '@/components/charts/PieChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import HeatmapChart from '@/components/charts/HeatmapChart.vue'
import ScatterChart from '@/components/charts/ScatterChart.vue'
import { fetchReguDates, fetchReguData } from '@/api/daily'
import { useFiltersStore } from '@/stores/filters'
import type { EChartsOption } from 'echarts'
import { fmtNum } from '@/utils/format'
import { REG_MODE_COLORS, REG_MODE_LABELS } from '@/utils/modeColors'

const filters = useFiltersStore()
const project = ref(filters.dailyProject ?? '')
const selectedDate = ref<Date | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const data = ref<Record<string, unknown> | null>(null)

watch(project, async (p) => {
  if (!p) return
  filters.setDailyProject(p)
  availableDates.value = await fetchReguDates(p)
  selectedDate.value = filters.resolveDailyDate(availableDates.value)
}, { immediate: true })

watch(selectedDate, async (d) => {
  if (!d || !project.value) return
  const dateStr = d.toISOString().split('T')[0]
  filters.setDailyDate(dateStr)
  loading.value = true
  try {
    data.value = await fetchReguData(project.value, dateStr)
  } finally {
    loading.value = false
  }
})

const modeColors = REG_MODE_COLORS
const modeLabels = REG_MODE_LABELS

const pieOption = computed<EChartsOption>(() => {
  const resume = (data.value?.resume as Array<{ label: string; pct: number; mode: number }>) ?? []
  if (!resume.length) return {}
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    series: [{
      type: 'pie',
      radius: ['35%', '70%'],
      data: resume.map(r => ({
        name: r.label,
        value: r.pct,
        itemStyle: { color: modeColors[r.mode] ?? '#888' },
      })),
    }],
  }
})

const timelineChartOption = computed<EChartsOption>(() => {
  const hist = (data.value?.hist as Array<Record<string, unknown>>) ?? []
  const segments = hist.filter(h => h.start_time && h.end_time && h.mode != null)
  if (!segments.length) return {}

  const presentModes = [...new Set(segments.map(h => h.mode as number))].sort((a, b) => a - b)

  // Convert "2024-01-15 10:30:00" -> "2024-01-15T10:30:00" for ECharts time axis
  const fixTime = (t: string) => t?.replace(' ', 'T') ?? t

  const series = presentModes.map(mode => {
    const modeSegs = segments.filter(h => (h.mode as number) === mode)
    const pts: [string, number | null][] = []
    for (const seg of modeSegs) {
      pts.push([fixTime(seg.start_time as string), mode])
      pts.push([fixTime(seg.end_time as string), mode])
      pts.push([fixTime(seg.end_time as string), null])
    }
    return {
      type: 'line' as const,
      name: modeLabels[mode] ?? `Mode ${mode}`,
      data: pts,
      lineStyle: { color: modeColors[mode] ?? '#888', width: 12 },
      itemStyle: { color: modeColors[mode] ?? '#888' },
      showSymbol: false,
      connectNulls: false,
    }
  })

  const dayStr = (segments[0].start_time as string).split(' ')[0]

  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'line' } },
    legend: {
      top: 0,
      data: presentModes.map(m => ({ name: modeLabels[m] ?? `Mode ${m}`, itemStyle: { color: modeColors[m] ?? '#888' } })),
      orient: 'horizontal',
    },
    xAxis: {
      type: 'time',
      min: `${dayStr}T00:00:00`,
      max: `${dayStr}T23:59:59`,
      axisLabel: { formatter: '{HH}:{mm}' },
      name: 'Heure',
    },
    yAxis: {
      type: 'value',
      name: 'PlantRunMode',
      min: Math.min(...presentModes) - 0.5,
      max: Math.max(...presentModes) + 0.5,
      interval: 1,
      axisLabel: { formatter: (val: number) => Number.isInteger(val) ? (modeLabels[val] ?? String(val)) : '' },
    },
    series,
    grid: { left: 130, right: 20, bottom: 40, top: 50 },
  }
})

const heatmapOption = computed<EChartsOption>(() => {
  const hm = (data.value?.heatmap as Array<{ hour: number; pct: number }>) ?? []
  if (!hm.length) return {}
  return {
    tooltip: {
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const values = Array.isArray(point?.data) ? point.data : []
        return `${values[0] ?? '-'}h: ${values[2] ?? '-'}%`
      },
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 24 }, (_, i) => String(i)),
      name: 'Heure',
    },
    yAxis: { type: 'category', data: ['Mode 4'], show: false },
    visualMap: { min: 0, max: 100, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{
      type: 'heatmap',
      data: hm.map(h => [h.hour, 0, h.pct]),
      label: {
        show: true,
        formatter: (params) => {
          const values = Array.isArray(params.data) ? params.data : []
          return `${values[2] ?? '-'}%`
        },
        fontSize: 10,
      },
    }],
    grid: { left: 60, right: 40, top: 20, bottom: 60, height: 60 },
  }
})

const scatterOption = computed<EChartsOption>(() => {
  const trx = (data.value?.transitions as Array<{ temp_c: number | null; duration_min: number | null }>) ?? []
  const valid = trx.filter(t => t.temp_c != null && t.duration_min != null)
  if (!valid.length) return {}
  return {
    title: { text: 'Corrélation température ↔ durée 3→4', left: 'center', textStyle: { fontSize: 13 } },
    tooltip: {
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const values = Array.isArray(point?.data) ? point.data : []
        return `Temp: ${values[0] ?? '-'}°C, Durée: ${values[1] ?? '-'} min`
      },
    },
    xAxis: { type: 'value', name: 'Température (°C)' },
    yAxis: { type: 'value', name: 'Durée (min)' },
    series: [{
      type: 'scatter',
      data: valid.map(t => [t.temp_c, t.duration_min]),
      symbolSize: 10,
      itemStyle: { color: '#3b82f6' },
    }],
    grid: { left: 60, right: 20, bottom: 50, top: 50 },
  }
})
</script>

<template>
  <div class="page-header"><h1>Analyse journaliere - Regulation</h1></div>

  <div class="filter-bar">
    <ProjectSelector v-model="project" />
    <DateFilter v-model="selectedDate" :availableDates="availableDates" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">
    <!-- Mode distribution -->
    <div class="section" v-if="(data.resume as unknown[])?.length">
      <h3 class="section-title">Répartition du temps par mode</h3>
      <div class="two-columns">
        <PieChart :option="pieOption" height="300px" />
        <DataTable :value="(data.resume as Record<string, unknown>[])" size="small" stripedRows>
          <Column field="label" header="Mode" sortable />
          <Column field="minutes" header="Minutes" sortable>
            <template #body="{ data }">{{ fmtNum(data.minutes) }}</template>
          </Column>
          <Column field="pct" header="%" sortable>
            <template #body="{ data }">{{ fmtNum(data.pct) }}</template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- Timeline PlantRunMode (visual chart) -->
    <div class="section" v-if="(data.hist as unknown[])?.length">
      <h3 class="section-title">Timeline PlantRunMode</h3>
      <LineChart :option="timelineChartOption" height="260px" />
    </div>

    <!-- Heatmap Mode 4 -->
    <div class="section" v-if="(data.heatmap as unknown[])?.length">
      <h3 class="section-title">Mode 4 (Batterie) - % du temps par heure</h3>
      <HeatmapChart :option="heatmapOption" height="180px" />
      <p style="font-size: 0.8rem; color: #888; margin-top: 0.25rem;">
        Calcul : minutes en mode 4 / minutes totales sur l'heure.
      </p>
    </div>

    <!-- Breakdown -->
    <div class="section" v-if="(data.breakdown as unknown[])?.length">
      <h3 class="section-title">Utilisation des batteries</h3>
      <DataTable :value="(data.breakdown as Record<string, unknown>[])" size="small" stripedRows>
        <Column field="label" header="Catégorie" sortable />
        <Column field="minutes" header="Minutes" sortable>
          <template #body="{ data }">{{ fmtNum(data.minutes) }}</template>
        </Column>
        <Column field="pct" header="%" sortable>
          <template #body="{ data }">{{ fmtNum(data.pct) }}</template>
        </Column>
      </DataTable>
    </div>

    <!-- Transitions 3->4 -->
    <div class="section" v-if="(data.transitions as unknown[])?.length">
      <h3 class="section-title">Transitions 3 (AC) → 4 (Batterie)</h3>
      <DataTable :value="(data.transitions as Record<string, unknown>[])" size="small" stripedRows>
        <Column field="start_mode3_time" header="Début mode 3" sortable />
        <Column field="start_mode4_time" header="Passage mode 4" sortable />
        <Column field="duration_min" header="Durée (min)" sortable>
          <template #body="{ data }">{{ fmtNum(data.duration_min) }}</template>
        </Column>
        <Column field="temp_c" header="Température (°C)" sortable>
          <template #body="{ data }">{{ fmtNum(data.temp_c) }}</template>
        </Column>
      </DataTable>

      <ScatterChart v-if="(scatterOption as Record<string, unknown>).series" :option="scatterOption" height="300px" style="margin-top: 1rem" />

      <div class="kpi-grid" style="margin-top: 1rem" v-if="data.trx_daily">
        <KpiCard title="Nb transitions 3→4" :value="String((data.trx_daily as Record<string, unknown>).n_transitions ?? 0)" />
        <KpiCard title="Durée moyenne (min)" :value="String((data.trx_daily as Record<string, unknown>).avg_duration_min ?? '-')" color="orange" />
        <KpiCard title="Température moyenne (°C)" :value="String((data.trx_daily as Record<string, unknown>).avg_temp_c ?? '-')" color="red" />
      </div>
    </div>

    <!-- Energy EV mode 3 -->
    <div class="kpi-grid" v-if="data.energy_ev_mode3 != null">
      <KpiCard title="Énergie EV en Mode AC (3) (kWh)" :value="`${data.energy_ev_mode3} kWh`" color="green" />
    </div>

    <!-- Historique complet des modes -->
    <div class="section" v-if="(data.hist as unknown[])?.length">
      <h3 class="section-title">Historique complet des modes</h3>
      <DataTable :value="(data.hist as Record<string, unknown>[])" size="small" stripedRows scrollable scrollHeight="400px">
        <Column field="start_time" header="Début" sortable />
        <Column field="end_time" header="Fin" sortable />
        <Column field="mode" header="Mode" sortable />
        <Column field="delta_time_min" header="Durée (min)" sortable>
          <template #body="{ data }">{{ fmtNum(data.delta_time_min) }}</template>
        </Column>
        <Column field="energie_pdc_kwh" header="E PDC (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energie_pdc_kwh) }}</template>
        </Column>
        <Column field="energie_ev_kwh" header="E EV (kWh)" sortable>
          <template #body="{ data }">{{ fmtNum(data.energie_ev_kwh) }}</template>
        </Column>
        <Column field="soc_debut" header="SOC début" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_debut) }}</template>
        </Column>
        <Column field="soc_fin" header="SOC fin" sortable>
          <template #body="{ data }">{{ fmtNum(data.soc_fin) }}</template>
        </Column>
        <Column field="delta_soc" header="ΔSOC" sortable>
          <template #body="{ data }">{{ fmtNum(data.delta_soc) }}</template>
        </Column>
      </DataTable>
    </div>
  </template>
</template>
