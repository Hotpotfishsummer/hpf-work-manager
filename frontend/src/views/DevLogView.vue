<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <h1 class="page-title">开发记录</h1>
        <p class="page-sub">{{ project?.name }} · Dev Log · 进度/难点/待办/决策</p>
      </div>
      <div class="head-actions">
        <LiveIndicator :connected="connected" :is-reconnectable="reconnectable" @reconnect="reconnect" />
        <el-button text size="large" @click="router.push(`/projects/${pid}`)">返回概览</el-button>
        <el-button plain size="large" @click="openCreate">新建记录</el-button>
        <el-button size="large" type="primary" @click="openReport">生成开发汇报</el-button>
      </div>
    </div>

    <!-- 指标卡：填充式卡片，标签用色调芯片 -->
    <div class="stats-row">
      <div class="md-card spec-cell"><span class="spec-value">{{ stats?.total ?? 0 }}</span><span class="md-chip md-chip--sm md-chip--secondary">总记录</span></div>
      <div class="md-card spec-cell"><span class="spec-value">{{ stats?.today_count ?? 0 }}</span><span class="md-chip md-chip--sm md-chip--secondary">今日</span></div>
      <div class="md-card spec-cell"><span class="spec-value">{{ stats?.open_difficulties ?? 0 }}</span><span class="md-chip md-chip--sm md-chip--warning">难点</span></div>
      <div class="md-card spec-cell"><span class="spec-value">{{ stats?.open_todos ?? 0 }}</span><span class="md-chip md-chip--sm md-chip--neutral">待办</span></div>
      <div class="md-card spec-cell"><span class="spec-value">{{ stats?.open_blockers ?? 0 }}</span><span class="md-chip md-chip--sm md-chip--error">阻塞</span></div>
      <div class="md-card spec-cell"><span class="spec-value">{{ stats?.decisions ?? 0 }}</span><span class="md-chip md-chip--sm md-chip--primary">决策</span></div>
    </div>

    <!-- 筛选 + 会话 -->
    <div class="toolbar">
      <el-select v-model="filters.entry_type" clearable placeholder="全部类型" style="width: 150px">
        <el-option v-for="t in TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px">
        <el-option label="进行中" value="open" />
        <el-option label="已完成" value="done" />
      </el-select>
      <div class="session-bar">
        <el-button size="large" v-if="activeSession" @click="endSession">
          {{ activeSession.title || '开发会话' }} · 结束
        </el-button>
        <el-button size="large" type="primary" plain v-else @click="startSession">开始会话</el-button>
      </div>
    </div>

    <!-- 记录时间线 -->
    <el-empty v-if="!loading && filteredLogs.length === 0" description="暂无开发记录，AI 工具会在这里沉淀每次开发过程" :image-size="100" />

    <div v-else class="md-card log-list">
      <div v-for="log in filteredLogs" :key="log.id" class="log-item">
        <div class="log-top">
          <span class="md-chip md-chip--sm" :class="TYPE_TAG[log.entry_type]">{{ TYPE_LABEL[log.entry_type] }}</span>
          <span class="log-title">{{ log.title }}</span>
          <span class="log-actions">
            <span
              v-if="log.severity"
              class="md-chip md-chip--sm"
              :class="log.severity === 'high' ? 'md-chip--error' : log.severity === 'medium' ? 'md-chip--warning' : 'md-chip--neutral'"
            >
              {{ SEVERITY_LABEL[log.severity] }}
            </span>
            <span
              v-if="derivedStatus(log) !== 'note'"
              class="md-chip md-chip--sm"
              :class="derivedStatus(log) === 'done' ? 'md-chip--success' : 'md-chip--primary'"
            >
              {{ derivedStatus(log) === 'done' ? '已完成' : '进行中' }}
            </span>
            <el-button
              v-if="log.entry_type === 'todo' || log.entry_type === 'blocker'"
              link
              size="small"
              :disabled="log.status === 'done'"
              @click="resolveLog(log)"
            >
              标记完成
            </el-button>
            <el-button link size="small" @click="openEdit(log)">编辑</el-button>
            <el-button link type="danger" size="small" @click="removeLog(log)">删除</el-button>
          </span>
        </div>
        <div class="log-meta">
          <span>{{ formatTime(log.created_at) }}</span>
          <span v-if="log.author">· {{ log.author }}</span>
          <span v-if="log.git_ref" class="git-ref">git: {{ log.git_ref }}</span>
          <span v-if="log.session_id">· 会话 #{{ log.session_id }}</span>
        </div>
        <p v-if="log.content" class="log-content">{{ log.content }}</p>
        <div v-if="log.related_task_ids?.length" class="log-tasks">
          关联任务：
          <button
            v-for="t in log.related_task_ids"
            :key="t"
            type="button"
            class="md-chip md-chip--sm md-chip--secondary log-task-tag"
            @click="goToTask(t)"
          >
            #{{ t }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="hasMore" class="load-more">
      <el-pagination
        v-model:current-page="pagination.page"
        :page-size="pagination.size"
        :total="pagination.total"
        layout="prev, pager, next"
        :disabled="loading"
        background
        @current-change="loadMore"
      />
    </div>

    <!-- 开发汇报弹窗 -->
    <el-dialog v-model="reportDialog" title="开发汇报" width="720px" destroy-on-close>
      <div class="report-range">
        <el-date-picker
          v-model="reportStart"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="开始日期"
          style="width: 160px"
        />
        <span class="range-sep">至</span>
        <el-date-picker
          v-model="reportEnd"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="结束日期"
          style="width: 160px"
        />
        <el-button plain :disabled="!reportStart && !reportEnd" @click="regenerateReport">
          应用范围
        </el-button>
      </div>
      <pre class="report-text">{{ reportText || '生成中…' }}</pre>
      <template #footer>
        <el-button @click="reportDialog = false">关闭</el-button>
        <el-button plain @click="downloadReport">下载 .md</el-button>
        <el-button type="primary" @click="copyReport">复制 Markdown</el-button>
      </template>
    </el-dialog>

    <!-- 创建/编辑 DevLog 弹窗 -->
    <el-dialog
      v-model="createDialog"
      :title="editingLog ? '编辑记录' : '新建记录'"
      width="560px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="类型" required>
          <el-select v-model="form.entry_type" style="width: 100%">
            <el-option v-for="t in TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="如：完成登录接口联调" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="详细说明（可选）" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item v-if="['todo', 'blocker'].includes(form.entry_type)" label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="s in STATUS_OPTIONS" :key="s" :label="s === 'done' ? '已完成' : '进行中'" :value="s" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="['difficulty', 'blocker'].includes(form.entry_type)" label="严重度">
            <el-select v-model="form.severity" clearable placeholder="无" style="width: 100%">
              <el-option v-for="s in SEVERITY_OPTIONS" :key="s" :label="SEVERITY_LABEL[s]" :value="s" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="关联任务">
          <el-select v-model="form.related_task_ids" multiple clearable filterable placeholder="选择关联任务（可选）" style="width: 100%">
            <el-option v-for="t in taskOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Git 引用">
          <el-input v-model="form.git_ref" placeholder="如：abc1234 / feature/login" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="logSaving" @click="saveLog">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { copyText } from '@/utils/clipboard'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { devLogApi, devSessionApi, projectApi, taskApi } from '@/api'
