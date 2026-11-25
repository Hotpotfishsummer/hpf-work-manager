<template>
  <div class="cockpit-container" v-loading="loading">
    <!-- 顶部状态看板与快捷调度条 -->
    <section class="cockpit-hero md-section">
      <div class="hero-left">
        <div class="quota-row">
          <div class="quota-pill md-chip md-chip--sm md-state" :class="quotaLevel" @click="router.push('/quota')">
            <span class="live-dot" :class="quotaLevel"></span>
            <span class="pill-label">5h 算力窗口:</span>
            <strong>{{ quota.remaining_percent ?? 100 }}%</strong>
            <span class="pill-divider">·</span>
            <span class="pill-timer">⏳ {{ quota.minutes_left ?? 0 }}m 后重置 ({{ quota.reset_time_str ?? '--:--' }})</span>
          </div>

          <div
            class="driver-mode-pill"
            :class="driverMode.driver_mode === 'DUAL_CERTIFIED' ? 'dual' : 'external'"
            :title="driverMode.guidelines"
          >
            <span class="mode-icon">{{ driverMode.driver_mode === 'DUAL_CERTIFIED' ? '🛡️' : '⚡' }}</span>
            <span class="mode-label">{{ driverMode.driver_mode === 'DUAL_CERTIFIED' ? '内部+外部双重认证协同' : '外部驱动安全护栏' }}</span>
          </div>
        </div>
        <div class="hero-subtext">
          <span v-if="quota.is_night_shift" class="night-badge">🌙 闲时时段 (23:00-07:00)</span>
          <span class="sugg-text">{{ quota.suggestion || '算力就绪，可随时向 dsh 分派开发工单' }}</span>
        </div>
      </div>

      <div class="hero-actions">
        <el-button type="primary" size="default" @click="openCreateModal('todo')">
          <el-icon><Plus /></el-icon>
          新建工单
        </el-button>
        <el-button size="default" @click="router.push('/ideas')">
          <el-icon><Compass /></el-icon>
          灵感 & Next Steps
        </el-button>
        <el-button size="default" @click="openBatchPromptModal">
          <el-icon><CopyDocument /></el-icon>
          🌙 夜班指令包 (Prompt)
        </el-button>
        <el-button size="default" text circle @click="loadData" :loading="loading" title="刷新看板" aria-label="刷新看板">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </section>

    <!-- 筛选过滤与统计栏 -->
    <section class="filter-toolbar">
      <div class="filter-left">
        <div class="filter-item">
          <span class="item-label">项目:</span>
          <el-select v-model="filterProject" placeholder="全部项目" class="project-select" size="default" filterable>
            <el-option label="🌐 全部项目 (All Projects)" :value="0" />
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-button size="default" text :loading="syncingProjects" @click="syncLocalProjects" title="扫描服务器本地目录，自动将新代码库建档为独立项目">
            📥 同步本地项目库
          </el-button>
          <el-button size="default" text @click="openDirections()" title="给项目留工作方向 / 指示：下一次接手该项目的 Agent 会读到">
            💬 项目指示
          </el-button>
        </div>

        <div class="filter-item">
          <span class="item-label">优先级:</span>
          <div class="chip-group" role="group" aria-label="按优先级筛选">
            <button type="button" class="md-chip md-chip--filter" :class="{ 'is-selected': filterPriority === 'all' }" :aria-pressed="filterPriority === 'all'" @click="filterPriority = 'all'">全部</button>
            <button type="button" class="md-chip md-chip--filter" :class="{ 'is-selected': filterPriority === 'high' }" :aria-pressed="filterPriority === 'high'" @click="filterPriority = 'high'">🔴 高优</button>
            <button type="button" class="md-chip md-chip--filter" :class="{ 'is-selected': filterPriority === 'medium' }" :aria-pressed="filterPriority === 'medium'" @click="filterPriority = 'medium'">🟡 中优</button>
            <button type="button" class="md-chip md-chip--filter" :class="{ 'is-selected': filterPriority === 'low' }" :aria-pressed="filterPriority === 'low'" @click="filterPriority = 'low'">🟢 低优</button>
          </div>
        </div>

        <div class="search-item">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务名称或 Prompt 关键词..."
            clearable
            style="width: 250px"
            size="default"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>

      <div class="stats-badges">
        <button type="button" class="md-chip md-chip--filter" :class="{ 'is-selected': filterHasDirections }" :aria-pressed="filterHasDirections" title="只看所属项目有未处理指示的任务" @click="filterHasDirections = !filterHasDirections">
          💬 仅看有指示的项目
        </button>
        <span class="stat-chip md-chip md-chip--sm md-chip--primary">待调度 <strong>{{ todoTasks.length }}</strong></span>
        <span class="stat-chip md-chip md-chip--sm md-chip--warning">执行中 <strong>{{ inProgressTasks.length }}</strong></span>
        <span class="stat-chip md-chip md-chip--sm md-chip--success">已完成 <strong>{{ doneTasks.length }}</strong></span>
      </div>
    </section>

    <!-- 分类筛选：点标签即筛选 -->
    <section class="category-bar" role="group" aria-label="按分类筛选">
      <button type="button" class="md-chip md-chip--filter cat-chip" :class="{ 'is-selected': filterCategory === 'all' }" :aria-pressed="filterCategory === 'all'" @click="filterCategory = 'all'">
        全部 <strong>{{ tasks.length }}</strong>
      </button>
      <button
        v-for="c in TASK_CATEGORIES"
        :key="c.value"
        type="button"
        class="md-chip md-chip--filter cat-chip"
        :class="{ 'is-selected': filterCategory === c.value }"
        :aria-pressed="filterCategory === c.value"
        @click="filterCategory = c.value"
      >{{ c.icon }} {{ c.label }} <strong>{{ categoryCounts[c.value] || 0 }}</strong></button>
      <button type="button" class="md-chip md-chip--filter cat-chip" :class="{ 'is-selected': filterCategory === UNCATALOGUED }" :aria-pressed="filterCategory === UNCATALOGUED" @click="filterCategory = UNCATALOGUED">
        📎 未分类 <strong>{{ categoryCounts[UNCATALOGUED] || 0 }}</strong>
      </button>
      <el-button v-if="hasActiveFilter" link size="small" @click="clearFilters">清空筛选</el-button>
    </section>

    <!-- 项目指示条：有「未处理指示」的项目 -->
    <section v-if="directionSummaries.length" class="directions-strip md-callout md-callout--warning">
      <span class="directions-label">💬 项目指示</span>
      <button
        v-for="d in directionSummaries"
        :key="d.project_id"
        type="button"
        class="direction-chip"
        :class="{ cleared: d.open_count === 0, current: d.project_id === filterProject }"
        :title="d.latest ? d.latest.content.slice(0, 120) : '该项目没有未处理的指示'"
        @click="openDirections(d.project_id)"
      >
        <span class="chip-name">{{ d.project_name }}</span>
        <span class="chip-count">{{ d.open_count > 0 ? d.open_count : '✓' }}</span>
      </button>
    </section>

    <!-- 纵向分区：执行中 → 待调度 → 已完成（开合状态记在本地） -->

    <CollapsibleSection
      title="执行中 / Agent Running"
      :count="inProgressTasks.length"
      tone="running"
      v-model:open="fold.running"
      :hint="inProgressTasks.length === 0 ? '' : sectionHint('running')"
    >
      <template #actions><el-button text size="small" @click="openCreateModal('in_progress')"><el-icon><Plus /></el-icon> 添加</el-button></template>
      <div v-if="inProgressTasks.length === 0" class="col-empty"><div class="empty-icon">⚡</div><div class="empty-text">当前无执行中任务</div><div class="empty-sub">从「待调度」里点「▶ 开始执行」，再把 Prompt 粘给 dsh</div></div>
      <div v-if="inProgressTasks.length" class="task-grid">
        <template v-for="task in inProgressTasks" :key="task.id">
