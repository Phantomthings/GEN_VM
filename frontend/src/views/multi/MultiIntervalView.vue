<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import SiteSelector from '@/components/common/SiteSelector.vue'
import DateRangeFilter from '@/components/common/DateRangeFilter.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import LineChart from '@/components/charts/LineChart.vue'
import BoxPlotChart from '@/components/charts/BoxPlotChart.vue'
import HeatmapChart from '@/components/charts/HeatmapChart.vue'
import { fetchIntervalDates, fetchIntervalData } from '@/api/multi'
import type { EChartsOption } from 'echarts'
import { fmtNum } from '@/utils/format'
import { REG_MODE_COLORS, REG_MODE_LABELS, SOC_STATE_COLORS, SOC_STATE_LABELS } from '@/utils/modeColors'

const sites = ref<string[]>([])
const dateRange = ref<Date[] | null>(null)
const availableDates = ref<string[]>([])
const loading = ref(false)
const data = ref<Record<string, unknown> | null>(null)

watch(sites, async (s) => {
  if (!s.length) return
  availableDates.value = await fetchIntervalDates(s)
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
    data.value = await fetchIntervalData(
      sites.value,
      range[0].toISOString().split('T')[0],
      range[1].toISOString().split('T')[0],
    )
  } finally {
    loading.value = false
  }
})

// â”€â”€ Chart helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const palette = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7']
function siteColor(site: string, allSites: string[]): string {
  return palette[allSites.indexOf(site) % palette.length]
}

type TSPoint = { site: string; date: string; [key: string]: unknown }

function buildLineChart(field: string, title: string, yLabel: string): EChartsOption {
  const ts = (data.value?.timeseries as TSPoint[]) ?? []
  if (!ts.length) return {}
  const allSites = [...new Set(ts.map(p => p.site))].sort()
  const allDates = [...new Set(ts.map(p => p.date))].sort()
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, data: allSites, type: 'scroll' },
    xAxis: { type: 'category', data: allDates, axisLabel: { rotate: 30, fontSize: 9 } },
    yAxis: { type: 'value', name: yLabel },
    series: allSites.map(site => ({
      type: 'line' as const,
      name: site,
      data: allDates.map(d => {
        const pt = ts.find(p => p.site === site && p.date === d)
        return pt ? (pt[field] as number ?? null) : null
      }),
      connectNulls: true,
      showSymbol: true,
      symbolSize: 5,
      lineStyle: { color: siteColor(site, allSites), width: 2 },
      itemStyle: { color: siteColor(site, allSites) },
    })),
    grid: { left: 55, right: 20, bottom: 55, top: 45 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 25 }],
  }
}

function buildBoxChart(): EChartsOption {
  const boxes = (data.value?.boxplot_minutes_run as Array<{ site: string; min: number; q1: number; median: number; q3: number; max: number }>) ?? []
  if (!boxes.length) return {}
  return {
    title: { text: 'Distribution de la durÃ©e passÃ©e en RUN (2)', left: 'center', textStyle: { fontSize: 13 } },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const values = Array.isArray(point?.data) ? point.data : []
        return `${point?.name ?? '-'}<br>Max: ${values[4] ?? '-'}<br>Q3: ${values[3] ?? '-'}<br>MÃ©diane: ${values[2] ?? '-'}<br>Q1: ${values[1] ?? '-'}<br>Min: ${values[0] ?? '-'}`
      },
    },
    xAxis: { type: 'category', data: boxes.map(b => b.site), axisLabel: { rotate: 20, fontSize: 10 } },
    yAxis: { type: 'value', name: 'Minutes' },
    series: [{
      type: 'boxplot',
      data: boxes.map((b, i) => ({
        name: b.site,
        value: [b.min, b.q1, b.median, b.q3, b.max],
        itemStyle: { color: palette[i % palette.length], borderColor: palette[i % palette.length] },
      })),
    }],
    grid: { left: 55, right: 20, bottom: 60, top: 50 },
  }
}