import type { DevLog, DevLogStats, DevLogType, DevSession, Project } from '@/types'
import { useProjectEvents } from '@/composables/useProjectEvents'
import LiveIndicator from '@/components/LiveIndicator.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const pid = computed(() => Number(props.id))

const loading = ref(false)
const project = ref<Project | null>(null)
const logs = ref<DevLog[]>([])
const stats = ref<DevLogStats | null>(null)
const sessions = ref<DevSession[]>([])
const filters = reactive<{ entry_type: string | null; status: string | null }>({
  entry_type: null,
  status: null,
})

const reportDialog = ref(false)
const reportText = ref('')

// P1-4: 创建/编辑 DevLog 弹窗
const createDialog = ref(false)
const editingLog = ref<DevLog | null>(null)
const logSaving = ref(false)
const form = reactive<{
  entry_type: DevLogType
  status: string
  severity: string | null
  title: string
  content: string | null
  related_task_ids: number[] | null
  git_ref: string | null
}>({
  entry_type: 'note',
  status: 'open',
  severity: null,
  title: '',
  content: null,
  related_task_ids: null,
  git_ref: null,
})

const TYPE_LABEL: Record<string, string> = {
  progress: '进展',
  difficulty: '难点',
  todo: '待办',
  decision: '决策',
  blocker: '阻塞',
  milestone: '里程碑',
  note: '备注',
}
const TYPE_OPTIONS = Object.entries(TYPE_LABEL).map(([value, label]) => ({ value, label }))
// 类型 → 色调芯片类：进展→success，难点→warning，待办→neutral，决策→primary，阻塞→error，备注→secondary
const TYPE_TAG: Record<string, string> = {
  progress: 'md-chip--success',
  difficulty: 'md-chip--warning',
  todo: 'md-chip--neutral',
  decision: 'md-chip--primary',
  blocker: 'md-chip--error',
  milestone: 'md-chip--tertiary',
  note: 'md-chip--secondary',
}
const SEVERITY_LABEL: Record<string, string> = { low: '低', medium: '中', high: '高' }
const STATUS_OPTIONS = ['open', 'done']
const SEVERITY_OPTIONS = ['low', 'medium', 'high']