<TaskCard
            :task="task"
            :project-name="getProjectName(task.project_id)"
            :direction-count="directionCountFor(task.project_id)"
            @copy="copyPrompt(task)"
            @command="(cmd: string) => handleTaskCommand(cmd, task)"
            @filter-project="(pid: number) => (filterProject = pid)"
            @open-directions="openDirections"
          />
        </template>
      </div>
      
    </CollapsibleSection>

    <CollapsibleSection
      title="待调度 / 待办池 (Backlog)"
      :count="todoTasks.length"
      tone="todo"
      v-model:open="fold.todo"
      :hint="todoTasks.length === 0 ? '' : sectionHint('todo')"
    >
      <template #actions><el-button text size="small" @click="openCreateModal('todo')"><el-icon><Plus /></el-icon> 添加</el-button></template>
      <div v-if="todoTasks.length === 0" class="col-empty"><div class="empty-icon">📂</div><div class="empty-text">待办池为空</div><el-button size="small" type="primary" plain @click="router.push('/ideas')">前往灵感工坊推演任务 →</el-button></div>
      <div v-if="todoTasks.length" class="task-grid">
        <template v-for="task in todoTasks" :key="task.id">
<TaskCard
            :task="task"
            :project-name="getProjectName(task.project_id)"
            :direction-count="directionCountFor(task.project_id)"
            @copy="copyPrompt(task)"
            @command="(cmd: string) => handleTaskCommand(cmd, task)"
            @filter-project="(pid: number) => (filterProject = pid)"
            @open-directions="openDirections"
          />
        </template>
      </div>
      
    </CollapsibleSection>

    <CollapsibleSection
      title="已完成 / Done"
      :count="doneTasks.length"
      tone="done"
      v-model:open="fold.done"
      :hint="visibleDoneTasks.length === 0 ? '' : sectionHint('done')"
    >
      <template #actions></template>
      <div v-if="doneTasks.length === 0" class="col-empty"><div class="empty-icon">🎯</div><div class="empty-text">暂无已完成工单</div></div>
      <div v-if="visibleDoneTasks.length" class="task-grid">
        <template v-for="task in visibleDoneTasks" :key="task.id">
