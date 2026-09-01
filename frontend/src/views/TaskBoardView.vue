<template>
  <div class="page-container" v-loading="loading">
    <!-- 页面头部 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ project?.name }}</h1>
        <p class="page-sub">Task Board · 按状态分组管理任务</p>
      </div>
      <div class="head-actions">
        <el-form inline size="small" :model="searchForm">
          <el-form-item label="搜索" collapse-text>
            <el-input v-model="searchForm.keyword" placeholder="输入任务名称..." />
          </el-form-item>
        </el-form>
        <el-select v-model="sortBy" placeholder="排序" style="width: 120px">
          <el-option label="最新创建" value="created_desc" />
          <el-option label="最久远" value="due_asc" />
          <el-option label="最晚截止" value="due_desc" />
          <el-option label="优先级高->低" value="priority_desc" />
        </el-select>
        <LiveIndicator :connected="connected" :is-reconnectable="reconnectable" @reconnect="reconnect" />
        <el-button size="large" @click="router.push(`/projects/${pid}`)">返回概览</el-button>
        <el-button size="large" @click="exportCsv">
          <el-icon style="margin-right: var(--md-space-1)"><Download /></el-icon>
          导出 CSV
        </el-button>
        <el-button size="large" @click="exportMd">
          <el-icon style="margin-right: var(--md-space-1)"><Download /></el-icon>
          导出 .md
        </el-button>
        <el-button type="primary" size="large" @click="openCreate">
          <el-icon style="margin-right: var(--md-space-1)"><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <!-- filter-chips：筛选 -->
    <div class="chips-row">
      <el-form inline :model="filterForm" size="small">
        <el-form-item label="状态" collapse-text>
          <el-select v-model="filterForm.status" placeholder="全部">
            <el-option label="全部" value="" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="done" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" collapse-text>
          <el-select v-model="filterForm.priority" placeholder="全部">
            <el-option label="全部" value="" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="逾期" collapse-text>
          <el-switch v-model="filterForm.overdue" active-text="是" inactive-text="否" />
        </el-form-item>
      </el-form>
      <span class="chips-count">{{ filteredTasks.length }} 个任务</span>
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
            :class="{ 'is-overdue': t.overdue, 'is-selected': selectedTasks.includes(t.id) }"
            role="button"
            tabindex="0"
            draggable="true"
            @dragstart="dragTask = t"
            @dblclick="openEdit(t)"
            @keydown.enter.prevent="openEdit(t)"
          >
            <div class="tc-select">
              <el-checkbox
                :model-value="selectedTasks.includes(t.id)"
                @update:model-value="(v: boolean) => toggleSelect(t.id, v)"
                @click.stop
              />
            </div>
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
                <el-button link size="small" @click.stop="openDeps(t)">依赖</el-button>
                <el-button link type="danger" size="small" @click.stop="removeTask(t.id)">删除</el-button>
              </div>
            </div>
            <div v-if="t.depends_on?.length" class="tc-deps">
              <el-tag
                v-for="depId in t.depends_on"
                :key="depId"
                size="small"
                type="info"
                effect="plain"
                class="tc-dep-tag"
                :title="depName(depId)"
              >
                {{ depName(depId) }}
              </el-tag>
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
              value-format="YYYY-MM-DD"
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

    <!-- 批量操作弹窗 -->
    <el-dialog v-model="bulkDialog" title="批量操作" width="420px" destroy-on-close @close="bulkDialog = false">
      <p style="margin: 0 0 var(--md-space-3)">
        已选择 <strong>{{ selectedTasks.length }}</strong> 个任务，批量修改字段：
      </p>
      <el-form label-position="top" :model="bulkForm">
        <el-form-item label="状态">
          <el-select v-model="bulkForm.status" placeholder="不改" clearable>
            <el-option label="待办" value="todo" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="done" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="bulkForm.priority" placeholder="不改" clearable>
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="里程碑">
          <el-select v-model="bulkForm.milestone_id" placeholder="不改" clearable>
            <el-option label="（无里程碑）" :value="null" />
            <el-option v-for="m in milestones" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bulkDialog = false">取消</el-button>
        <el-button type="primary" @click="applyBulk">应用</el-button>
      </template>
    </el-dialog>
    <!-- 依赖关系管理弹窗 -->
    <el-dialog
      v-model="depsDialog"
      :title="depsTask ? `依赖关系 · ${depsTask.name}` : '依赖关系'"
      width="480px"
      destroy-on-close
      @close="depsDialog = false"
    >
      <p class="deps-hint">勾选需要作为前置依赖的任务（可多选）。被依赖任务未完成时，会在卡片上提示。</p>
      <el-input v-model="depsSearch" placeholder="搜索任务名" size="small" clearable class="deps-search" />
      <el-checkbox-group v-model="depsSelected" class="deps-list">
        <el-checkbox
          v-for="opt in filteredDepsCandidates"
          :key="opt.id"
          :value="opt.id"
          :label="opt.label"
          class="deps-item"
        />
      </el-checkbox-group>
      <p v-if="depsCandidates.length === 0" class="deps-empty">无其他可选任务</p>
      <template #footer>
        <el-button @click="depsDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDeps">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { milestoneApi, projectApi, taskApi } from '@/api'
