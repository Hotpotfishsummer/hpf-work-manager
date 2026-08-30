<template>
  <div class="page-container" v-loading="loading">
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ project?.name }}</h1>
        <p class="page-sub">Gantt Chart · 时间线与依赖关系</p>
      </div>
      <div class="head-actions">
        <LiveIndicator :connected="connected" :is-reconnectable="reconnectable" @reconnect="reconnect" />
        <el-button size="large" @click="router.push(`/projects/${pid}`)">返回概览</el-button>
        <el-button size="large" @click="router.push(`/projects/${pid}/tasks`)">任务看板</el-button>
      </div>
    </div>

    <GanttChart
      v-if="gantt && gantt.tasks.length"
      :data="gantt"
      @date-change="onDateChange"
      @progress-change="onProgressChange"
    />
    <el-empty v-else-if="!loading" description="暂无任务，先去任务看板创建任务" :image-size="100" />

    <p class="gantt-legend">
      <span class="legend-item"><i class="legend-dot legend-blue" />进行中</span>
      <span class="legend-item"><i class="legend-dot legend-todo" />待办</span>
      <span class="legend-item"><i class="legend-dot legend-red" />已延期</span>
      <span class="legend-item"><i class="legend-line" />依赖关系</span>
      <span class="legend-item"><i class="legend-progress" />进度填充</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi, statsApi, taskApi } from '@/api'
import type { GanttData, Project } from '@/types'
import GanttChart from '@/components/GanttChart.vue'
import { useProjectEvents } from '@/composables/useProjectEvents'
import LiveIndicator from '@/components/LiveIndicator.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const pid = computed(() => Number(props.id))

const loading = ref(false)
const project = ref<Project | null>(null)
const gantt = ref<GanttData | null>(null)

async function load() {
  loading.value = true
  try {
    const [p, g] = await Promise.all([
      projectApi.get(pid.value),
      statsApi.gantt(pid.value),
    ])
    project.value = p
    gantt.value = g
  } finally {
    loading.value = false
  }
}

async function onDateChange(taskId: string, start: string, end: string) {
  await taskApi.update(Number(taskId), { start_date: start, due_date: end })
  ElMessage.success('日期已更新')
  gantt.value = await statsApi.gantt(pid.value)
}

async function onProgressChange(taskId: string, progress: number) {
  await taskApi.update(Number(taskId), {
    progress,
    status: progress >= 100 ? 'done' : undefined,
  })
  ElMessage.success(`进度已更新为 ${progress}%`)
  gantt.value = await statsApi.gantt(pid.value)
}

// 实时同步：AI 工具更新后自动刷新甘特图
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(load, 400)
}
const { connected, reconnectable, reconnect } = useProjectEvents(() => pid.value, scheduleReload)

onMounted(load)
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--md-space-6) 0 var(--md-space-4);
}
.page-title { margin: 0; font-size: var(--md-text-display-sm); }
.page-sub {
  margin: var(--md-space-1) 0 0;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  letter-spacing: var(--md-track-caption);
}
.head-actions { display: flex; gap: var(--md-space-2); }

.gantt-legend {
  display: flex;
  gap: var(--md-space-5);
  margin: var(--md-space-5) 0 0;
  padding: 0;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface);
  flex-wrap: wrap;
}
.legend-item { display: inline-flex; align-items: center; gap: var(--md-space-1); }
.legend-dot { width: 12px; height: 8px; display: inline-block; border-radius: var(--md-radius-sm); }
.legend-blue { background-color: var(--md-primary); }
.legend-todo { background-color: var(--md-status-todo); }
.legend-red { background-color: var(--md-status-overdue); }
.legend-line { width: 16px; height: 0; border-top: 2px dashed var(--md-outline-variant); }
.legend-progress { width: 12px; height: 8px; display: inline-block; border-radius: var(--md-radius-sm); background: linear-gradient(90deg, var(--md-primary-container) 55%, var(--md-primary) 55%); }
</style>