<TaskCard
            :task="task"
            :project-name="getProjectName(task.project_id)"
            :direction-count="directionCountFor(task.project_id)"
            @copy="copyPrompt(task)"
            @command="(cmd: string) => handleTaskCommand(cmd, task)"
            @filter-project="(pid: number) => (filterProject = pid)"
            @open-directions="openDirections"
          />
        </template>
      </div>
      <div v-if="doneTasks.length > DONE_PREVIEW" class="done-more">
        <el-button text type="primary" @click="expandedDone = !expandedDone">
          {{ expandedDone ? '收起（只看最近 ' + DONE_PREVIEW + ' 条）' : '展开全部 ' + doneTasks.length + ' 条' }}
        </el-button>
      </div>
    </CollapsibleSection>


    <!-- 创建 / 编辑工单弹窗 -->
    <el-dialog
      v-model="modalVisible"
      :title="isEditing ? '编辑工单' : '新建 AI 调度工单'"
      width="640px"
      append-to-body
      destroy-on-close
    >
      <el-form label-position="top" :model="form">
        <el-form-item required>
          <template #label>
            <div class="form-label-with-btn">
              <span>所属独立项目</span>
              <el-button link size="small" type="primary" @click="quickCreateProject">+ 新建独立项目</el-button>
            </div>
          </template>
          <el-select v-model="form.project_id" style="width: 100%" filterable>
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类（可留空）">
          <el-select v-model="form.category" style="width: 100%" clearable placeholder="未分类">
            <el-option v-for="c in TASK_CATEGORIES" :key="c.value" :label="c.icon + ' ' + c.label" :value="c.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="工单标题 / 核心目标" required>
          <el-input v-model="form.name" placeholder="简要概括目标，例如：重构前端设计规范与适配深色模式" />
        </el-form-item>

        <div class="form-row-2">
          <el-form-item label="优先级">
            <el-select v-model="form.priority" style="width: 100%">
              <el-option label="🔴 高优 (High)" value="high" />
              <el-option label="🟡 中优 (Medium)" value="medium" />
              <el-option label="🟢 低优 (Low)" value="low" />
            </el-select>
          </el-form-item>
          <el-form-item label="预估工时 (小时)">
            <el-input-number v-model="form.estimated_hours" :min="1" :max="24" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item label="执行要求与 AI Agent Prompt">
          <div class="preset-buttons">
            <span class="preset-label">快捷 Prompt:</span>
            <el-button size="small" @click="applyTemplate('refactor')">🛠️ 重构</el-button>
            <el-button size="small" @click="applyTemplate('test')">🧪 测试</el-button>
            <el-button size="small" @click="applyTemplate('bugfix')">🐛 排错</el-button>
            <el-button size="small" @click="applyTemplate('feature')">✨ 特性</el-button>
          </div>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="6"
            placeholder="写下具体的上下文、要求、验收标准或直接粘贴 Agent Prompt..."
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="modalVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存工单</el-button>
      </template>
    </el-dialog>

    <!-- 夜班无人值守批量指令弹窗 -->
    <el-dialog
      v-model="batchModalVisible"
      title="🌙 夜间无人值守开发批次指令 (dsh Batch Dispatch)"
      width="700px"
      append-to-body
    >
      <p class="batch-tip">
        已自动将当前待办池中的 <strong>{{ todoTasks.length }}</strong> 项工单打包为结构化自主开发 Prompt。睡前直接复制并粘贴到 dsh 对话框中，让 AI 在夜间充分消耗 5h 算力窗口！
      </p>

      <el-input
        v-model="batchPromptText"
        type="textarea"
        :rows="12"
        readonly
        class="batch-prompt-input"
      />

      <template #footer>
        <el-button @click="batchModalVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyBatchPrompt">
          📋 一键复制整包指令至剪贴板
        </el-button>
      </template>
    </el-dialog>

    <!-- 项目指示抽屉：留方向、标记已处理 -->
    <el-drawer v-model="directionsDrawer" title="💬 项目指示" size="520px" append-to-body destroy-on-close>
      <div class="directions-drawer">
        <el-select v-model="directionProjectId" style="width: 100%" filterable placeholder="选择项目">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id">
            <span>{{ p.name }}</span>
            <span v-if="directionCountFor(p.id) > 0" class="drawer-opt-count">💬 {{ directionCountFor(p.id) }}</span>
          </el-option>
        </el-select>
        <ProjectCommentsPanel
          v-if="directionProjectId"
          :key="directionProjectId"
          :project-id="directionProjectId"
          :project-name="getProjectName(directionProjectId)"
          @changed="loadDirections"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, CopyDocument, Compass } from '@element-plus/icons-vue'
import http from '@/api/http'
import { copyText } from '@/utils/clipboard'
import { TASK_CATEGORIES, UNCATALOGUED, categoryLabel } from '@/utils/taskCategory'
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import TaskCard from '@/components/TaskCard.vue'
import ProjectCommentsPanel from '@/components/ProjectCommentsPanel.vue'