// â”€â”€ Heatmap helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
type HourEntry = { hour: number; dominant_mode?: number | null; dominant_pct?: number | null; dominant_state?: number | null; avg_pct?: number }

function buildMode4HeatmapOption(hm: HourEntry[], site: string): EChartsOption {
  const full = Array.from({ length: 24 }, (_, h) => {
    const pt = hm.find(p => p.hour === h)
    return [h, 0, pt ? pt.avg_pct ?? 0 : 0]
  })
  return {
    title: { text: site, left: 0, textStyle: { fontSize: 11, color: '#475569' } },
    tooltip: {
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const values = Array.isArray(point?.data) ? point.data : []
        const pct = typeof values[2] === 'number' ? values[2].toFixed(1) : values[2] ?? '-'
        return `${values[0] ?? '-'}h : ${pct}%`
      },
    },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => String(i)), name: 'Heure', nameTextStyle: { fontSize: 10 } },
    yAxis: { type: 'category', data: [site], show: false },
    visualMap: { min: 0, max: 100, orient: 'horizontal', left: 'center', bottom: 0, show: false,
      inRange: { color: ['#eff6ff', '#1d4ed8'] } },
    series: [{
      type: 'heatmap',
      data: full,
      label: {
        show: true,
        formatter: (params) => {
          const values = Array.isArray(params.data) ? params.data : []
          return typeof values[2] === 'number' && values[2] > 0 ? `${values[2].toFixed(0)}%` : ''
        },
        fontSize: 8,
      },
    }],
    grid: { left: 8, right: 8, top: 22, bottom: 30, height: 38 },
  }
}

const REG_COLORS = REG_MODE_COLORS
const REG_LABELS = REG_MODE_LABELS
const SOC_COLORS = SOC_STATE_COLORS
const SOC_LABELS = SOC_STATE_LABELS

function buildDominantHeatmap(
  hours: HourEntry[],
  site: string,
  field: 'dominant_mode' | 'dominant_state',
  colorMap: Record<number, string>,
  labelMap: Record<number, string>,
): EChartsOption {
  const vals = Array.from({ length: 24 }, (_, h) => {
    const pt = hours.find(p => p.hour === h)
    const v = pt ? (pt[field] as number | null) : null
    return [h, 0, v ?? -1]
  })

  const presentStates = [...new Set(vals.map(v => v[2] as number).filter(v => v >= 0))].sort()
  const pieces = presentStates.map(s => ({
    value: s,
    label: labelMap[s] ?? `Mode ${s}`,
    color: colorMap[s] ?? '#888',
  }))

  return {
    title: { text: site, left: 0, textStyle: { fontSize: 11, color: '#475569' } },
    tooltip: {
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const values = Array.isArray(point?.data) ? point.data : []
        const hour = typeof values[0] === 'number' ? values[0] : Number(values[0])
        const v = typeof values[2] === 'number' ? values[2] : Number(values[2])
        if (!Number.isFinite(v) || v < 0) return `${Number.isFinite(hour) ? hour : '-'}h : -`
        const pt = hours.find(h => h.hour === hour)
        const pct = pt ? (field === 'dominant_mode' ? pt.dominant_pct : pt.dominant_pct) : null
        return `${hour}h : ${labelMap[v] ?? v}${pct != null ? ` (${pct}%)` : ''}`
      },
    },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => String(i)), name: 'Heure', nameTextStyle: { fontSize: 10 } },
    yAxis: { type: 'category', data: [site], show: false },
    visualMap: {
      type: 'piecewise',
      pieces: [{ value: -1, label: 'N/A', color: '#f1f5f9' }, ...pieces],
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      show: false,
    },
    series: [{
      type: 'heatmap',
      data: vals,
      label: {
        show: true,
        fontSize: 8,
        formatter: (params) => {
          const values = Array.isArray(params.data) ? params.data : []
          const v = typeof values[2] === 'number' ? values[2] : Number(values[2])
          if (!Number.isFinite(v) || v < 0) return ''
          return String(v)
        },
      },
    }],
    grid: { left: 8, right: 8, top: 22, bottom: 30, height: 38 },
  }
}

