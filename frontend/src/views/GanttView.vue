<template>
  <div class="page-container" v-loading="loading">
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ project?.name }}</h1>
        <p class="page-sub">GANTT CHART · 时间线与依赖关系</p>
      </div>
      <div class="head-actions">
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
      <span class="legend-item"><i class="legend-dot legend-blue" />进行中/待办</span>
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

onMounted(load)
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--bmw-space-xl) 0 var(--bmw-space-md);
}
.page-title { margin: 0; font-size: var(--bmw-text-display-md); }
.page-sub {
  margin: var(--bmw-space-xs) 0 0;
  font-size: var(--bmw-text-body-sm);
  color: var(--bmw-muted);
  letter-spacing: 1.5px;
}
.head-actions { display: flex; gap: var(--bmw-space-sm); }

.gantt-legend {
  display: flex;
  gap: var(--bmw-space-lg);
  margin: var(--bmw-space-lg) 0 0;
  padding: 0;
  font-size: var(--bmw-text-caption);
  color: var(--bmw-muted);
  flex-wrap: wrap;
}
.legend-item { display: inline-flex; align-items: center; gap: 6px; }
.legend-dot { width: 12px; height: 8px; display: inline-block; }
.legend-blue { background-color: var(--bmw-primary); }
.legend-red { background-color: var(--bmw-error); }
.legend-line { width: 16px; height: 0; border-top: 2px dashed var(--bmw-muted-soft); }
.legend-progress { width: 12px; height: 8px; display: inline-block; background: linear-gradient(90deg, #0653b6 55%, #1c69d4 55%); }
</style>
