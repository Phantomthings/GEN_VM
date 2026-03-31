<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BoxplotChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, DatasetComponent, TransformComponent,
} from 'echarts/components'
import type { EChartsOption } from 'echarts'

use([CanvasRenderer, BoxplotChart, TitleComponent, TooltipComponent, GridComponent, DatasetComponent, TransformComponent])

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
