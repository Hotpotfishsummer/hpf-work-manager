<template>
  <div class="page-container" v-loading="loading">
    <!-- 页面头部 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ project?.name }}</h1>
        <p class="page-sub">TASK BOARD · 按状态分组管理任务</p>
      </div>
      <div class="head-actions">
        <el-button size="large" @click="router.push(`/projects/${pid}`)">返回概览</el-button>
        <el-button type="primary" size="large" @click="openCreate">
          <el-icon style="margin-right: 6px"><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <!-- filter-chips：筛选 -->
    <div class="chips-row">
      <button
        v-for="c in FILTERS"
        :key="c.value"
        class="filter-chip"
        :class="{ active: filter === c.value }"
        @click="filter = c.value"
      >
        {{ c.label }}
      </button>
      <span class="chips-count">{{ tasks.length }} 个任务</span>
    </div>

    <!-- 三列看板 -->
    <div class="board">
      <div
        v-for="col in COLUMNS"
        :key="col.status"
        class="board-col"
        @dragover.prevent
        @drop="onDrop($event, col.status)"
      >
        <div class="col-head">
          <span class="col-dot" :style="{ backgroundColor: col.color }" />
          <span class="col-title">{{ col.label }}</span>
          <span class="col-count">{{ grouped[col.status].length }}</span>
        </div>

        <div class="col-body">
          <div
            v-for="t in grouped[col.status]"
            :key="t.id"
            class="task-card"
            :class="{ 'is-overdue': t.overdue }"
            draggable="true"
            @dragstart="dragTask = t"
            @dblclick="openEdit(t)"
          >
            <div class="tc-top">
              <span class="tc-name">{{ t.name }}</span>
              <el-tag
                :type="priorityTagType(t.priority)"
                effect="plain"
                size="small"
              >
                {{ PRIORITY_LABEL[t.priority] }}
              </el-tag>
            </div>
            <p v-if="t.description" class="tc-desc">{{ t.description }}</p>

            <div class="tc-meta">
              <span class="tc-date" :class="{ 'is-overdue': t.overdue }">
                {{ t.due_date ? t.due_date.slice(0, 10) : '无截止' }}
              </span>
              <span v-if="t.overdue" class="tc-overdue">已逾期</span>
            </div>

            <el-progress
              :percentage="t.progress"
              :stroke-width="4"
              :color="progressColor(t)"
              :show-text="false"
              class="tc-progress"
            />
            <div class="tc-actions">
              <span class="tc-progress-text">{{ t.progress }}%</span>
              <div>
                <el-button link size="small" @click.stop="openEdit(t)">编辑</el-button>
                <el-button link type="danger" size="small" @click.stop="removeTask(t.id)">删除</el-button>
              </div>
            </div>
          </div>

          <el-empty
            v-if="grouped[col.status].length === 0"
            description="暂无任务"
            :image-size="60"
            class="col-empty"
          />
        </div>
      </div>
    </div>

    <!-- 任务弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑任务' : '新建任务'"
      width="520px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="如：编写登录接口" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="任务说明（可选）" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="优先级">
            <el-select v-model="form.priority" style="width: 100%">
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="待办" value="todo" />
              <el-option label="进行中" value="in_progress" />
              <el-option label="已完成" value="done" />
            </el-select>
          </el-form-item>
          <el-form-item label="里程碑">
            <el-select v-model="form.milestone_id" clearable placeholder="无" style="width: 100%">
              <el-option v-for="m in milestones" :key="m.id" :label="m.name" :value="m.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="预估工时(h)">
            <el-input-number v-model="form.estimated_hours" :min="0" :step="1" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="进度">
            <el-slider v-model="form.progress" :min="0" :max="100" :step="5" />
          </el-form-item>
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="form.date_range"
              type="daterange"
              start-placeholder="开始"
              end-placeholder="截止"
              style="width: 100%"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { milestoneApi, projectApi, taskApi } from '@/api'