/* ---------- 开合状态：记在本地，刷新后保持 ---------- */
const FOLD_KEY = 'hpf_cockpit_fold'
type FoldState = { running: boolean; todo: boolean; done: boolean }
function readFold(): FoldState {
  const defaults: FoldState = { running: true, todo: true, done: false }
  try {
    const raw = localStorage.getItem(FOLD_KEY)
    return raw ? { ...defaults, ...(JSON.parse(raw) as Partial<FoldState>) } : defaults
  } catch {
    return defaults
  }
}
const fold = reactive<FoldState>(readFold())
watch(fold, (v) => {
  try {
    localStorage.setItem(FOLD_KEY, JSON.stringify(v))
  } catch {
    /* 隐私模式等场景写不进去，忽略即可 */
  }
})

/* 已完成默认只露最近几条，避免把页面拉得很长 */
const DONE_PREVIEW = 12
const expandedDone = ref(false)

interface TaskItem {
  id: number
  project_id: number
  name: string
  description?: string
  priority: 'low' | 'medium' | 'high'
  status: 'todo' | 'in_progress' | 'done'
  progress: number
  estimated_hours?: number
  category?: string | null
  completed_at?: string
  created_at: string
}

interface DirectionSummary {
  project_id: number
  project_name: string
  open_count: number
  total_count: number
  latest: { id: number; content: string } | null
}

interface OpenDirection {
  id: number
  content: string
}

interface ProjectItem {
  id: number
  name: string
  description?: string
  status: string
}

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const tasks = ref<TaskItem[]>([])
const projects = ref<ProjectItem[]>([])
const quota = ref<any>({})
const driverMode = ref<any>({
  driver_mode: 'DUAL_CERTIFIED',
  mode_desc: '双重认证协同模式',
  has_internal_tokens: true,
  guidelines: '内部 MiniMax 算力充足，正在协同审核外部规划',
})

const filterProject = ref<number>(0)
const filterPriority = ref<string>('all')
const searchKeyword = ref<string>('')
const filterCategory = ref<string>('all')
const filterHasDirections = ref(false)

const modalVisible = ref(false)
const isEditing = ref(false)
const currentTaskId = ref<number | null>(null)

const form = ref({
  project_id: 1,
  name: '',
  priority: 'medium' as 'low' | 'medium' | 'high',
  status: 'todo',
  estimated_hours: 2,
  description: '',
  category: '',
})

/* ---------- 项目指示（负责人留给 Agent 的工作方向） ---------- */
const directionSummaries = ref<DirectionSummary[]>([])
// 各项目未处理指示的全文，按需拉取；复制 Prompt 时要带上具体内容和 id
const openDirectionsCache = ref<Record<number, OpenDirection[]>>({})
const directionsDrawer = ref(false)
const directionProjectId = ref<number | null>(null)

function directionCountFor(projectId: number): number {
  const s = directionSummaries.value.find((x) => x.project_id === projectId)
  return s ? s.open_count : 0
}

async function loadDirections() {
  try {
    directionSummaries.value = (await http.get('/comments/project-summary')) as any
  } catch {
    directionSummaries.value = []
  }
}

async function fetchOpenDirections(projectId: number): Promise<OpenDirection[]> {
  try {
    const rows: any = await http.get(`/projects/${projectId}/comments`)
    const list = (rows || []).filter((c: any) => !c.resolved).map((c: any) => ({ id: c.id, content: c.content }))
    openDirectionsCache.value = { ...openDirectionsCache.value, [projectId]: list }
    return list
  } catch {
    return openDirectionsCache.value[projectId] || []
  }
}

function openDirections(projectId?: number) {
  const pid =
    projectId ??
    (filterProject.value !== 0 ? filterProject.value : null) ??
    (directionSummaries.value.find((d) => d.open_count > 0)?.project_id ?? null) ??
    projects.value[0]?.id ??
    null
  directionProjectId.value = pid
  directionsDrawer.value = true
}
/* 复制 Prompt 时附在后面的指示块；没有未处理指示就返回空串 */
function formatDirectionsBlock(projectId: number, list: OpenDirection[]): string {
  if (!list.length) return ''
  const lines = list.map((d, i) => `${i + 1}. (id=${d.id}) ${d.content.length > 300 ? d.content.slice(0, 300) + '…' : d.content}`)
  return (
    `\n【项目指示】（负责人留言，必须遵守；落实后请用 MCP add_comment(project_id=${projectId}, resolve_ids=[对应id]) 标记已处理）:\n` +
    lines.join('\n')
  )
}

const batchModalVisible = ref(false)
const batchPromptText = ref('')

const quotaLevel = computed(() => {
  const p = quota.value.remaining_percent ?? 100
  if (p <= 10) return 'critical'
  if (p <= 30) return 'warning'
  return 'good'
})

function getProjectName(id: number) {
  const p = projects.value.find((x) => x.id === id)
  return p ? p.name : `项目 #${id}`
}

