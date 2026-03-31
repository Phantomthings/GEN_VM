<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import DateFilter from '@/components/common/DateFilter.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import LineChart from '@/components/charts/LineChart.vue'
import { fetchEnergyDates, fetchEnergyData } from '@/api/daily'
import { useFiltersStore } from '@/stores/filters'
import type { EChartsOption } from 'echarts'
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
  availableDates.value = await fetchEnergyDates(p)
  selectedDate.value = filters.resolveDailyDate(availableDates.value)
}, { immediate: true })

watch(selectedDate, async (d) => {
  if (!d || !project.value) return
  const dateStr = d.toISOString().split('T')[0]
  filters.setDailyDate(dateStr)
  loading.value = true
  try {
    data.value = await fetchEnergyData(project.value, dateStr)
  } finally {
    loading.value = false
  }
})

const modeColors = REG_MODE_COLORS
const modeLabels = REG_MODE_LABELS

function buildPowerChart(yField: 'res_kw' | 'ev_kw', title: string): EChartsOption {
  const pts = (data.value?.minute_chart as Array<Record<string, unknown>>) ?? []
  if (!pts.length) return {}

  // Split into segments by mode
  const segments: Array<{ mode: number; times: string[]; values: number[] }> = []
  let current: typeof segments[0] | null = null

  for (const p of pts) {
    const m = (p.mode as number) ?? 0
    const v = Math.abs((p[yField] as number) ?? 0)
    if (!current || current.mode !== m) {
      // Bridge: duplicate last point of previous segment
      if (current) {
        segments.push(current)
      }
      current = { mode: m, times: [p.time as string], values: [v] }
    } else {
      current.times.push(p.time as string)
      current.values.push(v)
    }
  }
  if (current) segments.push(current)

  // Name each segment by its mode label — ECharts groups same-name series in legend
  const series = segments.map((seg) => ({
    type: 'line' as const,
    data: seg.times.map((t, j) => [t, seg.values[j]]),
    lineStyle: { color: modeColors[seg.mode] ?? '#888', width: 1.5 },
    itemStyle: { color: modeColors[seg.mode] ?? '#888' },
    showSymbol: false,
    name: modeLabels[seg.mode] ?? `Mode ${seg.mode}`,
  }))

  const seenModes = new Set(segments.map(s => s.mode))

  return {
    title: { text: title, left: 'center', top: 4, textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'time',
      axisLabel: { formatter: '{HH}:{mm}' },
    },
    yAxis: { type: 'value', name: 'kW' },
    series,
    legend: {
      top: 28,
      right: 10,
      orient: 'horizontal',
      data: Array.from(seenModes).sort().map(m => ({
        name: modeLabels[m] ?? `Mode ${m}`,
        itemStyle: { color: modeColors[m] ?? '#888' },
      })),
    },
    grid: { left: 60, right: 20, bottom: 40, top: 70 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 0 }],
  }
}

const resChartOption = computed(() => buildPowerChart('res_kw', 'Puissance reseau'))
const evChartOption = computed(() => buildPowerChart('ev_kw', 'Puissance EV'))

const kpi = computed(() => (data.value?.kpi as Record<string, number>) ?? {})
</script>

<template>
  <div class="page-header"><h1>Analyse journaliere - Energie</h1></div>

  <div class="filter-bar">
    <ProjectSelector v-model="project" />
    <DateFilter v-model="selectedDate" :availableDates="availableDates" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">
    <!-- Power charts -->
    <div class="section" v-if="(data.minute_chart as unknown[])?.length">
      <LineChart :option="resChartOption" height="350px" />
      <LineChart :option="evChartOption" height="350px" style="margin-top: 1rem" />
    </div>

    <!-- KPI cards -->
    <div class="kpi-grid">
      <KpiCard title="Puissance batterie max" :value="`${kpi.max_pdc_kw ?? 0} kW`" color="blue" />
      <KpiCard title="Puissance EV max" :value="`${kpi.max_ev_kw ?? 0} kW`" color="green" />
      <KpiCard title="Energie EV" :value="`${kpi.energy_ev_kwh ?? 0} kWh`" color="orange" />
      <KpiCard title="Energie de charge" :value="`${kpi.energy_charge_kwh ?? 0} kWh`" color="blue" />
      <KpiCard title="Energie de decharge" :value="`${kpi.energy_decharge_kwh ?? 0} kWh`" color="red" />
      <KpiCard title="Energie auxiliaire" :value="`${kpi.energy_aux_kwh ?? 0} kWh`" color="purple" />
    </div>
  </template>
</template>