// â”€â”€ Computed accessors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const batteries = computed(() => (data.value?.batteries as Record<string, { pivot: Record<string, unknown>[]; stats: Record<string, unknown>[] }>) ?? {})
const energies = computed(() => (data.value?.energies as Record<string, { pivot: Record<string, unknown>[]; stats: Record<string, unknown>[] }>) ?? {})
const transitions = computed(() => (data.value?.transitions as Record<string, unknown>[]) ?? [])
const heatmapPerSite = computed(() => (data.value?.heatmap_per_site as Record<string, HourEntry[]>) ?? {})
const regDominant = computed(() => (data.value?.reg_dominant_hourly as Record<string, HourEntry[]>) ?? {})
const socDominant = computed(() => (data.value?.soc_dominant_hourly as Record<string, HourEntry[]>) ?? {})
const statusOverall = computed(() => (data.value?.status_overall as Record<string, unknown>[]) ?? [])
const statusDaily = computed(() => (data.value?.status_daily as Record<string, unknown>[]) ?? [])
const top3Ev = computed(() => (data.value?.top3_ev as Record<string, unknown>[]) ?? [])
const hasSeries = computed(() => !!((data.value?.timeseries as unknown[])?.length))

// Legend color dots for dominant timelines
function legendEntries(colorMap: Record<number, string>, labelMap: Record<number, string>) {
  return Object.entries(labelMap).map(([k, label]) => ({ state: Number(k), label, color: colorMap[Number(k)] }))
}
</script>