function priorityTag(p: string) {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}

function priorityLabel(p: string) {
  if (p === 'high') return '高优'
  if (p === 'medium') return '中优'
  return '低优'
}

function formatTime(ts: string) {
  if (!ts) return ''
  return ts.slice(0, 10)
}

const filteredTasks = computed(() => {
  return tasks.value.filter((t) => {
    if (filterProject.value !== 0 && t.project_id !== filterProject.value) return false
    if (filterPriority.value !== 'all' && t.priority !== filterPriority.value) return false
    if (filterCategory.value === UNCATALOGUED) {
      if (t.category) return false
    } else if (filterCategory.value !== 'all' && t.category !== filterCategory.value) return false
    if (filterHasDirections.value && directionCountFor(t.project_id) === 0) return false
    if (searchKeyword.value.trim()) {
      const q = searchKeyword.value.toLowerCase()
      const matchName = t.name.toLowerCase().includes(q)
      const matchDesc = (t.description || '').toLowerCase().includes(q)
      if (!matchName && !matchDesc) return false
    }
    return true
  })
})

// 排序：待办高优在前；已完成最近完成的在前
function byPriorityDesc(a: TaskItem, b: TaskItem) {
  const w = { high: 0, medium: 1, low: 2 }
  return w[a.priority] - w[b.priority]
}

const todoTasks = computed(() =>
  filteredTasks.value.filter((t) => t.status === 'todo').sort(byPriorityDesc),
)
const inProgressTasks = computed(() =>
  filteredTasks.value.filter((t) => t.status === 'in_progress').sort(byPriorityDesc),
)
const doneTasks = computed(() =>
  filteredTasks.value
    .filter((t) => t.status === 'done')
    .sort((a, b) => (b.completed_at || b.created_at).localeCompare(a.completed_at || a.created_at)),
)
const visibleDoneTasks = computed(() =>
  expandedDone.value ? doneTasks.value : doneTasks.value.slice(0, DONE_PREVIEW),
)

const categoryCounts = computed(() => {
  // 统计口径跟随「项目 / 优先级 / 关键词」，只忽略分类本身，方便横向比较各类数量
  const counts: Record<string, number> = {}
  for (const t of tasks.value) {
    if (filterProject.value !== 0 && t.project_id !== filterProject.value) continue
    if (filterPriority.value !== 'all' && t.priority !== filterPriority.value) continue
    if (searchKeyword.value.trim()) {
      const q = searchKeyword.value.toLowerCase()
      if (!t.name.toLowerCase().includes(q) && !(t.description || '').toLowerCase().includes(q)) continue
    }
    const key = t.category || UNCATALOGUED
    counts[key] = (counts[key] || 0) + 1
  }
  return counts
})

const hasActiveFilter = computed(
  () =>
    filterProject.value !== 0 ||
    filterPriority.value !== 'all' ||
    filterCategory.value !== 'all' ||
    filterHasDirections.value ||
    searchKeyword.value.trim() !== '',
)

function clearFilters() {
  filterProject.value = 0
  filterPriority.value = 'all'
  filterCategory.value = 'all'
  filterHasDirections.value = false
  searchKeyword.value = ''
}

/* 折叠时露在标题右侧的一句话摘要 */
function sectionHint(tone: string): string {
  if (tone === 'running') return inProgressTasks.value.map((t) => t.name).slice(0, 3).join(' · ')
  if (tone === 'todo') return todoTasks.value.slice(0, 3).map((t) => t.name).join(' · ')
  return doneTasks.value[0] ? `最近完成：${doneTasks.value[0].name}` : ''
}

// 正在筛选 / 搜索时把三个分区都撑开，免得「筛完没结果」看起来像数据丢了
let foldBeforeFilter: FoldState | null = null
watch(hasActiveFilter, (active) => {
  if (active) {
    // 先记下用户原本的开合习惯，筛选结束后还回去，别把「已完成保持折叠」永久冲掉
    foldBeforeFilter ??= { ...fold }
    fold.running = true
    fold.todo = true
    fold.done = true
  } else if (foldBeforeFilter) {
    Object.assign(fold, foldBeforeFilter)
    foldBeforeFilter = null
  }
})

const syncingProjects = ref(false)

async function syncLocalProjects() {
  syncingProjects.value = true
  try {
    const res: any = await http.post('/ideator/sync-projects')
    if (res && res.synced_count > 0) {
      ElMessage.success(`成功导入 ${res.synced_count} 个本地独立代码库项目！`)
    } else {
      ElMessage.info('本地所有代码库已全部建档为独立项目')
    }
    await loadData()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '同步项目失败')
  } finally {
    syncingProjects.value = false
  }
}

async function quickCreateProject() {
  try {
    const { value: name } = await ElMessageBox.prompt('请输入新独立项目名称（例如：my-new-app）', '新建独立项目', {
      confirmButtonText: '创建项目',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '项目名称不能为空',
    })
    if (name) {
      const newProj: any = await http.post('/projects', { name: name.trim(), status: 'active' })
      ElMessage.success(`独立项目「${name}」已创建！`)
      await loadData()
      form.value.project_id = newProj.id
      filterProject.value = newProj.id
    }
  } catch {}
}