// P1-4: 分页
const PAGE_SIZE = 20
const pagination = reactive({ page: 1, size: PAGE_SIZE, total: 0 })
const hasMore = computed(() => pagination.total > pagination.page * pagination.size)
const showingCount = computed(() => Math.min(pagination.page * pagination.size, pagination.total))

const activeSession = computed(() => sessions.value.find((s) => !s.ended_at) ?? null)

// P1-4: 任务选项（用于关联任务选择器与跳转）
const taskOptions = ref<{ id: number; name: string }[]>([])

async function loadTaskOptions() {
  try {
    taskOptions.value = (await taskApi.list(pid.value)).map((t) => ({ id: t.id, name: t.name }))
  } catch {
    /* ignore */
  }
}

function openCreate() {
  editingLog.value = null
  form.entry_type = 'note'
  form.status = 'open'
  form.severity = null
  form.title = ''
  form.content = null
  form.related_task_ids = null
  form.git_ref = null
  createDialog.value = true
}

function openEdit(log: DevLog) {
  editingLog.value = log
  form.entry_type = log.entry_type
  form.status = log.status
  form.severity = log.severity
  form.title = log.title
  form.content = log.content
  form.related_task_ids = log.related_task_ids?.length ? [...log.related_task_ids] : null
  form.git_ref = log.git_ref
  createDialog.value = true
}

async function saveLog() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  logSaving.value = true
  try {
    const payload = {
      entry_type: form.entry_type,
      status: form.status,
      severity: form.severity,
      title: form.title,
      content: form.content,
      related_task_ids: form.related_task_ids,
      git_ref: form.git_ref,
    }
    if (editingLog.value) {
      await devLogApi.update(editingLog.value.id, payload)
      ElMessage.success('已更新')
    } else {
      await devLogApi.create(pid.value, payload)
      ElMessage.success('已创建')
    }
    createDialog.value = false
    await load()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    logSaving.value = false
  }
}

// status 仅对 todo/blocker 有意义；progress/decision/milestone 本质是已完成的工作记录。
// 派生完成度：note 中性（仅「全部」显示），progress/decision/milestone 视为已完成。
function derivedStatus(log: DevLog): 'open' | 'done' | 'note' {
  if (log.entry_type === 'note') return 'note'
  if (['progress', 'decision', 'milestone'].includes(log.entry_type)) return 'done'
  return log.status === 'done' ? 'done' : 'open'
}