<template>
  <div class="page-header"><h1>Comparaison - Intervalle</h1></div>

  <div class="filter-bar">
    <SiteSelector v-model="sites" />
    <DateRangeFilter v-model="dateRange" />
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">

    <!-- â”€â”€ Batteries â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <div class="section">
      <h3 class="section-title">Batteries</h3>

      <template v-if="batteries.minutes_run?.pivot?.length">
        <h4>DurÃ©e SOC Management (min)</h4>
        <div class="table-scroll-wrapper">
          <DataTable :value="batteries.minutes_run.pivot" size="small" stripedRows scrollable scrollHeight="280px">
            <Column v-for="col in Object.keys(batteries.minutes_run.pivot[0] ?? {})" :key="col"
                    :field="col" :header="col === 'site' ? 'Site' : col"
                    :frozen="col === 'site'" style="min-width:90px" sortable>
              <template #body="{ data }">{{ col === 'site' ? data[col] : fmtNum(data[col]) }}</template>
            </Column>
          </DataTable>
        </div>
        <h4 style="margin-top:1rem">Stats DurÃ©e SOC Management (min)</h4>
        <DataTable :value="batteries.minutes_run.stats" size="small" stripedRows>
          <Column field="site" header="Site" sortable />
          <Column field="Min" header="Min" sortable><template #body="{ data }">{{ fmtNum(data['Min']) }}</template></Column>
          <Column field="Date Min" header="Date Min" sortable />
          <Column field="Max" header="Max" sortable><template #body="{ data }">{{ fmtNum(data['Max']) }}</template></Column>
          <Column field="Date Max" header="Date Max" sortable />
          <Column field="Moyenne" header="Moyenne" sortable><template #body="{ data }">{{ fmtNum(data['Moyenne']) }}</template></Column>
          <Column field="Ecart-type" header="Ã‰cart-type" sortable><template #body="{ data }">{{ fmtNum(data['Ecart-type']) }}</template></Column>
          <Column field="Jours" header="Jours" sortable />
        </DataTable>
      </template>

      <template v-if="batteries.soc_start_pct?.pivot?.length">
        <h4 style="margin-top:1.25rem">SOC au dÃ©but du SOC Management (%)</h4>
        <div class="table-scroll-wrapper">
          <DataTable :value="batteries.soc_start_pct.pivot" size="small" stripedRows scrollable scrollHeight="280px">
            <Column v-for="col in Object.keys(batteries.soc_start_pct.pivot[0] ?? {})" :key="col"
                    :field="col" :header="col === 'site' ? 'Site' : col"
                    :frozen="col === 'site'" style="min-width:90px" sortable>
              <template #body="{ data }">{{ col === 'site' ? data[col] : fmtNum(data[col]) }}</template>
            </Column>
          </DataTable>
        </div>
        <h4 style="margin-top:1rem">Stats SOC dÃ©but RUN (%)</h4>
        <DataTable :value="batteries.soc_start_pct.stats" size="small" stripedRows>
          <Column field="site" header="Site" sortable />
          <Column field="Min" header="Min" sortable><template #body="{ data }">{{ fmtNum(data['Min']) }}</template></Column>
          <Column field="Date Min" header="Date Min" sortable />
          <Column field="Max" header="Max" sortable><template #body="{ data }">{{ fmtNum(data['Max']) }}</template></Column>
          <Column field="Date Max" header="Date Max" sortable />
          <Column field="Moyenne" header="Moyenne" sortable><template #body="{ data }">{{ fmtNum(data['Moyenne']) }}</template></Column>
          <Column field="Ecart-type" header="Ã‰cart-type" sortable><template #body="{ data }">{{ fmtNum(data['Ecart-type']) }}</template></Column>
          <Column field="Jours" header="Jours" sortable />
        </DataTable>
      </template>

      <div style="margin-top:1.25rem" v-if="hasSeries">
        <LineChart :option="buildLineChart('soc_start_pct', 'SOC au passage en RUN (2)', 'SOC (%)')" height="300px" />
      </div>

      <div style="margin-top:1rem" v-if="(data.boxplot_minutes_run as unknown[])?.length">
        <BoxPlotChart :option="buildBoxChart()" height="280px" />
      </div>
    </div>

    <!-- â”€â”€ Timeline horaire â€” Mode batterie dominant (SOC) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <div class="section" v-if="Object.keys(socDominant).length">
      <h3 class="section-title">Timeline horaire â€” Mode batterie dominant sur la pÃ©riode</h3>
      <div v-for="(hours, site) in socDominant" :key="String(site)" style="margin-bottom:.75rem">
        <HeatmapChart :option="buildDominantHeatmap(hours, String(site), 'dominant_state', SOC_COLORS, SOC_LABELS)" height="100px" />
      </div>
      <!-- LÃ©gende -->
      <div class="dominant-legend">
        <span v-for="e in legendEntries(SOC_COLORS, SOC_LABELS)" :key="e.state" class="legend-item">
          <span class="legend-dot" :style="{ background: e.color }"></span>{{ e.label }}
        </span>
      </div>
      <p class="chart-caption">Couleur = Ã©tat dominant. Plus c'est foncÃ©, plus le % de dominance est Ã©levÃ©.</p>
    </div>

    <!-- â”€â”€ Ã‰nergies â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <div class="section">
      <h3 class="section-title">Ã‰nergies</h3>

      <template v-if="energies.energy_ev_kwh?.pivot?.length">
        <h4>Ã‰nergie EV (kWh)</h4>
        <div class="table-scroll-wrapper">
          <DataTable :value="energies.energy_ev_kwh.pivot" size="small" stripedRows scrollable scrollHeight="280px">
            <Column v-for="col in Object.keys(energies.energy_ev_kwh.pivot[0] ?? {})" :key="col"
                    :field="col" :header="col === 'site' ? 'Site' : col"
                    :frozen="col === 'site'" style="min-width:90px" sortable>
              <template #body="{ data }">{{ col === 'site' ? data[col] : fmtNum(data[col]) }}</template>
            </Column>
          </DataTable>
        </div>
        <h4 style="margin-top:1rem">Stats Ã‰nergie EV (kWh)</h4>
        <DataTable :value="energies.energy_ev_kwh.stats" size="small" stripedRows>
          <Column field="site" header="Site" sortable />
          <Column field="Min" header="Min" sortable><template #body="{ data }">{{ fmtNum(data['Min']) }}</template></Column>
          <Column field="Date Min" header="Date Min" sortable />
          <Column field="Max" header="Max" sortable><template #body="{ data }">{{ fmtNum(data['Max']) }}</template></Column>
          <Column field="Date Max" header="Date Max" sortable />
          <Column field="Moyenne" header="Moyenne" sortable><template #body="{ data }">{{ fmtNum(data['Moyenne']) }}</template></Column>
          <Column field="Ecart-type" header="Ã‰cart-type" sortable><template #body="{ data }">{{ fmtNum(data['Ecart-type']) }}</template></Column>
          <Column field="Jours" header="Jours" sortable />
        </DataTable>
      </template>

      <template v-if="top3Ev.length">
        <h4 style="margin-top:1.25rem">Top 3 journÃ©es Ã‰nergie EV par site</h4>
        <DataTable :value="top3Ev" size="small" stripedRows>
          <Column field="Site" header="Site" sortable />
          <Column field="Rang" header="Rang" sortable />
          <Column field="Date" header="Date" sortable />
          <Column field="Ã‰nergie EV (kWh)" header="Ã‰nergie EV (kWh)" sortable>
            <template #body="{ data }">{{ fmtNum(data['Ã‰nergie EV (kWh)']) }}</template>
          </Column>
        </DataTable>
      </template>

      <div style="margin-top:1.25rem" v-if="hasSeries">
        <LineChart :option="buildLineChart('energy_ev_kwh', 'Ã‰nergie EV journaliÃ¨re', 'kWh')" height="300px" />
        <LineChart :option="buildLineChart('ev_peak_kw', 'Puissance EV maximale', 'kW')" height="300px" style="margin-top:1rem" />
      </div>
    </div>

    <!-- â”€â”€ RÃ©gulation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ -->
    <div class="section">
      <h3 class="section-title">RÃ©gulation</h3>

      <template v-if="statusOverall.length">
        <h4>Status centrale</h4>
        <DataTable :value="statusOverall" size="small" stripedRows scrollable>
          <Column field="Site" header="Site" frozen sortable />
          <Column field="% OFF" header="% OFF" sortable><template #body="{ data }">{{ fmtNum(data['% OFF']) }}</template></Column>
          <Column field="Heures OFF" header="H OFF" sortable><template #body="{ data }">{{ fmtNum(data['Heures OFF']) }}</template></Column>
          <Column field="% AC" header="% AC" sortable><template #body="{ data }">{{ fmtNum(data['% AC']) }}</template></Column>
          <Column field="Heures AC" header="H AC" sortable><template #body="{ data }">{{ fmtNum(data['Heures AC']) }}</template></Column>
          <Column field="% BATT recharge EV" header="% BATT EV" sortable><template #body="{ data }">{{ fmtNum(data['% BATT recharge EV']) }}</template></Column>
          <Column field="Heures BATT recharge EV" header="H BATT EV" sortable><template #body="{ data }">{{ fmtNum(data['Heures BATT recharge EV']) }}</template></Column>
          <Column field="% BATT recharge rÃ©seau" header="% BATT rÃ©seau" sortable><template #body="{ data }">{{ fmtNum(data['% BATT recharge rÃ©seau']) }}</template></Column>
          <Column field="Heures BATT recharge rÃ©seau" header="H BATT rÃ©seau" sortable><template #body="{ data }">{{ fmtNum(data['Heures BATT recharge rÃ©seau']) }}</template></Column>
        </DataTable>
      </template>

      <template v-if="statusDaily.length">
        <h4 style="margin-top:1rem">Moyenne journaliÃ¨re des pourcentages (Status centrale)</h4>
        <DataTable :value="statusDaily" size="small" stripedRows>
          <Column field="Site" header="Site" sortable />
          <Column field="% OFF" header="% OFF" sortable><template #body="{ data }">{{ fmtNum(data['% OFF']) }}</template></Column>
          <Column field="% AC" header="% AC" sortable><template #body="{ data }">{{ fmtNum(data['% AC']) }}</template></Column>
          <Column field="% BATT recharge EV" header="% BATT recharge EV" sortable><template #body="{ data }">{{ fmtNum(data['% BATT recharge EV']) }}</template></Column>
          <Column field="% BATT recharge rÃ©seau" header="% BATT recharge rÃ©seau" sortable><template #body="{ data }">{{ fmtNum(data['% BATT recharge rÃ©seau']) }}</template></Column>
        </DataTable>
      </template>

      <template v-if="transitions.length">
        <h4 style="margin-top:1rem">Moyenne des transitions 3 â†’ 4 sur l'intervalle</h4>
        <DataTable :value="transitions" size="small" stripedRows>
          <Column field="Site" header="Site" sortable />
          <Column field="Total transitions (3â†’4)" header="Total" sortable />
          <Column field="Moyenne/jour" header="Moy/jour" sortable><template #body="{ data }">{{ fmtNum(data['Moyenne/jour']) }}</template></Column>
          <Column field="DurÃ©e moyenne 3â†’4 (min)" header="DurÃ©e moy. (min)" sortable><template #body="{ data }">{{ fmtNum(data['DurÃ©e moyenne 3â†’4 (min)']) }}</template></Column>
          <Column field="TempÃ©rature moyenne 3â†’4 (Â°C)" header="Temp moy. (Â°C)" sortable><template #body="{ data }">{{ fmtNum(data['TempÃ©rature moyenne 3â†’4 (Â°C)']) }}</template></Column>
          <Column field="Jours" header="Jours" sortable />
        </DataTable>
      </template>

      <!-- Heatmap Mode 4 % par heure (une ligne par site) -->
      <template v-if="Object.keys(heatmapPerSite).length">
        <h4 style="margin-top:1rem">Mode 4 (Batterie) â€” % moyen du temps par heure</h4>
        <div v-for="(hm, site) in heatmapPerSite" :key="String(site)" style="margin-bottom:.75rem">
          <HeatmapChart :option="buildMode4HeatmapOption(hm, String(site))" height="100px" />
        </div>
      </template>

      <!-- Timeline horaire â€” Mode rÃ©gulation dominant -->
      <template v-if="Object.keys(regDominant).length">
        <h4 style="margin-top:1rem">Timeline horaire â€” Mode rÃ©gulation dominant sur la pÃ©riode</h4>
        <div v-for="(hours, site) in regDominant" :key="String(site)" style="margin-bottom:.75rem">
          <HeatmapChart :option="buildDominantHeatmap(hours, String(site), 'dominant_mode', REG_COLORS, REG_LABELS)" height="100px" />
        </div>
        <div class="dominant-legend">
          <span v-for="e in legendEntries(REG_COLORS, REG_LABELS)" :key="e.state" class="legend-item">
            <span class="legend-dot" :style="{ background: e.color }"></span>{{ e.label }}
          </span>
        </div>
        <p class="chart-caption">Couleur = mode dominant. Plus c'est foncÃ©, plus le % de dominance est Ã©levÃ©.</p>
      </template>
    </div>

  </template>
</template>

<style scoped>
/* Scrollable pivot table wrapper */
.table-scroll-wrapper {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

/* Dominant timeline legend */
.dominant-legend {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem 1rem;
  margin-top: .5rem;
  padding: .4rem .6rem;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: .3rem;
  font-size: 0.78rem;
  color: #475569;
}
.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}
.chart-caption {
  font-size: 0.78rem;
  color: #94a3b8;
  margin-top: .35rem;
}
</style>

