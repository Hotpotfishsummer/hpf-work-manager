<template>
  <div ref="chartRef" class="burndown-chart" />
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { BurndownPoint } from '@/types'

const props = defineProps<{ data: BurndownPoint[] }>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chartRef.value || props.data.length === 0) return
  chart = chart ?? echarts.init(chartRef.value)
  chart.setOption(
    {
      animationDuration: 300,
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#e6e6e6',
        textStyle: { color: '#262626', fontFamily: 'Inter', fontWeight: 300 },
      },
      legend: {
        data: ['期望剩余', '实际剩余'],
        top: 0,
        right: 0,
        itemWidth: 16,
        itemHeight: 3,
        textStyle: { color: '#6b6b6b', fontFamily: 'Inter', fontWeight: 400 },
      },
      grid: { left: 44, right: 20, top: 44, bottom: 28 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: props.data.map((d) => d.date),
        axisLine: { lineStyle: { color: '#cccccc' } },
        axisTick: { show: false },
        axisLabel: { color: '#6b6b6b', fontFamily: 'Inter', fontWeight: 300 },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: '#ebebeb' } },
        axisLabel: { color: '#6b6b6b', fontFamily: 'Inter', fontWeight: 300 },
      },
      series: [
        {
          name: '期望剩余',
          type: 'line',
          data: props.data.map((d) => d.ideal_remaining),
          smooth: true,
          symbol: 'none',
          lineStyle: { color: '#9a9a9a', width: 2 },
          itemStyle: { color: '#9a9a9a' },
        },
        {
          name: '实际剩余',
          type: 'line',
          data: props.data.map((d) => d.actual_remaining),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color: '#1c69d4', width: 2 },
          itemStyle: { color: '#1c69d4' },
        },
      ],
    },
    true
  )
}

function onResize() {
  chart?.resize()
}

watch(
  () => props.data,
  () => nextTick(render)
)

onMounted(() => {
  render()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
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
