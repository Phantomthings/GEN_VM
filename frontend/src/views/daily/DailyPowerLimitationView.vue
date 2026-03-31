<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import DateFilter from '@/components/common/DateFilter.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import LineChart from '@/components/charts/LineChart.vue'
import { fetchPowerLimitationDates, fetchPowerLimitationData } from '@/api/daily'
import { useFiltersStore } from '@/stores/filters'
import type { EChartsOption } from 'echarts'

const filters = useFiltersStore()
const project = ref(filters.dailyProject ?? '')
const selectedDate = ref<Date | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const data = ref<Record<string, unknown> | null>(null)
let requestId = 0

// Which plugs to display
const allPlugs = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
const selectedPlugs = ref<string[]>([...allPlugs])

watch(() => filters.dailyProject, (p) => {
  if (p && p !== project.value) project.value = p
})

watch(() => filters.dailyDate, (d) => {
  if (!d) return
  const next = new Date(`${d}T12:00:00`)
  if (!selectedDate.value || selectedDate.value.toISOString().slice(0, 10) !== d) selectedDate.value = next
})

watch(project, async (p) => {
  if (!p) return
  filters.setDailyProject(p)
  const currentRequest = ++requestId
  const dates = await fetchPowerLimitationDates(p)
  if (currentRequest !== requestId) return
  availableDates.value = dates
  selectedDate.value = filters.resolveDailyDate(dates)
}, { immediate: true })

