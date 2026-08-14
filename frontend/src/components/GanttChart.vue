<template>
  <div class="gantt-wrap">
    <div class="gantt-toolbar">
      <button
        v-for="m in VIEW_MODES"
        :key="m.value"
        class="view-chip"
        :class="{ active: viewMode === m.value }"
        @click="setViewMode(m.value)"
      >
        {{ m.label }}
      </button>
      <span class="gantt-today">今日：{{ today }}</span>
    </div>
    <div ref="ganttRef" class="gantt-container" />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import Gantt from 'frappe-gantt'
import 'frappe-gantt/dist/frappe-gantt.css'
import type { GanttTask as FGTask } from 'frappe-gantt'
import type { GanttData } from '@/types'
import { cssVar, onThemeChange } from '@/composables/useThemeColors'
import './gantt.css'

const props = defineProps<{ data: GanttData }>()

const emit = defineEmits<{
  (e: 'date-change', taskId: string, start: string, end: string): void
  (e: 'progress-change', taskId: string, progress: number): void
}>()

const VIEW_MODES = [
  { value: 'Day', label: '日' },
  { value: 'Week', label: '周' },
  { value: 'Month', label: '月' },
]

const ganttRef = ref<HTMLElement>()
const viewMode = ref('Week')
const today = new Date().toISOString().slice(0, 10)
let chart: Gantt | null = null
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')

function toFGTask(): FGTask[] {
  return props.data.tasks.map((t) => ({
    id: String(t.id),
    name: t.name,
    start: t.start || props.data.project_start,
    end: t.end || props.data.project_end,
    progress: t.progress,
    dependencies: t.dependencies,
  }))
}

function barRadius() {
  return parseInt(cssVar('--md-radius-sm', '8px'), 10) || 8
}

function render() {
  if (!ganttRef.value) return
  if (chart) {
    chart.refresh(toFGTask())
  } else {
    chart = new Gantt(ganttRef.value, toFGTask(), {
      view_mode: viewMode.value as 'Day' | 'Week' | 'Month',
      language: 'zh',
      date_format: 'YYYY-MM-DD',
      header_height: 48,
      bar_height: 28,
      bar_corner_radius: barRadius(),
      padding: 16,
      on_date_change: (task, start, end) => {
        emit('date-change', task.id, fmt(start), fmt(end))
      },
      on_progress_change: (task, progress) => {
        emit('progress-change', task.id, Math.round(progress))
      },
    })
  }
}

function fmt(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// 渲染后标记延期任务（frappe-gantt 不提供该字段，手动加 data-overdue）
function markOverdue() {
  const overdueIds = new Set(props.data.tasks.filter((t) => t.overdue).map((t) => t.id))
  ganttRef.value?.querySelectorAll('.bar-wrapper').forEach((el) => {
    const id = el.getAttribute('data-id')
    if (id && overdueIds.has(id)) el.setAttribute('data-overdue', 'true')
    else el.removeAttribute('data-overdue')
  })
}

// 减少动态效果：frappe-gantt 用 SMIL <animate> 做宽度动画，摘除后条带直接呈最终宽度
function stripAnimations() {
  if (!prefersReducedMotion.matches) return
  ganttRef.value?.querySelectorAll('animate').forEach((el) => el.remove())
}

function afterRender() {
  nextTick(() => {
    markOverdue()
    stripAnimations()
  })
}

function setViewMode(mode: string) {
  viewMode.value = mode
  chart?.change_view_mode(mode)
}

watch(
  () => props.data,
  () => {
    render()
    afterRender()
  },
  { deep: true }
)

onMounted(() => {
  render()
  afterRender()
})

// 主题切换后重绘（CSS 变量已更新的下一帧再读）
onThemeChange(() => {
  render()
  afterRender()
})
</script>

<style scoped>
.gantt-wrap {
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg);
  background-color: var(--md-surface);
  padding: var(--md-space-4);
  overflow-x: auto;
}
.gantt-toolbar {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  margin-bottom: var(--md-space-4);
}
.view-chip {
  display: inline-flex;
  align-items: center;
  min-height: var(--md-control-height);
  background-color: var(--md-surface);
  border: 1px solid var(--md-outline);
  color: var(--md-on-surface);
  font-family: var(--md-font);
  font-size: var(--md-text-label-md);
  padding: var(--md-space-1) var(--md-space-3);
  cursor: pointer;
  border-radius: var(--md-radius-full);
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.view-chip.active {
  background-color: var(--md-primary);
  color: var(--md-on-primary);
  border-color: var(--md-primary);
}
.gantt-today {
  margin-left: auto;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}
.gantt-container { min-width: 720px; }
</style>