async function loadData() {
  loading.value = true
  try {
    const [pRes, tRes, qRes, dRes] = await Promise.all([
      http.get('/projects?limit=200').catch(() => []),
      Promise.all([
        http.get('/tasks?status=todo&limit=500').catch(() => []),
        http.get('/tasks?status=in_progress&limit=500').catch(() => []),
        http.get('/tasks?status=done&limit=500').catch(() => []),
      ]).then((parts: any) => parts.flat()),
      http.get('/quota').catch(() => ({})),
      http.get('/quota/driver-mode').catch(() => ({})),
    ])
    projects.value = (pRes as any) || []
    tasks.value = (tRes as any) || []
    await loadDirections()
    quota.value = (qRes as any) || {}
    if ((dRes as any)?.driver_mode) {
      driverMode.value = dRes as any
    }
    if (projects.value.length > 0 && !form.value.project_id) {
      form.value.project_id = projects.value[0].id
    }
  } catch (err) {
    console.error('Failed to load cockpit data:', err)
  } finally {
    loading.value = false
  }
}

async function copyPrompt(task: TaskItem) {
  const pName = getProjectName(task.project_id)
  const directions = formatDirectionsBlock(
    task.project_id,
    task.status === 'done' ? [] : await fetchOpenDirections(task.project_id),
  )
  const text = `【项目】: ${pName}\n【任务】: ${task.name}\n【优先级】: ${priorityLabel(task.priority)}${task.category ? `\n【分类】: ${categoryLabel(task.category)}` : ''}\n【执行要求与 Prompt】:\n${task.description || '请阅读项目上下文完成此任务并运行测试验证。'}${directions}`
  const ok = await copyText(text)
  if (ok) {
    ElMessage.success(`📋 Prompt 已复制！可直接粘贴至 dsh 开始开发`)
  } else {
    ElMessage.info(`Prompt: ${text.slice(0, 80)}...`)
  }
}

async function moveToStatus(task: TaskItem, newStatus: 'todo' | 'in_progress' | 'done') {
  try {
    await http.put(`/tasks/${task.id}`, {
      status: newStatus,
      progress: newStatus === 'done' ? 100 : task.progress,
    })
    task.status = newStatus
    if (newStatus === 'done') {
      task.completed_at = new Date().toISOString()
      task.progress = 100
      ElMessage.success(`任务「${task.name}」已标记完成！`)
    } else if (newStatus === 'in_progress') {
      ElMessage.success(`任务「${task.name}」已转入执行中！`)
    } else {
      ElMessage.info(`任务「${task.name}」已移回待办池`)
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '状态更新失败')
  }
}

function handleTaskCommand(cmd: string, task: TaskItem) {
  if (cmd === 'edit') {
    editTask(task)
  } else if (cmd === 'start') {
    moveToStatus(task, 'in_progress')
  } else if (cmd.startsWith('category:')) {
    setCategory(task, cmd.slice('category:'.length))
  } else if (cmd === 'done') {
    moveToStatus(task, 'done')
  } else if (cmd === 'backlog') {
    moveToStatus(task, 'todo')
  } else if (cmd === 'delete') {
    deleteTask(task)
  }
}

/* 卡片上直接改分类；空串 = 改回未分类 */
async function setCategory(task: TaskItem, category: string) {
  try {
    const res: any = await http.put(`/tasks/${task.id}`, { category: category || null })
    task.category = res?.category ?? (category || null)
    ElMessage.success(category ? `已设为「${categoryLabel(category)}」` : '已改回未分类')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '分类更新失败')
  }
}

function openCreateModal(status = 'todo') {
  isEditing.value = false
  currentTaskId.value = null
  const defaultPid = filterProject.value !== 0 ? filterProject.value : (projects.value[0]?.id || 1)
  form.value = {
    project_id: defaultPid,
    name: '',
    priority: 'medium',
    status: status,
    estimated_hours: 2,
    description: '',
    // 正在看某个分类就沿用，省一次选择
    category: filterCategory.value !== 'all' && filterCategory.value !== UNCATALOGUED ? filterCategory.value : '',
  }
  modalVisible.value = true
}

function editTask(task: TaskItem) {
  isEditing.value = true
  currentTaskId.value = task.id
  form.value = {
    project_id: task.project_id,
    name: task.name,
    priority: task.priority,
    status: task.status,
    estimated_hours: task.estimated_hours || 2,
    description: task.description || '',
    category: task.category || '',
  }
  modalVisible.value = true
}

