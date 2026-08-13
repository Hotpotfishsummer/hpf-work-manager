<template>
  <div class="page-container" v-loading="loading">
    <div class="page-head">
      <div>
        <h1 class="page-title">开发记录</h1>
        <p class="page-sub">{{ project?.name }} · DEV LOG · 进度/难点/待办/决策</p>
      </div>
      <div class="head-actions">
        <el-button size="large" @click="router.push(`/projects/${pid}`)">返回概览</el-button>
        <el-button size="large" type="primary" @click="openReport">生成开发汇报</el-button>
      </div>
    </div>

    <!-- 统计格 -->
    <div class="stats-row">
      <div class="spec-cell"><span class="spec-value">{{ stats?.total ?? 0 }}</span><span class="spec-label">总记录</span></div>
      <div class="spec-cell"><span class="spec-value">{{ stats?.today_count ?? 0 }}</span><span class="spec-label">今日</span></div>
      <div class="spec-cell"><span class="spec-value status-text-primary">{{ stats?.open_difficulties ?? 0 }}</span><span class="spec-label">难点</span></div>
      <div class="spec-cell"><span class="spec-value status-text-muted">{{ stats?.open_todos ?? 0 }}</span><span class="spec-label">待办</span></div>
      <div class="spec-cell"><span class="spec-value status-text-danger">{{ stats?.open_blockers ?? 0 }}</span><span class="spec-label">阻塞</span></div>
      <div class="spec-cell"><span class="spec-value">{{ stats?.decisions ?? 0 }}</span><span class="spec-label">决策</span></div>
    </div>

    <!-- 筛选 + 会话 -->
    <div class="toolbar">
      <el-select v-model="filters.entry_type" clearable placeholder="全部类型" style="width: 150px" @change="loadLogs">
        <el-option v-for="t in TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px" @change="loadLogs">
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
    <el-empty v-if="!loading && logs.length === 0" description="暂无开发记录，AI 工具会在这里沉淀每次开发过程" :image-size="100" />

    <div v-else class="log-list">
      <div v-for="log in logs" :key="log.id" class="log-item">
        <div class="log-top">
          <el-tag :type="TYPE_TAG[log.entry_type]" effect="light" size="small">{{ TYPE_LABEL[log.entry_type] }}</el-tag>
          <span class="log-title">{{ log.title }}</span>
          <span class="log-actions">
            <el-tag
              v-if="log.severity"
              :type="log.severity === 'high' ? 'danger' : log.severity === 'medium' ? 'warning' : 'info'"
              effect="plain"
              size="small"
            >
              {{ SEVERITY_LABEL[log.severity] }}
            </el-tag>
            <el-tag v-if="log.entry_type === 'todo' || log.entry_type === 'blocker'"
              :type="log.status === 'done' ? 'success' : 'primary'"
              effect="plain" size="small">
              {{ log.status === 'done' ? '已完成' : '待处理' }}
            </el-tag>
            <el-button
              v-if="log.entry_type === 'todo' || log.entry_type === 'blocker'"
              link
              size="small"
              :disabled="log.status === 'done'"
              @click="resolveLog(log)"
            >
              标记完成
            </el-button>
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
        <div v-if="log.related_task_ids.length" class="log-tasks">
          关联任务：<el-tag v-for="t in log.related_task_ids" :key="t" size="small" effect="plain">#{{ t }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 开发汇报弹窗 -->
    <el-dialog v-model="reportDialog" title="开发汇报" width="720px" destroy-on-close>
      <pre class="report-text">{{ reportText || '生成中…' }}</pre>
      <template #footer>
        <el-button @click="reportDialog = false">关闭</el-button>
        <el-button type="primary" @click="copyReport">复制 Markdown</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { devLogApi, devSessionApi, projectApi } from '@/api'
import type { DevLog, DevLogStats, DevSession, Project } from '@/types'
import { useProjectEvents } from '@/composables/useProjectEvents'

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

const TYPE_LABEL: Record<string, string> = {
  progress: '进展',
  difficulty: '难点',
  todo: '待办',
  decision: '决策',
  blocker: '阻塞',
  milestone: '里程碑',
  note: '备注',
}
const TYPE_TAG: Record<string, 'primary' | 'warning' | 'success' | 'info' | 'danger'> = {
  progress: 'primary',
  difficulty: 'warning',
  todo: 'info',
  decision: 'success',
  blocker: 'danger',
  milestone: 'primary',
  note: 'info',
}
const SEVERITY_LABEL: Record<string, string> = { low: '低', medium: '中', high: '高' }
const TYPE_OPTIONS = Object.entries(TYPE_LABEL).map(([value, label]) => ({ value, label }))