const filteredLogs = computed(() => {
  let list = logs.value
  if (filters.entry_type) list = list.filter((l) => l.entry_type === filters.entry_type)
  if (filters.status) list = list.filter((l) => derivedStatus(l) === filters.status)
  // 当前页 slice
  return list.slice(0, pagination.page * pagination.size)
})

// P1-4: 分页加载更多
async function loadMore() {
  if (loading.value) return
  loading.value = true
  try {
    const offset = pagination.page * pagination.size
    const params: Record<string, string | number> = {
      limit: pagination.size,
      offset,
    }
    if (filters.entry_type) params.entry_type = filters.entry_type
    const page = await devLogApi.listPage(pid.value, params)
    pagination.total = page.total // 服务端精确计数（此前 +1 估算，筛选后不准）
    // 追加（去重）
    const existingIds = new Set(logs.value.map((l) => l.id))
    const newItems = page.items.filter((l) => !existingIds.has(l.id))
    logs.value = [...logs.value, ...newItems]
    if (newItems.length) pagination.page += 1
  } finally {
    loading.value = false
  }
}

// related_task_ids 点击跳转
function goToTask(taskId: number) {
  router.push(`/projects/${pid.value}/tasks?task=${taskId}`)
}

function formatTime(iso: string) {
  return iso.replace('T', ' ').slice(0, 16)
}

async function loadLogs(reset = true) {
  const params: Record<string, string> = {}
  if (filters.entry_type) params.entry_type = filters.entry_type
  const page = await devLogApi.listPage(pid.value, params)
  logs.value = page.items
  if (reset) {
    pagination.page = 1
    pagination.total = page.total
  }
}

async function load() {
  loading.value = true
  try {
    const [p, s, ls, ss] = await Promise.all([
      projectApi.get(pid.value),
      devLogApi.stats(pid.value),
      devLogApi.listPage(pid.value),
      devSessionApi.list(pid.value),
    ])
    project.value = p
    stats.value = s
    logs.value = ls.items
    sessions.value = ss
    pagination.page = 1
    pagination.total = ls.total
  } finally {
    loading.value = false
  }
}

async function startSession() {
  let result
  try {
    result = await ElMessageBox.prompt('给本次会话起个名字（可选）', '开始开发会话', {
      confirmButtonText: '开始',
      cancelButtonText: '取消',
      inputPlaceholder: '如：实现登录模块',
    })
  } catch {
    return
  }
  const { value } = result
  await devSessionApi.start(pid.value, { title: value || null })
  ElMessage.success('会话已开始，AI 写入的记录会自动归入')
  sessions.value = await devSessionApi.list(pid.value)
}

async function endSession() {
  const s = activeSession.value
  if (!s) return
  let result
  try {
    result = await ElMessageBox.prompt('总结本次会话（可选，会写入记录）', '结束会话', {
      confirmButtonText: '结束',
      cancelButtonText: '取消',
      inputPlaceholder: '如：完成认证流程与单元测试',
    })
  } catch {
    return
  }
  const { value } = result
  await devSessionApi.end(s.id, { summary: value || null })
  ElMessage.success('会话已结束')
  sessions.value = await devSessionApi.list(pid.value)
  await loadLogs()
}

