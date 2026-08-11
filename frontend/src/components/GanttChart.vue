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
import './gantt-bmw.css'

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
      bar_corner_radius: 0, // BMW 直角
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

function setViewMode(mode: string) {
  viewMode.value = mode
  chart?.change_view_mode(mode)
}

watch(
  () => props.data,
  () => {
    render()
    nextTick(markOverdue)
  },
  { deep: true }
)

onMounted(() => {
  render()
  nextTick(markOverdue)
})
</script>

<style scoped>
.gantt-wrap {
  border: 1px solid var(--bmw-hairline);
  border-radius: var(--bmw-radius-none);
  background-color: var(--bmw-canvas);
  padding: var(--bmw-space-md);
  overflow-x: auto;
}
.gantt-toolbar {
  display: flex;
  align-items: center;
  gap: var(--bmw-space-xs);
  margin-bottom: var(--bmw-space-md);
}
.view-chip {
  background-color: var(--bmw-canvas);
  border: 1px solid var(--bmw-hairline-strong);
  color: var(--bmw-ink);
  font-family: var(--bmw-font);
  font-size: var(--bmw-text-caption);
  padding: var(--bmw-space-xxs) 12px;
  cursor: pointer;
  border-radius: var(--bmw-radius-none);
}
.view-chip.active {
  background-color: var(--bmw-ink);
  color: var(--bmw-on-dark);
  border-color: var(--bmw-ink);
}
.gantt-today {
  margin-left: auto;
  font-size: var(--bmw-text-caption);
  color: var(--bmw-muted);
}
.gantt-container { min-width: 720px; }
</style>