import type { Milestone, Project, Task, TaskPriority, TaskStatus, TaskUpdate } from '@/types'
import { generateCsv } from '@/utils/csv'
import { useProjectEvents } from '@/composables/useProjectEvents'
import LiveIndicator from '@/components/LiveIndicator.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const pid = computed(() => Number(props.id))

const loading = ref(false)
const project = ref<Project | null>(null)
// 扩展 Task 类型：依赖列表由 SSE 刷新时注入
type TaskEx = Task & { depends_on?: number[] }
const tasks = ref<TaskEx[]>([])
const milestones = ref<Milestone[]>([])
const filterForm = reactive({
  status: '',
  priority: '',
  overdue: false,
})
const searchForm = reactive({
  keyword: '',
})
const sortBy = ref('')
const dragTask = ref<Task | null>(null)
const selectedTasks = ref<number[]>([])
const bulkDialog = ref(false)
const bulkForm = reactive<{
  status?: TaskStatus
  priority?: TaskPriority
  milestone_id?: number | null
}>({ status: undefined, priority: undefined, milestone_id: null })
const saving = ref(false)

const dialogVisible = ref(false)
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

/** 应用前端筛选 + 搜索 + 排序（响应式派生，不另行请求） */
const filteredTasks = computed(() => {
  let result = tasks.value
  if (filterForm.status) result = result.filter((t) => t.status === filterForm.status)
  if (filterForm.priority) result = result.filter((t) => t.priority === filterForm.priority)
  if (filterForm.overdue) result = result.filter((t) => t.overdue)
  const k = searchForm.keyword.trim().toLowerCase()
  if (k) result = result.filter((t) => t.name.toLowerCase().includes(k) || (t.description ?? '').toLowerCase().includes(k))
  if (sortBy.value) {
    result = [...result].sort((a, b) => {
      switch (sortBy.value) {
        case 'due_asc':
          return (a.due_date ?? '9999-99-99').localeCompare(b.due_date ?? '9999-99-99')
        case 'due_desc':
          return (b.due_date ?? '0000-00-00').localeCompare(a.due_date ?? '0000-00-00')
        case 'priority_desc': {
          const order = { high: 0, medium: 1, low: 2 }
          return (order[a.priority] ?? 3) - (order[b.priority] ?? 3)
        }
        default:
          return 0
      }
    })
  }
  return result
})

