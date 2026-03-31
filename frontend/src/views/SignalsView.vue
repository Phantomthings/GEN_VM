<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import MultiSelect from 'primevue/multiselect'
import SelectButton from 'primevue/selectbutton'
import ProjectSelector from '@/components/common/ProjectSelector.vue'
import DateFilter from '@/components/common/DateFilter.vue'
import KpiCard from '@/components/common/KpiCard.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import LineChart from '@/components/charts/LineChart.vue'
import { fetchSignalsConfig, fetchSignalsData } from '@/api/signals'
import type { EChartsOption } from 'echarts'

interface SignalInfo {
  label: string
  unit: string
  thresholds?: Record<string, number>
}

const project = ref('')
const selectedDate = ref<Date | null>(null)
const viewMode = ref('individual')
const viewModeOptions = [
  { label: 'Individuel', value: 'individual' },
  { label: 'Comparaison', value: 'comparison' },
]

const signalConfigs = ref<Record<string, SignalInfo>>({})
const selectedSignals = ref<string[]>([])
const loading = ref(false)
const data = ref<Record<string, unknown> | null>(null)

const signalOptions = computed(() =>
  Object.entries(signalConfigs.value).map(([key, cfg]) => ({
    label: cfg.label,
    value: key,
  }))
)

onMounted(async () => {
  const cfg = await fetchSignalsConfig()
  signalConfigs.value = cfg.signals
  const keys = Object.keys(cfg.signals)
  selectedSignals.value = keys.slice(0, 3)
})

async function loadData() {
  if (!project.value || !selectedDate.value || !selectedSignals.value.length) return
  loading.value = true
  try {
    data.value = await fetchSignalsData(
      project.value,
      selectedDate.value.toISOString().split('T')[0],
      selectedSignals.value,
    )
  } finally {
    loading.value = false
  }
}

watch([project, selectedDate, selectedSignals], () => {
  if (project.value && selectedDate.value && selectedSignals.value.length) {
    loadData()
  }
})

const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316']

function individualChartOption(key: string, index: number): EChartsOption {
  const ts = (data.value?.timeseries as Array<Record<string, unknown>>) ?? []
  if (!ts.length) return {}
  const cfg = signalConfigs.value[key]
  const chartData = ts.filter(p => p[key] != null)

  const markLines: Array<Record<string, unknown>> = []
  if (cfg?.thresholds) {
    for (const [name, val] of Object.entries(cfg.thresholds)) {
      markLines.push({
        yAxis: val,
        label: { formatter: `${name}: ${val}`, position: 'end' },
        lineStyle: { type: 'dashed', color: name === 'critical' ? '#ef4444' : '#f59e0b' },
      })
    }
  }

  return {
    title: { text: cfg?.label ?? key, left: 'center', textStyle: { fontSize: 13 } },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chartData.map(p => p.time as string), axisLabel: { rotate: 45, fontSize: 9, formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v } },
    yAxis: { type: 'value', name: cfg?.unit ?? '' },
    series: [{
      type: 'line',
      data: chartData.map(p => p[key] as number),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: colors[index % colors.length], width: 1.5 },
      itemStyle: { color: colors[index % colors.length] },
      markLine: markLines.length ? { data: markLines, silent: true } : undefined,
    }],
    grid: { left: 60, right: 20, bottom: 80, top: 40 },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  }
}

const comparisonChartOption = computed<EChartsOption>(() => {
  const ts = (data.value?.timeseries as Array<Record<string, unknown>>) ?? []
  if (!ts.length) return {}

  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: ts.map(p => p.time as string), axisLabel: { rotate: 45, fontSize: 9, formatter: (v: string) => v.split(' ')[1]?.slice(0, 5) ?? v } },
    yAxis: { type: 'value' },
    series: selectedSignals.value.map((key, i) => ({
      type: 'line' as const,
      name: signalConfigs.value[key]?.label ?? key,
      data: ts.map(p => (p[key] as number) ?? null),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: colors[i % colors.length] },
      itemStyle: { color: colors[i % colors.length] },
    })),
    grid: { left: 60, right: 20, bottom: 80, top: 40 },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  }
})

const statistics = computed(() => (data.value?.statistics as Record<string, Record<string, number>>) ?? {})
const alarms = computed(() => (data.value?.alarms as Array<{ type: string; message: string }>) ?? [])
</script>

<template>
  <div class="page-header"><h1>Visualisation des signaux</h1></div>

  <div class="filter-bar">
    <ProjectSelector v-model="project" />
    <DateFilter v-model="selectedDate" />
    <div class="filter-group">
      <label>Mode</label>
      <SelectButton v-model="viewMode" :options="viewModeOptions" optionLabel="label" optionValue="value" />
    </div>
  </div>

  <div class="filter-bar">
    <div class="filter-group">
      <label>Signaux</label>
      <MultiSelect
        v-model="selectedSignals"
        :options="signalOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Choisir les signaux"
        display="chip"
        :maxSelectedLabels="4"
        style="min-width: 400px"
      />
    </div>
  </div>

  <LoadingOverlay v-if="loading" />

  <template v-else-if="data">
    <!-- Alarms -->
    <div v-for="alarm in alarms" :key="alarm.message"
         :class="alarm.type === 'error' ? 'kpi-card red' : 'kpi-card orange'"
         style="margin-bottom: 0.5rem;">
      <div class="kpi-value" style="font-size: 1rem;">
        <i :class="alarm.type === 'error' ? 'pi pi-times-circle' : 'pi pi-exclamation-triangle'"></i>
        {{ alarm.message }}
      </div>
    </div>

    <!-- Statistics -->
    <div class="kpi-grid" v-if="Object.keys(statistics).length">
      <template v-for="(stat, key) in statistics" :key="key">
        <KpiCard
          :title="signalConfigs[key]?.label ?? key"
          :value="`moy: ${stat.mean}`"
          :subtitle="`min: ${stat.min} | max: ${stat.max}`"
        />
      </template>
    </div>

    <!-- Charts -->
    <template v-if="viewMode === 'individual'">
      <div class="section" v-for="(key, i) in selectedSignals" :key="key">
        <LineChart :option="individualChartOption(key, i)" height="300px" />
      </div>
    </template>

    <div class="section" v-else>
      <LineChart :option="comparisonChartOption" height="500px" />
    </div>
  </template>
</template>
