<template>
  <div class="cockpit-container" v-loading="loading">
    <!-- 顶部状态看板与快捷调度条 -->
    <section class="cockpit-hero">
      <div class="hero-left">
        <div class="quota-row">
          <div class="quota-pill" :class="quotaLevel" @click="router.push('/quota')">
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
        <el-button size="default" circle @click="loadData" :loading="loading" title="刷新看板">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </section>

    <!-- 筛选过滤与统计栏 -->
    <section class="filter-toolbar">
      <div class="filter-left">
        <div class="filter-item">
          <span class="item-label">项目:</span>
          <el-select v-model="filterProject" placeholder="全部项目" style="width: 220px" size="default" filterable>
            <el-option label="🌐 全部项目 (All Projects)" :value="0" />
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-button size="default" :loading="syncingProjects" @click="syncLocalProjects" title="扫描服务器本地目录，自动将新代码库建档为独立项目">
            📥 同步本地项目库
          </el-button>
        </div>

        <div class="filter-item">
          <span class="item-label">优先级:</span>
          <el-select v-model="filterPriority" placeholder="全部" style="width: 110px" size="default">
            <el-option label="全部" value="all" />
            <el-option label="🔴 高优" value="high" />
            <el-option label="🟡 中优" value="medium" />
            <el-option label="🟢 低优" value="low" />
          </el-select>
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
        <span class="stat-chip todo">待调度: <strong>{{ todoTasks.length }}</strong></span>
        <span class="stat-chip in-progress">执行中: <strong>{{ inProgressTasks.length }}</strong></span>
        <span class="stat-chip done">已完成: <strong>{{ doneTasks.length }}</strong></span>
      </div>
    </section>

    <!-- 3列任务流水线看板 (Agent Kanban Pipeline) -->
    <div class="kanban-grid">
      <!-- 列 1: 待调度 / 待办池 -->
      <div class="kanban-column col-todo">
        <div class="column-header">
          <div class="col-title-group">
            <span class="col-dot dot-todo"></span>
            <span class="col-title">待调度 / 待办池 (Backlog)</span>
            <span class="col-badge">{{ todoTasks.length }}</span>
          </div>
          <el-button link size="small" type="primary" @click="openCreateModal('todo')">
            <el-icon><Plus /></el-icon> 添加
          </el-button>
        </div>

        <div class="column-body">
          <div v-if="todoTasks.length === 0" class="col-empty">
            <div class="empty-icon">📂</div>
            <div class="empty-text">待办池为空</div>
            <el-button link size="small" type="primary" @click="router.push('/ideas')">前往灵感工坊推演任务 →</el-button>
          </div>

          <div
            v-for="task in todoTasks"
            :key="task.id"
            class="task-card"
          >
            <div class="card-meta">
              <span class="project-tag clickable" @click="filterProject = task.project_id" title="点击仅筛选该独立项目工单">{{ getProjectName(task.project_id) }}</span>
              <el-tag size="small" :type="priorityTag(task.priority)" effect="light">
                {{ priorityLabel(task.priority) }}
              </el-tag>
              <span v-if="task.estimated_hours" class="hours-tag">⏱️ {{ task.estimated_hours }}h</span>
            </div>

            <h4 class="card-title">{{ task.name }}</h4>

            <div v-if="task.description" class="prompt-preview">
              <div class="prompt-header">
                <span>Agent Prompt 预览</span>
                <button class="mini-copy-btn" @click.stop="copyPrompt(task)">📋 复制</button>
              </div>
              <div class="prompt-text">{{ task.description }}</div>
            </div>

            <div class="card-footer">
              <button class="action-btn copy-btn" @click="copyPrompt(task)">
                📋 复制 Prompt
              </button>
              <div class="footer-right">
                <el-button size="small" type="primary" plain @click="moveToStatus(task, 'in_progress')">
                  ▶ 开始执行
                </el-button>
                <el-dropdown trigger="click" @command="(cmd: string) => handleTaskCommand(cmd, task)">
                  <el-button size="small" circle text class="more-btn">···</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">编辑工单</el-dropdown-item>
                      <el-dropdown-item command="done">直接标记完成</el-dropdown-item>
                      <el-dropdown-item command="delete" divided style="color: var(--md-error)">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 列 2: 执行中 / Agent Running -->
      <div class="kanban-column col-running">
        <div class="column-header">
          <div class="col-title-group">
            <span class="col-dot dot-running"></span>
            <span class="col-title">执行中 / Agent Running</span>
            <span class="col-badge">{{ inProgressTasks.length }}</span>
          </div>
          <el-button link size="small" type="primary" @click="openCreateModal('in_progress')">
            <el-icon><Plus /></el-icon> 添加
          </el-button>
        </div>

        <div class="column-body">
          <div v-if="inProgressTasks.length === 0" class="col-empty">
            <div class="empty-icon">⚡</div>
            <div class="empty-text">当前无执行中任务</div>
            <div class="empty-sub">从待办池点击「开始执行」并将 Prompt 粘给 dsh</div>
          </div>

          <div
            v-for="task in inProgressTasks"
            :key="task.id"
            class="task-card is-active"
          >
            <div class="card-meta">
              <span class="project-tag clickable" @click="filterProject = task.project_id" title="点击仅筛选该独立项目工单">{{ getProjectName(task.project_id) }}</span>
              <el-tag size="small" :type="priorityTag(task.priority)" effect="light">
                {{ priorityLabel(task.priority) }}
              </el-tag>
              <span class="running-indicator"><span class="pulse-ring"></span> 开发中</span>
            </div>

            <h4 class="card-title">{{ task.name }}</h4>

            <div v-if="task.description" class="prompt-preview">
              <div class="prompt-header">
                <span>Agent Prompt 预览</span>
                <button class="mini-copy-btn" @click.stop="copyPrompt(task)">📋 复制</button>
              </div>
              <div class="prompt-text">{{ task.description }}</div>
            </div>

            <div class="card-footer">
              <button class="action-btn copy-btn" @click="copyPrompt(task)">
                📋 复制 Prompt
              </button>
              <div class="footer-right">
                <el-button size="small" type="success" @click="moveToStatus(task, 'done')">
                  ✓ 完成
                </el-button>
                <el-dropdown trigger="click" @command="(cmd: string) => handleTaskCommand(cmd, task)">
                  <el-button size="small" circle text class="more-btn">···</el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="backlog">放回待办</el-dropdown-item>
                      <el-dropdown-item command="edit">编辑工单</el-dropdown-item>
                      <el-dropdown-item command="delete" divided style="color: var(--md-error)">删除</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 列 3: 已完成 (Done) -->
      <div class="kanban-column col-done">
        <div class="column-header">
          <div class="col-title-group">
            <span class="col-dot dot-done"></span>
            <span class="col-title">已完成 / Done</span>
            <span class="col-badge">{{ doneTasks.length }}</span>
          </div>
        </div>

        <div class="column-body">
          <div v-if="doneTasks.length === 0" class="col-empty">
            <div class="empty-icon">🎯</div>
            <div class="empty-text">暂无已完成工单</div>
          </div>

          <div
            v-for="task in doneTasks"
            :key="task.id"
            class="task-card is-done"
          >
            <div class="card-meta">
              <span class="project-tag clickable" @click="filterProject = task.project_id" title="点击仅筛选该独立项目工单">{{ getProjectName(task.project_id) }}</span>
              <span class="done-check">✓ 已归档</span>
              <span class="time-done" v-if="task.completed_at">{{ formatTime(task.completed_at) }}</span>
            </div>

            <h4 class="card-title strike">{{ task.name }}</h4>

            <div class="card-footer done-footer">
              <el-button size="small" link @click="moveToStatus(task, 'todo')">
                ↩ 重启任务
              </el-button>
              <el-button size="small" link type="danger" @click="deleteTask(task)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, CopyDocument, Compass } from '@element-plus/icons-vue'