async function submitForm() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入工单标题')
    return
  }
  saving.value = true
  try {
    if (isEditing.value && currentTaskId.value) {
      await http.put(`/tasks/${currentTaskId.value}`, {
        name: form.value.name,
        priority: form.value.priority,
        estimated_hours: form.value.estimated_hours,
        description: form.value.description,
        category: form.value.category || null,
      })
      ElMessage.success('工单修改成功')
    } else {
      await http.post(`/projects/${form.value.project_id}/tasks`, {
        name: form.value.name,
        priority: form.value.priority,
        status: form.value.status,
        estimated_hours: form.value.estimated_hours,
        description: form.value.description,
        category: form.value.category || null,
      })
      ElMessage.success('工单创建成功！已放入看板')
    }
    modalVisible.value = false
    await loadData()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteTask(task: TaskItem) {
  try {
    await ElMessageBox.confirm(`确定要删除工单「${task.name}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await http.delete(`/tasks/${task.id}`)
    ElMessage.success('已删除工单')
    tasks.value = tasks.value.filter((t) => t.id !== task.id)
  } catch {}
}

function applyTemplate(type: string) {
  // 模板与分类一一对应，选了模板就默认归类
  form.value.category = type === 'test' ? 'testing' : type
  if (type === 'refactor') {
    form.value.description =
      '【目标】重构此模块代码结构，消除重复逻辑并提升可读性。\n【执行准则】保持向后兼容，外部 API 签名不变，重构后运行测试验证。\n【输出要求】提供 git diff 与改动说明。'
  } else if (type === 'test') {
    form.value.description =
      '【目标】为当前核心模块编写单元测试与边界用例。\n【执行准则】覆盖正常流程、非法输入与异常处理。\n【输出要求】执行对应测试框架命令确保全部 PASS。'
  } else if (type === 'bugfix') {
    form.value.description =
      '【目标】排查并修复当前缺陷。\n【排查思路】分析调用链与报错上下文，设计防御性修复代码。\n【验证要求】编写回归测试确保缺陷不再复现。'
  } else if (type === 'feature') {
    form.value.description =
      '【目标】实现新功能特性。\n【技术要求】遵循现有工程架构与类型规范，保持代码优雅简洁。\n【交付要求】实现功能并配套单元测试。'
  }
}

async function openBatchPromptModal() {
  const pending = todoTasks.value
  if (pending.length === 0) {
    ElMessage.info('待办池中暂无任务，请先添加工单')
    return
  }

  let prompt = `# 🌙 夜间无人值守自主开发任务包 (Night-Shift Dispatch)\n`
  prompt += `你是自主开发 AI Agent。当前为无人值守时间，请依次推进完成以下 ${pending.length} 项任务：\n\n`

  pending.forEach((item, index) => {
    prompt += `### 任务 ${index + 1}: ${item.name}\n`
    prompt += `- 所属项目: ${getProjectName(item.project_id)}\n`
    prompt += `- 优先级: ${priorityLabel(item.priority)}\n`
    prompt += `- 详情与执行要求:\n${item.description || '阅读项目代码实现此目标。'}\n\n`
  })

  // 相关项目的未处理指示（Agent 夜间无人可问，方向必须在包里）
  const pids = [...new Set(pending.map((t) => t.project_id))]
  const directionParts: string[] = []
  for (const pid of pids) {
    const block = formatDirectionsBlock(pid, await fetchOpenDirections(pid))
    if (block) directionParts.push(`◆ ${getProjectName(pid)}${block}`)
  }
  if (directionParts.length) {
    prompt += `==================================================\n`
    prompt += `【各项目负责人的指示】（开工前先读；落实后用 add_comment(resolve_ids=[...]) 标记已处理）\n`
    prompt += directionParts.join('\n') + `\n\n`
  }

  prompt += `--------------------------------------------------\n`
  prompt += `【自主开发执行准则】\n`
  prompt += `1. 依次执行各任务，每项完成后自动运行测试验证并执行 git commit；\n`
  prompt += `2. 若遇编译/测试报错，请自行排查修复，直至测试全通；\n`
  prompt += `3. 全部任务完成后，在终端输出最终执行报告。\n`

  batchPromptText.value = prompt
  batchModalVisible.value = true
}

async function copyBatchPrompt() {
  const ok = await copyText(batchPromptText.value)
  if (ok) {
    ElMessage.success('📋 夜班整包指令已复制！可直接粘贴至 dsh 开始开发')
  } else {
    ElMessage.info('未能自动写入剪贴板，请全选上方文本框手动复制')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.cockpit-container {
  max-width: var(--md-content-max);
  margin: 0 auto;
  padding: var(--md-space-3) var(--md-space-5) var(--md-space-7);
}

/* 顶部状态：只靠间距与标题分组，不套框 */
.cockpit-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--md-space-3);
  padding: var(--md-space-2) 0 var(--md-space-5);
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-2);
}

.quota-row {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  flex-wrap: wrap;
}

/* 驱动模式：只读状态芯片（双重认证=primary，外部驱动=warning） */
.driver-mode-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  padding: 0 var(--md-space-3);
  height: 24px;
  border-radius: var(--md-shape-small);
  font-size: var(--md-type-label-md);
  font-weight: var(--md-weight-medium);
  cursor: default;
}

.driver-mode-pill.dual {
  background: var(--md-primary-container);
  color: var(--md-on-primary-container);
}

.driver-mode-pill.external {
  background: var(--md-warning-container);
  color: var(--md-on-warning-container);
}

/* 算力窗口：可点的状态芯片（md-chip 提供底色，这里只管手势） */
.quota-pill {
  cursor: pointer;
  width: fit-content;
}

.quota-pill:hover {
  text-decoration: underline;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.live-dot.good { background: var(--md-success); }
.live-dot.warning { background: var(--md-warning); }
.live-dot.critical { background: var(--md-error); }

.pill-label { color: var(--md-on-surface-variant); }
.pill-divider { color: var(--md-outline); }
.pill-timer { font-size: var(--md-type-label-md); color: var(--md-on-surface-variant); }

.hero-subtext {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  font-size: var(--md-type-body-sm);
}

.night-badge {
  background: var(--md-primary-container);
  color: var(--md-on-primary-container);
  padding: 2px var(--md-space-2);
  border-radius: var(--md-shape-extra-small);
  font-weight: var(--md-weight-medium);
}

.sugg-text {
  color: var(--md-on-surface-variant);
}

.hero-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--md-space-2);
}

