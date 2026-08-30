<template>
  <div ref="chartRef" class="burndown-chart" />
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { BurndownPoint } from '@/types'
import { chartColors, cssVar, onThemeChange } from '@/composables/useThemeColors'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

const props = defineProps<{ data: BurndownPoint[] }>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function buildOption() {
  const font = cssVar('--md-font') || 'Inter, -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif'
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  return {
    animation: !reducedMotion,
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      backgroundColor: chartColors.surface,
      borderColor: chartColors.outlineVariant,
      textStyle: { color: chartColors.onSurface, fontFamily: font, fontWeight: 400 },
    },
    legend: {
      data: ['期望剩余', '实际剩余'],
      top: 0,
      right: 0,
      itemWidth: 16,
      itemHeight: 3,
      textStyle: { color: chartColors.onSurfaceVariant, fontFamily: font, fontWeight: 400 },
    },
    grid: { left: 44, right: 20, top: 44, bottom: 28 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.data.map((d) => d.date),
      axisLine: { lineStyle: { color: chartColors.outlineVariant } },
      axisTick: { show: false },
      axisLabel: { color: chartColors.onSurfaceVariant, fontFamily: font, fontWeight: 400 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: chartColors.outlineVariant } },
      axisLabel: { color: chartColors.onSurfaceVariant, fontFamily: font, fontWeight: 400 },
    },
    series: [
      {
        name: '期望剩余',
        type: 'line',
        data: props.data.map((d) => d.ideal_remaining),
        smooth: true,
        symbol: 'none',
        lineStyle: { color: chartColors.onSurfaceVariant, width: 2 },
        itemStyle: { color: chartColors.onSurfaceVariant },
      },
      {
        name: '实际剩余',
        type: 'line',
        data: props.data.map((d) => d.actual_remaining),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: chartColors.primary, width: 2 },
        itemStyle: { color: chartColors.primary },
      },
    ],
  }
}

function render() {
  if (!chartRef.value || props.data.length === 0) return
  chart = chart ?? echarts.init(chartRef.value)
  chart.setOption(buildOption(), true)
}

function onResize() {
  chart?.resize()
}

watch(
  () => props.data,
  () => nextTick(render)
)

onThemeChange(() => render())

onMounted(() => {
  render()
  window.addEventListener('resize', onResize)
  ro = new ResizeObserver(onResize)
  if (chartRef.value) ro.observe(chartRef.value)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  ro?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.burndown-chart {
  width: 100%;
  height: 280px;
}
</style>