import http from '@/api/http'
import { copyText } from '@/utils/clipboard'

interface TaskItem {
  id: number
  project_id: number
  name: string
  description?: string
  priority: 'low' | 'medium' | 'high'
  status: 'todo' | 'in_progress' | 'done'
  progress: number
  estimated_hours?: number
  completed_at?: string
  created_at: string
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
})

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
    if (searchKeyword.value.trim()) {
      const q = searchKeyword.value.toLowerCase()
      const matchName = t.name.toLowerCase().includes(q)
      const matchDesc = (t.description || '').toLowerCase().includes(q)
      if (!matchName && !matchDesc) return false
    }
    return true
  })
})

const todoTasks = computed(() => filteredTasks.value.filter((t) => t.status === 'todo'))
const inProgressTasks = computed(() => filteredTasks.value.filter((t) => t.status === 'in_progress'))
const doneTasks = computed(() => filteredTasks.value.filter((t) => t.status === 'done'))

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
      http.get('/tasks?limit=500').catch(() => []),
      http.get('/quota').catch(() => ({})),
      http.get('/quota/driver-mode').catch(() => ({})),
    ])
    projects.value = (pRes as any) || []
    tasks.value = (tRes as any) || []
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
  const text = `【项目】: ${pName}\n【任务】: ${task.name}\n【优先级】: ${priorityLabel(task.priority)}\n【执行要求与 Prompt】:\n${task.description || '请阅读项目上下文完成此任务并运行测试验证。'}`
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
  } else if (cmd === 'done') {
    moveToStatus(task, 'done')
  } else if (cmd === 'backlog') {
    moveToStatus(task, 'todo')
  } else if (cmd === 'delete') {
    deleteTask(task)
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
      })
      ElMessage.success('工单修改成功')
    } else {
      await http.post(`/projects/${form.value.project_id}/tasks`, {
        name: form.value.name,
        priority: form.value.priority,
        status: form.value.status,
        estimated_hours: form.value.estimated_hours,
        description: form.value.description,
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

function openBatchPromptModal() {
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
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 24px;
}

/* 顶部状态 Hero */
.cockpit-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--md-surface-container, #f1f2f4);
  border: 1px solid var(--md-outline-variant, #e0e2e8);
  border-radius: 12px;
  padding: 14px 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quota-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.driver-mode-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: default;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.driver-mode-pill.dual {
  background: rgba(22, 119, 255, 0.1);
  color: #1677ff;
  border-color: rgba(22, 119, 255, 0.25);
}

.driver-mode-pill.external {
  background: rgba(250, 140, 22, 0.1);
  color: #fa8c16;
  border-color: rgba(250, 140, 22, 0.25);
}

.quota-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--md-surface, #ffffff);
  border: 1px solid var(--md-outline-variant, #d0d3da);
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 13px;
  cursor: pointer;
  width: fit-content;
  transition: all 0.2s ease;
}

.quota-pill:hover {
  border-color: var(--md-primary, #0066cc);
  transform: translateY(-1px);
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.live-dot.good { background: #52c41a; box-shadow: 0 0 6px rgba(82, 196, 26, 0.6); }
.live-dot.warning { background: #faad14; box-shadow: 0 0 6px rgba(250, 173, 20, 0.6); }
.live-dot.critical { background: #ff4d4f; box-shadow: 0 0 6px rgba(255, 77, 79, 0.6); }

.pill-label { color: var(--md-on-surface-variant, #666); }
.pill-divider { color: #ccc; }
.pill-timer { font-size: 12px; color: var(--md-on-surface-variant, #666); }

.hero-subtext {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.night-badge {
  background: rgba(114, 46, 209, 0.12);
  color: #722ed1;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.sugg-text {
  color: var(--md-on-surface-variant, #555);
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 筛选工具栏 */
.filter-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  background: var(--md-surface, #ffffff);
  border: 1px solid var(--md-outline-variant, #e8eaee);
  border-radius: 8px;
  padding: 10px 16px;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.item-label {
  font-size: 13px;
  color: var(--md-on-surface-variant, #666);
}

.stats-badges {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-chip {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--md-surface-container, #f1f2f4);
  color: var(--md-on-surface-variant, #555);
}

.stat-chip.todo strong { color: #0066cc; }
.stat-chip.in-progress strong { color: #fa8c16; }
.stat-chip.done strong { color: #52c41a; }

/* 3 列看板流水线 */
.kanban-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  align-items: start;
}

.kanban-column {
  background: var(--md-surface-container-low, #f7f8fa);
  border: 1px solid var(--md-outline-variant, #e8eaee);
  border-radius: 12px;
  padding: 14px;
  min-height: 550px;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--md-outline-variant, #eaecf0);
}

.col-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot-todo { background: #0066cc; }
.dot-running { background: #fa8c16; }
.dot-done { background: #52c41a; }

.col-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--md-on-surface, #1d1d1f);
}

.col-badge {
  background: var(--md-surface-container-high, #e4e6ea);
  color: var(--md-on-surface-variant, #444);
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
  font-weight: 600;
}

.column-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.col-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 10px;
  text-align: center;
  color: var(--md-on-surface-variant, #888);
}

.empty-icon { font-size: 28px; margin-bottom: 8px; }
.empty-text { font-size: 13px; font-weight: 500; }
.empty-sub { font-size: 12px; margin-top: 4px; color: #999; }

/* 任务卡片 */
.task-card {
  background: var(--md-surface, #ffffff);
  border: 1px solid var(--md-outline-variant, #e2e4e8);
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.task-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #c0c4cc;
}

.task-card.is-active {
  border-left: 3px solid #fa8c16;
}

.task-card.is-done {
  opacity: 0.78;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.project-tag.clickable {
  cursor: pointer;
  transition: all 0.15s ease;
}
.project-tag.clickable:hover {
  background: var(--md-primary-container, #cfe3ff);
  color: var(--md-primary, #0066cc);
}
.form-label-with-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.project-tag {
  font-size: 11px;
  color: var(--md-on-surface-variant, #666);
  background: var(--md-surface-container, #f1f2f4);
  padding: 2px 6px;
  border-radius: 4px;
}

.hours-tag {
  font-size: 11px;
  color: var(--md-on-surface-variant, #888);
  margin-left: auto;
}

.running-indicator {
  margin-left: auto;
  font-size: 11px;
  color: #fa8c16;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.pulse-ring {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fa8c16;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.5; }
  100% { transform: scale(0.9); opacity: 1; }
}

.done-check {
  font-size: 11px;
  color: #52c41a;
  font-weight: 600;
}

.time-done {
  margin-left: auto;
  font-size: 11px;
  color: #999;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px 0;
  line-height: 1.4;
  color: var(--md-on-surface, #1d1d1f);
}

.card-title.strike {
  text-decoration: line-through;
  color: #888;
}

.prompt-preview {
  background: var(--md-surface-container-low, #f8f9fa);
  border: 1px solid var(--md-outline-variant, #eaedf1);
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 12px;
}

.prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--md-on-surface-variant, #888);
  margin-bottom: 4px;
}

.mini-copy-btn {
  background: none;
  border: none;
  color: #0066cc;
  cursor: pointer;
  font-size: 11px;
  padding: 0;
}
.mini-copy-btn:hover { text-decoration: underline; }

.prompt-text {
  font-size: 12px;
  line-height: 1.4;
  color: var(--md-on-surface, #333);
  white-space: pre-wrap;
  max-height: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px dashed var(--md-outline-variant, #eaedf1);
}

.card-footer.done-footer {
  justify-content: flex-end;
  gap: 12px;
}

.action-btn.copy-btn {
  background: var(--md-surface-container, #f0f2f5);
  border: 1px solid var(--md-outline-variant, #dcdfe6);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--md-on-surface, #2c3e50);
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn.copy-btn:hover {
  background: #e6f7ff;
  border-color: #91d5ff;
  color: #0066cc;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.more-btn {
  color: #888;
}

/* 模态框样式 */
.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.preset-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.preset-label {
  font-size: 12px;
  color: var(--md-on-surface-variant, #666);
}

.batch-tip {
  font-size: 13px;
  color: var(--md-on-surface-variant, #555);
  line-height: 1.5;
  margin-bottom: 12px;
}

.batch-prompt-input textarea {
  font-family: var(--md-font-mono, monospace);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 1024px) {
  .kanban-grid {
    grid-template-columns: 1fr;
  }
}
</style>
