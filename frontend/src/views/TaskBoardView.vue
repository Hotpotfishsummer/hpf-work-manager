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

    <!-- filter-chips：BMW 风格筛选 -->
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
  { status: 'todo', label: '待办', color: '#9a9a9a' },
  { status: 'in_progress', label: '进行中', color: '#1c69d4' },
  { status: 'done', label: '已完成', color: '#22c55e' },
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
  if (t.overdue) return '#dc2626'
  if (t.status === 'done') return '#22c55e'
  return '#1c69d4'
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

/* filter-chips：白底 + 描边，激活态墨底白字 */
.chips-row {
  display: flex;
  align-items: center;
  gap: var(--bmw-space-xs);
  margin-bottom: var(--bmw-space-lg);
  flex-wrap: wrap;
}
.filter-chip {
  background-color: var(--bmw-canvas);
  border: 1px solid var(--bmw-hairline-strong);
  color: var(--bmw-ink);
  font-size: var(--bmw-text-caption);
  font-family: var(--bmw-font);
  padding: var(--bmw-space-xs) 14px;
  cursor: pointer;
  border-radius: var(--bmw-radius-none);
  transition: background-color 0.15s ease, color 0.15s ease;
}
.filter-chip:hover { border-color: var(--bmw-ink); }
.filter-chip.active {
  background-color: var(--bmw-ink);
  color: var(--bmw-on-dark);
  border-color: var(--bmw-ink);
}
.chips-count { margin-left: auto; font-size: var(--bmw-text-caption); color: var(--bmw-muted); }

/* 三列看板 */
.board {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--bmw-space-lg);
  align-items: start;
}
@media (max-width: 900px) { .board { grid-template-columns: 1fr; } }

.board-col {
  border: 1px solid var(--bmw-hairline);
  border-radius: var(--bmw-radius-none);
  background-color: var(--bmw-surface-soft);
  min-height: 320px;
}
.col-head {
  display: flex;
  align-items: center;
  gap: var(--bmw-space-xs);
  padding: var(--bmw-space-md);
  background-color: var(--bmw-canvas);
  border-bottom: 1px solid var(--bmw-hairline);
}
.col-dot { width: 8px; height: 8px; border-radius: var(--bmw-radius-full); }
.col-title {
  font-size: var(--bmw-text-title-sm);
  font-weight: var(--bmw-weight-display);
  color: var(--bmw-ink);
}
.col-count {
  margin-left: auto;
  font-size: var(--bmw-text-caption);
  color: var(--bmw-muted);
  background-color: var(--bmw-surface-strong);
  padding: 2px 8px;
}
.col-body {
  padding: var(--bmw-space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--bmw-space-sm);
}
.col-empty { padding: var(--bmw-space-lg) 0; }

/* task-card：白底直角卡片，延期红色左描边 */
.task-card {
  background-color: var(--bmw-canvas);
  border: 1px solid var(--bmw-hairline);
  border-left: 3px solid var(--bmw-hairline-strong);
  border-radius: var(--bmw-radius-none);
  padding: var(--bmw-space-md);
  cursor: grab;
}
.task-card.is-overdue { border-left-color: var(--bmw-error); }
.task-card:active { cursor: grabbing; }

.tc-top { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--bmw-space-xs); }
.tc-name { font-size: var(--bmw-text-title-sm); font-weight: var(--bmw-weight-display); color: var(--bmw-ink); }
.tc-desc {
  margin: var(--bmw-space-xs) 0;
  font-size: var(--bmw-text-body-sm);
  color: var(--bmw-body);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.tc-meta { display: flex; align-items: center; justify-content: space-between; margin: var(--bmw-space-xs) 0; }
.tc-date { font-size: var(--bmw-text-caption); color: var(--bmw-muted); }
.tc-date.is-overdue { color: var(--bmw-error); font-weight: 700; }
.tc-overdue {
  font-size: var(--bmw-text-caption);
  font-weight: 700;
  color: var(--bmw-on-dark);
  background-color: var(--bmw-error);
  padding: 1px 6px;
}
.tc-progress { margin: var(--bmw-space-xs) 0; }
.tc-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tc-progress-text { font-size: var(--bmw-text-caption); color: var(--bmw-muted); font-weight: 700; }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 var(--bmw-space-md);
}
@media (max-width: 520px) { .form-grid { grid-template-columns: 1fr; } }
</style>
