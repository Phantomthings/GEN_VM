<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart as EPieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import type { EChartsOption } from 'echarts'

use([CanvasRenderer, EPieChart, TitleComponent, TooltipComponent, LegendComponent])

const props = defineProps<{
  option: EChartsOption
  height?: string
}>()

const chartStyle = computed(() => ({
  width: '100%',
  height: props.height ?? '350px',
}))
</script>

<template>
  <VChart :option="option" :style="chartStyle" autoresize />
</template>