import type { Milestone, Project, Task, TaskPriority, TaskStatus } from '@/types'
import { useProjectEvents } from '@/composables/useProjectEvents'

const props = defineProps<{ id: string }>()
const router = useRouter()
const pid = computed(() => Number(props.id))

const loading = ref(false)
const project = ref<Project | null>(null)
const tasks = ref<Task[]>([])
const milestones = ref<Milestone[]>([])
const filter = ref('all')
const dragTask = ref<Task | null>(null)

const dialogVisible = ref(false)
const saving = ref(false)
const editing = ref<Task | null>(null)
const formRef = ref<FormInstance>()

const PRIORITY_LABEL: Record<TaskPriority, string> = { high: '高', medium: '中', low: '低' }

const COLUMNS: { status: TaskStatus; label: string; color: string }[] = [
  { status: 'todo', label: '待办', color: 'var(--md-status-todo)' },
  { status: 'in_progress', label: '进行中', color: 'var(--md-status-inprogress)' },
  { status: 'done', label: '已完成', color: 'var(--md-status-done)' },
]

const FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'overdue', label: '已延期' },
  { value: 'high', label: '高优先级' },
]

const filteredTasks = computed(() => {
  if (filter.value === 'overdue') return tasks.value.filter((t) => t.overdue)
  if (filter.value === 'high') return tasks.value.filter((t) => t.priority === 'high')
  return tasks.value
})

const grouped = computed(() => {
  const map: Record<TaskStatus, Task[]> = { todo: [], in_progress: [], done: [] }
  filteredTasks.value.forEach((t) => map[t.status].push(t))
  return map
})

const form = reactive({
  name: '',
  description: '',
  priority: 'medium' as TaskPriority,
  status: 'todo' as TaskStatus,
  milestone_id: null as number | null,
  estimated_hours: null as number | null,
  progress: 0,
  date_range: null as [string, string] | null,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
}

function priorityTagType(p: TaskPriority) {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}

function progressColor(t: Task) {
  if (t.overdue) return 'var(--md-status-overdue)'
  if (t.status === 'done') return 'var(--md-status-done)'
  if (t.status === 'in_progress') return 'var(--md-status-inprogress)'
  return 'var(--md-status-todo)'
}

async function load() {
  loading.value = true
  try {
    const [p, ts, ms] = await Promise.all([
      projectApi.get(pid.value),
      taskApi.list(pid.value),
      milestoneApi.list(pid.value),
    ])
    project.value = p
    tasks.value = ts
    milestones.value = ms
  } finally {
    loading.value = false
  }
}

// 实时同步：AI 工具更新任务后自动刷新
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(load, 400)
}
useProjectEvents(() => pid.value, scheduleReload)

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  form.priority = 'medium'
  form.status = 'todo'
  form.milestone_id = null
  form.estimated_hours = null
  form.progress = 0
  form.date_range = null
  dialogVisible.value = true
}

function openEdit(t: Task) {
  editing.value = t
  form.name = t.name
  form.description = t.description ?? ''
  form.priority = t.priority
  form.status = t.status
  form.milestone_id = t.milestone_id
  form.estimated_hours = t.estimated_hours
  form.progress = t.progress
  form.date_range = t.start_date && t.due_date ? [t.start_date, t.due_date] : null
  dialogVisible.value = true
}