const activeSession = computed(() => sessions.value.find((s) => !s.ended_at) ?? null)

function formatTime(iso: string) {
  return iso.replace('T', ' ').slice(0, 16)
}

async function loadLogs() {
  const params: Record<string, string> = {}
  if (filters.entry_type) params.entry_type = filters.entry_type
  if (filters.status) params.status = filters.status
  logs.value = await devLogApi.list(pid.value, params)
}

async function load() {
  loading.value = true
  try {
    const [p, s, ls, ss] = await Promise.all([
      projectApi.get(pid.value),
      devLogApi.stats(pid.value),
      devLogApi.list(pid.value),
      devSessionApi.list(pid.value),
    ])
    project.value = p
    stats.value = s
    logs.value = ls
    sessions.value = ss
  } finally {
    loading.value = false
  }
}

async function startSession() {
  const { value } = await ElMessageBox.prompt('给本次会话起个名字（可选）', '开始开发会话', {
    confirmButtonText: '开始',
    cancelButtonText: '取消',
    inputPlaceholder: '如：实现登录模块',
  })
  await devSessionApi.start(pid.value, { title: value || null })
  ElMessage.success('会话已开始，AI 写入的记录会自动归入')
  sessions.value = await devSessionApi.list(pid.value)
}

async function endSession() {
  const s = activeSession.value
  if (!s) return
  const { value } = await ElMessageBox.prompt('总结本次会话（可选，会写入记录）', '结束会话', {
    confirmButtonText: '结束',
    cancelButtonText: '取消',
    inputPlaceholder: '如：完成认证流程与单元测试',
  })
  await devSessionApi.end(s.id, { summary: value || null })
  ElMessage.success('会话已结束')
  sessions.value = await devSessionApi.list(pid.value)
  await loadLogs()
}

async function resolveLog(log: DevLog) {
  await devLogApi.resolve(log.id)
  ElMessage.success('已标记完成')
  await Promise.all([loadLogs(), loadStats()])
}

async function removeLog(log: DevLog) {
  await ElMessageBox.confirm(`确定删除「${log.title}」？`, '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
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
  const r = await devLogApi.report(pid.value, null, null)
  reportText.value = r.text
}

async function copyReport() {
  await navigator.clipboard.writeText(reportText.value)
  ElMessage.success('已复制 Markdown')
}

// 实时同步：AI 工具写入记录后自动刷新
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(load, 400)
}
useProjectEvents(() => pid.value, scheduleReload)

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

.stats-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  border: 1px solid var(--md-outline-variant);
  margin-bottom: var(--md-space-5);
}
@media (max-width: 800px) { .stats-row { grid-template-columns: repeat(3, 1fr); } }
.spec-cell {
  padding: var(--md-space-4);
  text-align: center;
  border-right: 1px solid var(--md-outline-variant);
}
.spec-cell:nth-child(6n) { border-right: none; }
@media (max-width: 800px) { .spec-cell:nth-child(3n) { border-right: none; } }
.spec-value {
  display: block;
  font-size: var(--md-text-display-sm);
  font-weight: var(--md-weight-bold);
  color: var(--md-on-surface);
}
.spec-label {
  display: block;
  margin-top: var(--md-space-1);
  font-size: var(--md-text-label-md);
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--md-on-surface-variant);
}

.toolbar {
  display: flex;
  gap: var(--md-space-2);
  align-items: center;
  margin-bottom: var(--md-space-5);
  flex-wrap: wrap;
}
.session-bar { margin-left: auto; }

.log-list {
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg);
  overflow: hidden;
}
.log-item {
  padding: var(--md-space-4) var(--md-space-5);
  border-bottom: 1px solid var(--md-outline-variant);
}
.log-item:last-child { border-bottom: none; }
.log-top {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  flex-wrap: wrap;
}
.log-title {
  flex: 1;
  font-weight: var(--md-weight-bold);
  font-size: var(--md-text-body-md);
  color: var(--md-on-surface);
}
.log-actions { display: flex; align-items: center; gap: var(--md-space-1); }
.log-meta {
  display: flex;
  gap: var(--md-space-2);
  margin-top: var(--md-space-1);
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  flex-wrap: wrap;
}
.git-ref { font-family: var(--md-font-mono, monospace); }
.log-content {
  margin: var(--md-space-2) 0 0;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  white-space: pre-wrap;
}
.log-tasks {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  margin-top: var(--md-space-1);
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}

.report-text {
  max-height: 480px;
  overflow: auto;
  white-space: pre-wrap;
  background-color: var(--md-surface-container-high);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: var(--md-space-4);
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface);
  line-height: 1.7;
}
</style>