watch(selectedDate, async (d) => {
  if (!d || !project.value) return
  const dateStr = d.toISOString().split('T')[0]
  filters.setDailyDate(dateStr)
  const currentRequest = ++requestId
  loading.value = true
  try {
    const payload = await fetchPowerLimitationData(project.value, dateStr)
    if (currentRequest !== requestId) return
    data.value = payload
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
})

type ChartPt = Record<string, unknown>

// ── BOX charts ────────────────────────────────────────────────────────────────

const boxChart = computed(() => (data.value?.box_chart as ChartPt[]) ?? [])
const boxKpi = computed(() => (data.value?.box_kpi as Record<string, number>) ?? {})

/** Main BOX chart: PDC_ORI_Lim_DC (abs) + Gen_ORI_EVPMes (abs) + Plant_is_limited (negative axis) */
const plantChartOption = computed((): EChartsOption => {
  const pts = boxChart.value
  if (!pts.length) return {}

  const times = pts.map(p => p.time as string)
  const pdcAbs = pts.map(p => p.pdc_lim_dc != null ? Math.abs(p.pdc_lim_dc as number) : null)
  const evAbs  = pts.map(p => p.ev_power   != null ? Math.abs(p.ev_power   as number) : null)

  // Plant_is_limited: 0→-5 (OK), 1→-50 (LIMITED)
  const limited = pts.map(p => {
    if (p.plant_is_limited == null) return null
    return p.plant_is_limited === 1 ? -50 : -5
  })

  const yMax = Math.max(
    ...pdcAbs.filter(v => v != null).map(v => v as number),
    ...evAbs.filter(v => v != null).map(v => v as number),
    50,
  ) * 1.1

  return {
    title: { text: 'Limitation DC, Puissance EV et Plant is limited', left: 'center', top: 4, textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { top: 28, right: 10, data: ['PDC_ORI_Lim_DC (abs)', 'Gen_ORI_EVPMes (abs)', 'Plant is limited'] },
    xAxis: { type: 'category', data: times, axisLabel: { formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v, interval: 59 } },
    yAxis: { type: 'value', name: 'kW', min: -60, max: Math.ceil(yMax) },
    series: [
      {
        name: 'PDC_ORI_Lim_DC (abs)',
        type: 'line',
        data: pdcAbs,
        showSymbol: false,
        lineStyle: { color: '#1f77b4', width: 2 },
        itemStyle: { color: '#1f77b4' },
      },
      {
        name: 'Gen_ORI_EVPMes (abs)',
        type: 'line',
        data: evAbs,
        showSymbol: false,
        lineStyle: { color: '#ff7f0e', width: 2 },
        itemStyle: { color: '#ff7f0e' },
      },
      {
        name: 'Plant is limited',
        type: 'line',
        data: limited,
        showSymbol: false,
        step: 'end',
        lineStyle: { color: '#d62728', width: 4 },
        itemStyle: { color: '#d62728' },
        areaStyle: { color: 'rgba(214,39,40,0.5)' },
        tooltip: {
          valueFormatter: (v: unknown) => (v === -50 ? 'LIMITED' : 'OK'),
        },
      },
    ],
    markLine: {
      silent: true,
      data: [{ yAxis: 0, lineStyle: { color: '#aaa', type: 'dashed' } }],
    },
    grid: { left: 60, right: 20, bottom: 40, top: 70 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 0 }],
  }
})

/** SOC chart: Gen_ORI_SOC (continuous) + SocMgt_OBI_SocLow (step/binary) */
const socChartOption = computed((): EChartsOption => {
  const pts = boxChart.value
  if (!pts.length) return {}

  const times  = pts.map(p => p.time as string)
  const soc    = pts.map(p => p.soc    != null ? p.soc    : null)
  const socLow = pts.map(p => p.soc_low != null ? p.soc_low : null)

  return {
    title: { text: 'SOC Low et SOC', left: 'center', top: 4, textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { top: 28, right: 10, data: ['Gen_ORI_SOC', 'SocMgt_OBI_SocLow'] },
    xAxis: { type: 'category', data: times, axisLabel: { formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v, interval: 59 } },
    yAxis: { type: 'value', name: 'Valeur' },
    series: [
      {
        name: 'Gen_ORI_SOC',
        type: 'line',
        data: soc,
        showSymbol: false,
        lineStyle: { color: '#2ca02c', width: 2 },
        itemStyle: { color: '#2ca02c' },
      },
      {
        name: 'SocMgt_OBI_SocLow',
        type: 'line',
        data: socLow,
        showSymbol: false,
        step: 'end',
        lineStyle: { color: '#d62728', width: 2 },
        itemStyle: { color: '#d62728' },
      },
    ],
    grid: { left: 60, right: 20, bottom: 40, top: 70 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 0 }],
  }
})

// ── BORNE / plug charts ────────────────────────────────────────────────────────

type PlugData = { kpi: Record<string, number>; chart: ChartPt[] }

function getPlug(name: string): PlugData {
  const plugs = (data.value?.plugs as Record<string, PlugData>) ?? {}
  return plugs[name] ?? { kpi: {}, chart: [] }
}

function buildPlugMainChart(plugName: string): EChartsOption {
  const num = plugName.replace('P', '')
  const pts = getPlug(plugName).chart
  if (!pts.length) return {}
  const times = pts.map(p => p.time as string)
  const pdc   = pts.map(p => p.pdc_r_plim      != null ? p.pdc_r_plim      : null)
  const evse  = pts.map(p => p.evse_out_power   != null ? p.evse_out_power  : null)
  return {
    title: { text: `Prise P${num} — Power limitation`, left: 'center', top: 4, textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis' },
    legend: { top: 26, right: 10, data: [`PDCx_R_PLim[${num}]`, `EVSE_OutPower P${num}`] },
    xAxis: { type: 'category', data: times, axisLabel: { formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v, interval: 59 } },
    yAxis: { type: 'value', name: 'kW' },
    series: [
      {
        name: `PDCx_R_PLim[${num}]`,
        type: 'line',
        data: pdc,
        showSymbol: false,
        lineStyle: { color: '#1f77b4', width: 2 },
        itemStyle: { color: '#1f77b4' },
      },
      {
        name: `EVSE_OutPower P${num}`,
        type: 'line',
        data: evse,
        showSymbol: false,
        lineStyle: { color: '#2ca55c', width: 2 },
        itemStyle: { color: '#2ca55c' },
      },
    ],
    grid: { left: 60, right: 20, bottom: 40, top: 65 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 0 }],
  }
}

function buildPlugLimitedChart(plugName: string): EChartsOption {
  const num = plugName.replace('P', '')
  const pts = getPlug(plugName).chart
  if (!pts.length) return {}
  const times   = pts.map(p => p.time as string)
  const limited = pts.map(p => p.is_limited != null ? p.is_limited : null)
  return {
    title: { text: `Plug${num} is limited (timeline)`, left: 'center', top: 2, textStyle: { fontSize: 12 } },
    tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => (v === 1 ? 'LIMITED' : 'OK') },
    xAxis: { type: 'category', data: times, axisLabel: { formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v, interval: 59 } },
    yAxis: {
      type: 'value',
      min: -0.1, max: 1.1,
      interval: 1,
      axisLabel: { formatter: (v: number) => (v === 1 ? 'LIMITED' : v === 0 ? 'OK' : '') },
    },
    series: [{
      name: `Plug${num} is limited`,
      type: 'line',
      data: limited,
      showSymbol: false,
      step: 'end',
      lineStyle: { color: '#d62728', width: 2 },
      itemStyle: { color: '#d62728' },
      areaStyle: { color: 'rgba(214,39,40,0.3)' },
    }],
    grid: { left: 70, right: 20, bottom: 30, top: 30 },
    dataZoom: [{ type: 'inside' }],
  }
}