/* 筛选工具栏：无外框，一行可换行的筛选控件 */
.project-select {
  width: 220px;
  max-width: 100%;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--md-space-2) var(--md-space-4);
  padding: var(--md-space-2) 0 var(--md-space-4);
}

.filter-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--md-space-2) var(--md-space-4);
}

.filter-item {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  flex-wrap: wrap;
  min-width: 0;
}

.chip-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--md-space-1);
}

.item-label {
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}

.stats-badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--md-space-2);
}

/* ---------- 分区内容 ---------- */
.col-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md-space-1);
  padding: var(--md-space-6) var(--md-space-3);
  text-align: center;
  color: var(--md-on-surface-variant);
}

.empty-icon { font-size: var(--md-type-display-sm); line-height: 1; margin-bottom: var(--md-space-1); }
.empty-text { font-size: var(--md-type-title-sm); font-weight: var(--md-weight-medium); color: var(--md-on-surface); }
.empty-sub { font-size: var(--md-type-body-sm); color: var(--md-on-surface-variant); }
.col-empty .el-button { margin-top: var(--md-space-2); }

.form-label-with-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

/* 模态框样式 */
.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md-space-4);
}

.preset-buttons {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  margin-bottom: var(--md-space-2);
  flex-wrap: wrap;
}

.preset-label {
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
}

.batch-tip {
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
  line-height: 1.5;
  margin-bottom: var(--md-space-3);
}

.batch-prompt-input textarea {
  font-family: var(--md-font-mono);
  font-size: var(--md-type-body-sm);
  line-height: 1.5;
}

/* ---------- 纵向分区的卡片网格：按宽度自动换行，每张卡至少 ~330px ---------- */
.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: var(--md-space-3);
  align-items: start;
}

.done-more {
  text-align: center;
  padding-top: var(--md-space-2);
}

/* ---------- 分类筛选条：全部是筛选芯片，选中态由 .is-selected 表达 ---------- */
.category-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--md-space-1);
  padding: 0 0 var(--md-space-3);
}

.cat-chip strong {
  font-weight: var(--md-weight-medium);
  opacity: 0.75;
}

/* ---------- 项目指示条：色调提示块 ---------- */
.directions-strip {
  flex-wrap: wrap;
  gap: var(--md-space-2);
  margin-bottom: var(--md-space-4);
  padding: var(--md-space-2) var(--md-space-3);
}

.directions-label {
  font-size: var(--md-type-label-md);
  font-weight: var(--md-weight-medium);
  margin-right: var(--md-space-1);
}

.direction-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  padding: var(--md-space-1) var(--md-space-3);
  border-radius: var(--md-shape-small);
  border: 0;
  background: var(--md-surface-container-high);
  font: inherit;
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface);
  cursor: pointer;
  transition: background-color var(--md-duration-short-2) var(--md-ease-standard);
}

.direction-chip:hover {
  background: var(--md-surface-container-highest);
}

.direction-chip.current {
  background: var(--md-secondary-container);
  color: var(--md-on-secondary-container);
}

.direction-chip.cleared {
  color: var(--md-on-surface-variant);
  opacity: 0.72;
}

.chip-name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 var(--md-space-1);
  border-radius: var(--md-shape-full);
  background: var(--md-warning-container);
  color: var(--md-on-warning-container);
  font-size: var(--md-type-label-sm);
  font-weight: var(--md-weight-medium);
}

.direction-chip.cleared .chip-count {
  background: var(--md-success-container);
  color: var(--md-on-success-container);
}

.directions-drawer {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-3);
}

.drawer-opt-count {
  float: right;
  font-size: var(--md-type-body-sm);
  color: var(--md-on-warning);
}

@media (max-width: 720px) {
  .cockpit-container { padding: var(--md-space-3); }
  .cockpit-hero { align-items: stretch; }
  .task-grid { grid-template-columns: 1fr; }
}
</style>
