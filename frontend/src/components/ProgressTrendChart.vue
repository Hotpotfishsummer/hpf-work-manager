<template>
  <div ref="chartRef" class="trend-chart" />
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ProgressSnapshotPoint } from '@/types'
import { chartColors, cssVar, onThemeChange } from '@/composables/useThemeColors'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ data: ProgressSnapshotPoint[] }>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function buildOption() {
  const font = cssVar('--md-font') || 'Inter, -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif'
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const hasHours = props.data.some((d) => d.weighted_progress > 0)
  return {
    animation: !reducedMotion,
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: number) => `${v}%`,
      backgroundColor: chartColors.surface,
      borderColor: chartColors.outlineVariant,
      textStyle: { color: chartColors.onSurface, fontFamily: font, fontWeight: 400 },
    },
    legend: {
      data: hasHours ? ['数量进度', '工时加权'] : ['数量进度'],
      top: 0,
      right: 0,
      itemWidth: 16,
      itemHeight: 3,
      textStyle: { color: chartColors.onSurfaceVariant, fontFamily: font, fontWeight: 400 },
    },
    grid: { left: 40, right: 20, top: 40, bottom: 28 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.data.map((d) => d.date.slice(5)),
      axisLine: { lineStyle: { color: chartColors.outlineVariant } },
      axisTick: { show: false },
      axisLabel: { color: chartColors.onSurfaceVariant, fontFamily: font, fontWeight: 400 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', color: chartColors.onSurfaceVariant, fontFamily: font, fontWeight: 400 },
      splitLine: { lineStyle: { color: chartColors.outlineVariant } },
    },
    series: [
      {
        name: '数量进度',
        type: 'line',
        data: props.data.map((d) => d.progress),
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: chartColors.primary, width: 2 },
        itemStyle: { color: chartColors.primary },
        areaStyle: { color: chartColors.primary, opacity: 0.08 },
      },
      ...(hasHours
        ? [
            {
              name: '工时加权',
              type: 'line',
              data: props.data.map((d) => d.weighted_progress),
              smooth: true,
              symbol: 'none',
              lineStyle: { color: chartColors.onSurfaceVariant, width: 2, type: 'dashed' as const },
              itemStyle: { color: chartColors.onSurfaceVariant },
            },
          ]
        : []),
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
.trend-chart {
  width: 100%;
  height: 220px;
}
</style>