const grouped = computed(() => {
  const map: Record<TaskStatus, TaskEx[]> = { todo: [], in_progress: [], done: [] }
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
  if (p === 'high') return 'warning'
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

function sanitizeFilename(name: string): string {
  const cleaned = name.replace(/[/\\]/g, '_').replace(/[\x00-\x1f\x7f]/g, '')
  return (cleaned.slice(0, 80) || 'tasks').trim()
}

function exportCsv() {
  if (!tasks.value.length) {
    ElMessage.info('暂无任务可导出')
    return
  }
  const headers = ['ID', '名称', '状态', '优先级', '进度', '开始日期', '截止日期']
  const statusLabel: Record<string, string> = { todo: '待办', in_progress: '进行中', done: '已完成' }
  const rows = tasks.value.map((t) => [
    t.id,
    t.name,
    statusLabel[t.status] ?? t.status,
    t.priority,
    `${t.progress}%`,
    t.start_date ?? '',
    t.due_date ?? '',
  ])
  const csv = '\uFEFF' + generateCsv(headers, rows)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${sanitizeFilename(project.value?.name ?? 'project')}_tasks_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// P1-5: 导出任务 Markdown
function exportMd() {
  if (!tasks.value.length) {
    ElMessage.info('暂无任务可导出')
    return
  }
  const statusLabel: Record<string, string> = { todo: '待办', in_progress: '进行中', done: '已完成' }
  const lines: string[] = [
    `# ${project.value?.name ?? '项目'} · 任务清单`,
    '',
    `> 导出时间：${new Date().toLocaleString('zh-CN')} · 共 ${tasks.value.length} 个任务`,
    '',
  ]
  for (const col of COLUMNS) {
    const list = tasks.value.filter((t) => t.status === col.status)
    if (!list.length) continue
    lines.push(`## ${col.label}（${list.length}）`, '')
    for (const t of list) {
      const due = t.due_date ? ` · 截止 ${t.due_date.slice(0, 10)}` : ''
      const overdue = t.overdue ? ' · **已逾期**' : ''
      lines.push(`- [${t.status === 'done' ? 'x' : ' '}] **${t.name}**（${PRIORITY_LABEL[t.priority]}优先级 · ${t.progress}%${due}${overdue}）`)
      if (t.description) lines.push(`  ${t.description}`)
    }
    lines.push('')
  }
  const md = lines.join('\n')
  const blob = new Blob(['\uFEFF' + md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${sanitizeFilename(project.value?.name ?? 'project')}_tasks_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
}

// 实时同步：AI 工具更新任务后自动刷新
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(load, 400)
}
const { connected, reconnectable, reconnect } = useProjectEvents(() => pid.value, scheduleReload)

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
      const prev = tasks.value.find((t) => t.id === editing.value!.id)
      optimisticPatch(editing.value.id, payload as Partial<Task>, prev!)
      try {
        await taskApi.update(editing.value.id, payload)
        ElMessage.success('已更新')
      } catch {
        rollback(prev)
        return
      }
    } else {
      const res = await taskApi.create(pid.value, payload)
      tasks.value.unshift(res)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
  } finally {
    saving.value = false
  }
}

async function removeTask(id: number) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确定删除该任务？', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const prev = tasks.value.find((t) => t.id === id)
  tasks.value = tasks.value.filter((t) => t.id !== id)
  try {
    await taskApi.remove(id)
    ElMessage.success('已删除')
  } catch {
    rollback(prev)
  }
}

// 乐观更新：本地应用 patch，失败时回滚
function optimisticPatch(id: number, patch: Partial<Task>, fallback: Task) {
  tasks.value = tasks.value.map((t) => (t.id === id ? { ...t, ...patch } : t))
}
function rollback(item: Task | undefined) {
  if (item) {
    tasks.value = tasks.value.filter((t) => t.id !== item.id)
    tasks.value = [item, ...tasks.value]
  }
}

function onDrop(e: DragEvent, status: TaskStatus) {
  const t = dragTask.value
  dragTask.value = null
  if (!t || t.status === status) return
  // done → todo/in_progress 时重置 progress（计划 P1-2）
  const progress = status === 'done' ? 100 : 0
  const patch = { status, progress: progress < 100 ? progress : (t.progress < 100 ? 0 : t.progress) }
  optimisticPatch(t.id, { ...patch, progress }, t)
  if (status === 'done' && t.progress < 100) {
    ElMessage.info('完成任务时进度将自动设为 100%')
  }
  taskApi
    .update(t.id, { status, progress })
    .then(() => { /* SSE 会广播，无需 reload */ })
    .catch(() => rollback(t))
}

function toggleSelect(id: number, checked: boolean) {
  if (checked) {
    selectedTasks.value = [...selectedTasks.value, id]
  } else {
    selectedTasks.value = selectedTasks.value.filter((sid) => sid !== id)
  }
}

// ---- 批量操作 ----

function openBulkDialog() {
  bulkForm.status = undefined
  bulkForm.priority = undefined
  bulkForm.milestone_id = null
  bulkDialog.value = true
}

async function applyBulk() {
  if (!selectedTasks.value.length) return
  const data: Record<string, unknown> = {}
  if (bulkForm.status) data.status = bulkForm.status
  if (bulkForm.priority) data.priority = bulkForm.priority
  if (bulkForm.milestone_id !== null) data.milestone_id = bulkForm.milestone_id
if (!Object.keys(data).length) {
    ElMessage.info('请选择要批量修改的字段')
    return
  }
  bulkDialog.value = false
  try {
    await taskApi.bulk({ ids: selectedTasks.value, data: data })
    ElMessage.success('批量更新完成')
    selectedTasks.value = []
    load()
  } catch {
    ElMessage.error('批量更新失败')
  }
}

// ---- 依赖关系编辑 (P1-3) ----
const depsDialog = ref(false)
const depsTask = ref<TaskEx | null>(null)
const depsCandidates = ref<{ id: number; label: string }[]>([])
const depsSelected = ref<number[]>([])
const depsSearch = ref('')

// 过滤后的候选列表（包含搜索词匹配）
const filteredDepsCandidates = computed(() => {
  const search = depsSearch.value?.trim().toLowerCase() ?? ''
  return depsCandidates.value.filter((c) => c.label.toLowerCase().includes(search))
})

function depName(id: number): string {
  return tasks.value.find((t) => t.id === id)?.name ?? `#${id}`
}

async function openDeps(t: TaskEx) {
  depsTask.value = t
  const all = await taskApi.list(pid.value)
  const excluded = new Set<number>([t.id, ...(t.depends_on ?? [])])
  depsCandidates.value = all
    .filter((x) => !excluded.has(x.id))
    .map((x) => ({ id: x.id, label: `${x.name}${x.status === 'done' ? '（已完成）' : ''}` }))
  depsSelected.value = [...(t.depends_on ?? [])]
  depsSearch.value = ''
  depsDialog.value = true
}

async function saveDeps() {
  const task = depsTask.value
  if (!task) return
  const current = task.depends_on ?? []
  const target = depsSelected.value
  const toAdd = target.filter((id) => !current.includes(id))
  const toRemove = current.filter((id) => !target.includes(id))
  try {
    await Promise.all([
      ...toAdd.map((id) => taskApi.addDep(task.id, id)),
      ...toRemove.map((id) => taskApi.removeDep(task.id, id)),
    ])
    // 乐观更新本地依赖列表
    const idx = tasks.value.findIndex((t) => t.id === task.id)
    if (idx >= 0) tasks.value[idx] = { ...tasks.value[idx], depends_on: [...target] }
    ElMessage.success('依赖关系已更新')
    depsDialog.value = false
  } catch {
    ElMessage.error('依赖关系更新失败')
  }
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
  letter-spacing: var(--md-track-caption);
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
  display: inline-flex;
  align-items: center;
  min-height: var(--md-control-height);
  background-color: var(--md-surface-container-highest);
  border: 1px solid var(--md-outline);
  color: var(--md-on-surface);
  font-size: var(--md-text-label-md);
  font-family: var(--md-font);
  padding: var(--md-space-1) var(--md-space-4);
  cursor: pointer;
  border-radius: var(--md-radius-full);
  transition: background-color var(--md-duration-standard) var(--md-ease-standard),
    color var(--md-duration-standard) var(--md-ease-standard),
    border-color var(--md-duration-standard) var(--md-ease-standard);
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
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-surface);
}
.col-count {
  margin-left: auto;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  background-color: var(--md-surface-container-high);
  padding: 0 var(--md-space-2);
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
  transition: border-color var(--md-duration-standard) var(--md-ease-standard),
    background-color var(--md-duration-standard) var(--md-ease-standard);
}
.task-card:hover {
  border-color: var(--md-primary);
  background-color: var(--md-surface-container-low);
}
.task-card.is-overdue { border-left-color: var(--md-status-overdue); }
.task-card:active { cursor: grabbing; }

.tc-top { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--md-space-1); }
.tc-name { font-size: var(--md-text-title-sm); font-weight: var(--md-weight-semibold); color: var(--md-on-surface); }
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
.tc-date.is-overdue { color: var(--md-status-overdue); font-weight: var(--md-weight-semibold); }
.tc-overdue {
  font-size: var(--md-text-label-md);
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-error);
  background-color: var(--md-status-overdue);
  padding: 1px var(--md-space-2);
  border-radius: var(--md-radius-sm);
}
.tc-progress { margin: var(--md-space-1) 0; }
.tc-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tc-progress-text { font-size: var(--md-text-label-md); color: var(--md-on-surface-variant); font-weight: var(--md-weight-semibold); }

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 var(--md-space-4);
}
@media (max-width: 520px) { .form-grid { grid-template-columns: 1fr; } }

/* 选择态 */
.task-card.is-selected {
  border-color: var(--md-primary);
  background-color: var(--md-primary-container);
}
.tc-select {
  position: absolute;
  top: var(--md-space-2);
  left: var(--md-space-2);
  z-index: 1;
}
.task-card {
  position: relative;
  padding-left: var(--md-space-7);
}
</style>