async function resolveLog(log: DevLog) {
  try {
    await ElMessageBox.confirm(`「${log.title}」标记为已完成？`, '标记完成', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await devLogApi.resolve(log.id)
    ElMessage.success('已标记完成')
    await Promise.all([loadLogs(), loadStats()])
  } catch {
    ElMessage.error('标记完成失败')
  }
}

async function removeLog(log: DevLog) {
  try {
    await ElMessageBox.confirm(`确定删除「${log.title}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await devLogApi.remove(log.id)
  ElMessage.success('已删除')
  await Promise.all([loadLogs(), loadStats()])
}

async function loadStats() {
  stats.value = await devLogApi.stats(pid.value)
}

async function openReport() {
  reportDialog.value = true
  reportText.value = ''
  reportStart.value = ''
  reportEnd.value = ''
  const r = await devLogApi.report(pid.value, null, null)
  reportText.value = r.text
}

const reportStart = ref('')
const reportEnd = ref('')
async function regenerateReport() {
  reportText.value = '生成中…'
  const r = await devLogApi.report(
    pid.value,
    reportStart.value || null,
    reportEnd.value || null,
  )
  reportText.value = r.text
}

function downloadReport() {
  if (!reportText.value) return
  const blob = new Blob(['\uFEFF' + reportText.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${project.value?.name ?? 'project'}_report_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已下载 Markdown')
}

async function copyReport() {
  await copyText(reportText.value)
  ElMessage.success('已复制 Markdown')
}

// 实时同步：AI 工具写入记录后自动刷新
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(load, 400)
}
const { connected, reconnectable, reconnect } = useProjectEvents(() => pid.value, scheduleReload)

onMounted(() => {
  load()
  loadTaskOptions()
})
// 路由参数变化时组件复用，需按 pid 重载（含任务下拉选项）
watch(pid, () => {
  load()
  loadTaskOptions()
})
</script>

<style scoped>
/* 指标卡 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--md-space-3);
  margin-bottom: var(--md-space-5);
}
@media (max-width: 800px) { .stats-row { grid-template-columns: repeat(3, 1fr); } }
.spec-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--md-space-2);
  padding: var(--md-space-4);
}
.spec-value {
  font-size: var(--md-type-headline-md);
  line-height: var(--md-type-headline-lh-md);
  font-weight: var(--md-weight-bold);
  color: var(--md-on-surface);
}

.toolbar {
  display: flex;
  gap: var(--md-space-2);
  align-items: center;
  margin-bottom: var(--md-space-5);
  flex-wrap: wrap;
}
.session-bar { margin-left: auto; }

/* 记录列表：一张卡片，条目之间用分隔线 */
.log-list {
  padding: 0;
  overflow: hidden;
}
.log-item {
  padding: var(--md-space-4) var(--md-space-5);
}
.log-item + .log-item { border-top: 1px solid var(--md-outline-variant); }
.log-top {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  flex-wrap: wrap;
}
.log-title {
  flex: 1;
  min-width: 200px;
  font-weight: var(--md-weight-medium);
  font-size: var(--md-type-body-md);
  color: var(--md-on-surface);
}
.log-actions { display: flex; align-items: center; gap: var(--md-space-1); }
.log-meta {
  display: flex;
  gap: var(--md-space-2);
  margin-top: var(--md-space-1);
  padding-left: var(--md-space-1);
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
  flex-wrap: wrap;
}
.git-ref { font-family: var(--md-font-mono); }
.log-content {
  margin: var(--md-space-2) 0 0 var(--md-space-1);
  font-size: var(--md-type-body-sm);
  line-height: var(--md-type-body-lh-md);
  color: var(--md-on-surface-variant);
  white-space: pre-wrap;
  max-width: var(--md-text-measure);
}
.log-tasks {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  margin-top: var(--md-space-2);
  padding-left: var(--md-space-1);
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}
.log-task-tag {
  cursor: pointer;
  transition: background-color var(--md-duration-short-4) var(--md-ease-standard);
}
.log-task-tag:hover { background-color: var(--md-primary-container); color: var(--md-on-primary-container); }
.load-more {
  display: flex;
  justify-content: center;
  padding: var(--md-space-5) 0;
}

.report-range {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  margin-bottom: var(--md-space-3);
}
.range-sep { color: var(--md-on-surface-variant); }
.report-text {
  max-height: 480px;
  max-width: var(--md-text-measure);
  overflow: auto;
  white-space: pre-wrap;
  background-color: var(--md-surface-container-high);
  border-radius: var(--md-shape-medium);
  padding: var(--md-space-4);
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface);
  line-height: 1.7;
}
</style>