async function save() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return

  saving.value = true
  try {
    const payload = {
      name: form.name,
      description: form.description || null,
      priority: form.priority,
      status: form.status,
      milestone_id: form.milestone_id,
      estimated_hours: form.estimated_hours,
      progress: form.status === 'done' ? 100 : form.progress,
      start_date: form.date_range?.[0] ?? null,
      due_date: form.date_range?.[1] ?? null,
    }
    if (editing.value) {
      await taskApi.update(editing.value.id, payload)
      ElMessage.success('已更新')
    } else {
      await taskApi.create(pid.value, payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function removeTask(id: number) {
  await ElMessageBox.confirm('删除后不可恢复，确定删除该任务？', '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await taskApi.remove(id)
  ElMessage.success('已删除')
  load()
}

function onDrop(e: DragEvent, status: TaskStatus) {
  const t = dragTask.value
  dragTask.value = null
  if (!t || t.status === status) return
  if (status === 'done' && t.progress < 100) {
    ElMessage.info('完成任务时进度将自动设为 100%')
  }
  taskApi.update(t.id, { status, progress: status === 'done' ? 100 : t.progress }).then(() => load())
}

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
  letter-spacing: 1.5px;
}
.head-actions { display: flex; gap: var(--md-space-2); }

/* filter-chips：描边胶囊，激活态主色填充 */
.chips-row {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  margin-bottom: var(--md-space-5);
  flex-wrap: wrap;
}
.filter-chip {
  background-color: var(--md-surface);
  border: 1px solid var(--md-outline);
  color: var(--md-on-surface);
  font-size: var(--md-text-label-md);
  font-family: var(--md-font);
  padding: var(--md-space-1) 16px;
  cursor: pointer;
  border-radius: var(--md-radius-full);
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.filter-chip:hover { border-color: var(--md-on-surface); }
.filter-chip.active {
  background-color: var(--md-primary);
  color: var(--md-on-primary);
  border-color: var(--md-primary);
}
.chips-count { margin-left: auto; font-size: var(--md-text-label-md); color: var(--md-on-surface-variant); }

/* 三列看板 */
.board {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md-space-5);
  align-items: start;
}
@media (max-width: 900px) { .board { grid-template-columns: 1fr; } }

.board-col {
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg);
  background-color: var(--md-surface-container);
  min-height: 320px;
}
.col-head {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  padding: var(--md-space-4);
  background-color: var(--md-surface);
  border-bottom: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg) var(--md-radius-lg) 0 0;
}
.col-dot { width: 8px; height: 8px; border-radius: var(--md-radius-full); }
.col-title {
  font-size: var(--md-text-title-sm);
  font-weight: var(--md-weight-bold);
  color: var(--md-on-surface);
}
.col-count {
  margin-left: auto;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  background-color: var(--md-surface-container-high);
  padding: 2px 8px;
  border-radius: var(--md-radius-sm);
}
.col-body {
  padding: var(--md-space-2);
  display: flex;
  flex-direction: column;
  gap: var(--md-space-2);
}
.col-empty { padding: var(--md-space-5) 0; }

/* task-card：圆角卡片，延期用状态色左描边 */
.task-card {
  background-color: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-left: 3px solid var(--md-outline);
  border-radius: var(--md-radius-lg);
  padding: var(--md-space-4);
  cursor: grab;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.task-card:hover {
  box-shadow: var(--md-shadow-1);
  transform: translateY(-1px);
}
.task-card.is-overdue { border-left-color: var(--md-status-overdue); }
.task-card:active { cursor: grabbing; }

.tc-top { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--md-space-1); }
.tc-name { font-size: var(--md-text-title-sm); font-weight: var(--md-weight-bold); color: var(--md-on-surface); }
.tc-desc {
  margin: var(--md-space-1) 0;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tc-meta { display: flex; align-items: center; justify-content: space-between; margin: var(--md-space-1) 0; }
.tc-date { font-size: var(--md-text-label-md); color: var(--md-on-surface-variant); }
.tc-date.is-overdue { color: var(--md-status-overdue); font-weight: 700; }
.tc-overdue {
  font-size: var(--md-text-label-md);
  font-weight: 700;
  color: var(--md-inverse-on-surface);
  background-color: var(--md-status-overdue);
  padding: 1px 6px;
  border-radius: var(--md-radius-sm);
}
.tc-progress { margin: var(--md-space-1) 0; }
.tc-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tc-progress-text { font-size: var(--md-text-label-md); color: var(--md-on-surface-variant); font-weight: 700; }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 var(--md-space-4);
}
@media (max-width: 520px) { .form-grid { grid-template-columns: 1fr; } }
</style>