function buildPlugWeightChart(plugName: string): EChartsOption {
  const num = plugName.replace('P', '')
  const pts = getPlug(plugName).chart
  if (!pts.length) return {}
  const times  = pts.map(p => p.time as string)
  const weight = pts.map(p => p.weight != null ? p.weight : null)
  return {
    title: { text: `Poids de répartition P${num}`, left: 'center', top: 2, textStyle: { fontSize: 12 } },
    tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '-') },
    xAxis: { type: 'category', data: times, axisLabel: { formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v, interval: 59 } },
    yAxis: { type: 'value', min: 0, max: 1.05, name: 'Poids (0-1)', axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{
      name: `Poids P${num}`,
      type: 'line',
      data: weight,
      showSymbol: false,
      connectNulls: true,
      lineStyle: { color: '#9467bd', width: 2 },
      itemStyle: { color: '#9467bd' },
    }],
    grid: { left: 60, right: 20, bottom: 30, top: 30 },
    dataZoom: [{ type: 'inside' }],
  }
}

function hasPlugData(plugName: string): boolean {
  return getPlug(plugName).chart.length > 0
}
</script>

<template>
  <div class="page-header"><h1>Analyse journaliere - Power Limitation</h1></div>

  <div class="filter-bar">
    <ProjectSelector v-model="project" />
    <DateFilter v-model="selectedDate" :availableDates="availableDates" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">

    <!-- ── Section BOX ───────────────────────────────────────────── -->
    <div class="section-title">Donnees Box</div>

    <!-- KPI global plant -->
    <div class="kpi-grid" v-if="Object.keys(boxKpi).length">
      <KpiCard
        title="Temps en limitation"
        :value="`${boxKpi.minutes_limited ?? 0} min`"
        :subtitle="`${boxKpi.pct_limited ?? 0}%`"
        color="red"
      />
      <KpiCard title="Points valides" :value="`${boxKpi.n_valid ?? 0}`" color="blue" />
      <KpiCard title="Points totaux"  :value="`${boxKpi.n_total ?? 0}`" color="blue" />
    </div>
    <p v-else class="no-data">Pas de donnees disponibles pour le diagnostic de limitation.</p>

    <!-- Plant chart -->
    <div class="section" v-if="boxChart.length">
      <LineChart :option="plantChartOption" height="380px" />
      <LineChart :option="socChartOption"   height="280px" style="margin-top:1rem" />
    </div>
    <p v-else class="no-data">Pas de donnees Box pour cette journee.</p>

    <!-- ── Section BORNES ────────────────────────────────────────── -->
    <div class="section-title" style="margin-top:2rem">Donnees Bornes (P1-P6)</div>

    <!-- Plug selector -->
    <div class="plug-selector">
      <span class="plug-selector-label">Prises a afficher :</span>
      <label v-for="p in allPlugs" :key="p" class="plug-checkbox">
        <input type="checkbox" :value="p" v-model="selectedPlugs" />
        {{ p }}
      </label>
    </div>

    <template v-for="plug in selectedPlugs" :key="plug">
      <div class="plug-block">
        <div class="plug-title">Prise {{ plug }}</div>

        <template v-if="hasPlugData(plug)">
          <!-- KPI plug -->
          <div class="kpi-grid kpi-grid--small">
            <KpiCard
              title="Temps en limitation"
              :value="`${getPlug(plug).kpi.minutes_limited ?? 0} min`"
              :subtitle="`${getPlug(plug).kpi.pct_limited ?? 0}%`"
              color="red"
            />
            <KpiCard title="Points valides" :value="`${getPlug(plug).kpi.n_valid ?? 0}`" color="blue" />
          </div>

          <!-- Main power chart -->
          <LineChart :option="buildPlugMainChart(plug)"    height="280px" />
          <!-- Limited timeline -->
          <LineChart :option="buildPlugLimitedChart(plug)" height="140px" style="margin-top:0.5rem" />
          <!-- Weight -->
          <LineChart :option="buildPlugWeightChart(plug)"  height="180px" style="margin-top:0.5rem" />
        </template>

        <p v-else class="no-data">Pas de donnees pour {{ plug }} sur cette journee.</p>
      </div>
    </template>

  </template>
</template>

<style scoped>
.section-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #000000;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 1.25rem 0 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid #475569;
}

.no-data {
  color: #64748b;
  font-style: italic;
  padding: 0.5rem 0;
}

.plug-selector {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.plug-selector-label {
  color: #94a3b8;
  font-size: 0.875rem;
}

.plug-checkbox {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: #cbd5e1;
  font-size: 0.875rem;
  cursor: pointer;
}

.plug-block {
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
}

.plug-title {
  font-size: 1rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: #2ca55c;
  border-left: 3px solid #2ca55c;
  border-radius: 3px;
}

.kpi-grid--small {
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  margin-bottom: 0.75rem;
}
</style>
