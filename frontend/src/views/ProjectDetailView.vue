<template>
  <div v-loading="loading">
    <!-- hero-band-dark：深海军蓝横幅，唯一深色块 -->
    <div class="hero-band">
      <div class="page-container hero-inner">
        <div class="hero-info">
          <p class="hero-eyebrow">Project · {{ project?.status === 'archived' ? '已归档' : '进行中' }}</p>
          <h1 class="hero-title">{{ project?.name }}</h1>
          <p class="hero-desc">{{ project?.description || '暂无描述' }}</p>
          <div class="hero-actions">
            <el-button size="large" @click="openEditProject">编辑项目</el-button>
            <el-button size="large" @click="toggleProjectStatus">
              {{ project?.status === 'archived' ? '取消归档' : '归档项目' }}
            </el-button>
            <el-button type="primary" size="large" @click="router.push(`/projects/${pid}/tasks`)">
              管理任务
            </el-button>
            <el-button class="hero-ghost-btn" size="large" @click="router.push(`/projects/${pid}/gantt`)">
              查看甘特图
            </el-button>
            <el-button class="hero-ghost-btn" size="large" @click="router.push(`/projects/${pid}/logs`)">
              开发记录
            </el-button>
          </div>
        </div>

        <!-- hero 上的进度环：surface-dark-elevated 嵌套卡片 -->
        <div class="hero-progress">
          <el-progress
            type="circle"
            :percentage="Math.round(stats?.progress ?? 0)"
            :width="120"
            :stroke-width="6"
            color="var(--md-primary)"
          >
            <template #default>
              <span class="progress-num">{{ Math.round(stats?.progress ?? 0) }}%</span>
              <span class="progress-label">项目进度</span>
            </template>
          </el-progress>
          <p v-if="hasHours" class="hero-weighted">
            工时加权 {{ Math.round(stats?.weighted_progress ?? 0) }}%
            <el-tooltip content="按预估工时加权：大任务占比更高，未填工时的任务按 1 小时计" placement="top">
              <el-icon class="weighted-help"><InfoFilled /></el-icon>
            </el-tooltip>
          </p>
          <p class="hero-range">{{ fmtRange() }}</p>
        </div>
      </div>
    </div>

    <!-- category-tab 子导航：UPPERCASE + ink 下划线 -->
    <div class="subnav-wrap">
      <div class="page-container subnav">
        <el-tabs v-model="activeTab" class="bmw-tabs" @tab-click="onTabClick">
          <el-tab-pane label="概览" name="overview" />
          <el-tab-pane label="任务" name="tasks" />
          <el-tab-pane label="甘特图" name="gantt" />
          <el-tab-pane label="开发记录" name="logs" />
        </el-tabs>
        <LiveIndicator :connected="connected" :is-reconnectable="reconnectable" @reconnect="reconnect" />
      </div>
    </div>

    <div class="page-container content" v-show="activeTab === 'overview'">
      <!-- spec-cells：统计格 -->
      <div class="stats-row">
        <div class="spec-cell"><span class="spec-value">{{ stats?.total_tasks ?? 0 }}</span><span class="spec-label">总任务</span></div>
        <div class="spec-cell"><span class="spec-value status-text-success">{{ stats?.done_tasks ?? 0 }}</span><span class="spec-label">已完成</span></div>
        <div class="spec-cell"><span class="spec-value status-text-primary">{{ stats?.in_progress_tasks ?? 0 }}</span><span class="spec-label">进行中</span></div>
        <div class="spec-cell"><span class="spec-value status-text-muted">{{ stats?.todo_tasks ?? 0 }}</span><span class="spec-label">待办</span></div>
      </div>

      <div class="two-col">
        <!-- 燃尽图 -->
        <section class="bmw-card section-card">
          <h2 class="section-title">燃尽图</h2>
          <p class="section-sub">Burndown</p>
          <BurndownChart v-if="burndown.length" :data="burndown" />
          <el-empty v-else description="暂无任务数据" :image-size="80" />
        </section>

        <!-- 进度趋势（P4-3 每日快照） -->
        <section class="bmw-card section-card">
          <h2 class="section-title">进度趋势</h2>
          <p class="section-sub">Trend · 每日快照</p>
          <ProgressTrendChart v-if="progressHistory.length" :data="progressHistory" />
          <el-empty v-else description="快照随每次查看统计自动沉淀，明天回来就能看到曲线" :image-size="80" />
        </section>

        <!-- 延期预警 -->
        <section class="bmw-card section-card">
          <h2 class="section-title">延期预警</h2>
          <p class="section-sub">Overdue</p>
          <div v-if="overdueTasks.length === 0" class="ok-block">
            <span class="ok-dot" />没有延期任务，一切正常
          </div>
          <ul v-else class="overdue-list">
            <li v-for="t in overdueTasks" :key="t.id" class="overdue-item">
              <span class="od-name">{{ t.name }}</span>
              <el-tag
                :type="t.priority === 'high' ? 'warning' : 'info'"
                effect="plain"
                size="small"
              >
                {{ PRIORITY_LABEL[t.priority] }}
              </el-tag>
              <span class="od-late">逾期 {{ t.days_late }} 天</span>
            </li>
          </ul>
        </section>
      </div>

      <!-- 里程碑 -->
      <section class="bmw-card section-card">
        <div class="milestone-head">
          <div>
            <h2 class="section-title">里程碑</h2>
            <p class="section-sub">Milestones</p>
          </div>
          <el-button size="large" @click="openCreateMilestone">新建里程碑</el-button>
        </div>

        <el-timeline v-if="milestones.length">
          <el-timeline-item
            v-for="m in milestones"
            :key="m.id"
            :timestamp="m.due_date ? m.due_date.slice(0, 10) : '未设日期'"
            :type="m.status === 'done' ? 'success' : 'primary'"
            placement="top"
          >
            <div class="milestone-row">
              <span class="milestone-name">{{ m.name }}</span>
              <el-tag :type="m.status === 'done' ? 'success' : 'primary'" effect="plain" size="small">
                {{ m.status === 'done' ? '已完成' : '进行中' }}
              </el-tag>
              <el-button link size="small" @click="openEditMilestone(m)">编辑</el-button>
              <el-button link size="small" @click="toggleMilestone(m)">
                {{ m.status === 'done' ? '取消完成' : '标记完成' }}
              </el-button>
              <el-button link type="danger" size="small" @click="removeMilestone(m.id)">删除</el-button>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无里程碑" :image-size="80" />
      </section>
    </div>

    <!-- 新建/编辑里程碑弹窗 -->
    <el-dialog v-model="milestoneDialog" :title="editingMilestone ? '编辑里程碑' : '新建里程碑'" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="milestoneForm.name" placeholder="如：完成数据模型" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="milestoneForm.due_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="milestoneDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingMilestone" @click="saveMilestone">保存</el-button>
      </template>
    </el-dialog>

    <!-- 编辑项目弹窗 -->
    <el-dialog v-model="projectDialog" title="编辑项目" width="480px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="项目名称">
          <el-input v-model="projectForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="projectForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="起止日期">
          <el-date-picker
            v-model="projectForm.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="截止日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingProject" @click="saveProject">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { milestoneApi, projectApi, statsApi } from '@/api'
import type { Milestone, Project, ProjectStats, BurndownPoint, ProgressSnapshotPoint } from '@/types'
import BurndownChart from '@/components/BurndownChart.vue'
import ProgressTrendChart from '@/components/ProgressTrendChart.vue'
import LiveIndicator from '@/components/LiveIndicator.vue'
import { useProjectEvents } from '@/composables/useProjectEvents'

const props = defineProps<{ id: string }>()
const router = useRouter()
const pid = computed(() => Number(props.id))

const loading = ref(false)
const project = ref<Project | null>(null)
const stats = ref<ProjectStats | null>(null)
const burndown = ref<BurndownPoint[]>([])
const progressHistory = ref<ProgressSnapshotPoint[]>([])
const milestones = ref<Milestone[]>([])
const activeTab = ref('overview')

// 有任务填了预估工时才显示工时加权进度
const hasHours = computed(() => stats.value?.estimated_hours_total != null)

const milestoneDialog = ref(false)
const savingMilestone = ref(false)
const editingMilestone = ref<Milestone | null>(null)
const milestoneForm = reactive<{ name: string; due_date: string | null }>({ name: '', due_date: null })

const projectDialog = ref(false)
const savingProject = ref(false)
const projectForm = reactive<{
  name: string
  description: string
  dateRange: [string, string] | null
}>({ name: '', description: '', dateRange: null })

const PRIORITY_LABEL: Record<string, string> = { high: '高', medium: '中', low: '低' }

const overdueTasks = computed(() => stats.value?.overdue_tasks ?? [])

// 子 tab 跳转到独立路由页面（el-tab-pane 的 @click 不会触发，需用 el-tabs 的 @tab-click）
function onTabClick(pane: { paneName: string }) {
  if (pane.paneName === 'overview') return
  router.push(`/projects/${pid.value}/${pane.paneName}`)
}

function fmtRange() {
  if (!project.value) return ''
  const s = project.value.start_date?.slice(0, 10) ?? '—'
  const e = project.value.end_date?.slice(0, 10) ?? '—'
  return `${s} 至 ${e}`
}

// 实时同步：AI 工具更新数据后自动刷新
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReload() {
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(load, 400)
}
const { connected, reconnectable, reconnect } = useProjectEvents(() => pid.value, scheduleReload)

async function load() {
  loading.value = true
  try {
    const [p, s, b, ms, ph] = await Promise.all([
      projectApi.get(pid.value),
      statsApi.project(pid.value),
      statsApi.burndown(pid.value),
      milestoneApi.list(pid.value),
      statsApi.progressHistory(pid.value).catch(() => []),
    ])
    project.value = p
    stats.value = s
    burndown.value = b
    milestones.value = ms
    progressHistory.value = ph
  } finally {
    loading.value = false
  }
}

function openCreateMilestone() {
  editingMilestone.value = null
  milestoneForm.name = ''
  milestoneForm.due_date = null
  milestoneDialog.value = true
}

function openEditMilestone(m: Milestone) {
  editingMilestone.value = m
  milestoneForm.name = m.name
  milestoneForm.due_date = m.due_date ? m.due_date.slice(0, 10) : null
  milestoneDialog.value = true
}

async function toggleMilestone(m: Milestone) {
  const next = m.status === 'done' ? 'active' : 'done'
  await milestoneApi.update(m.id, { status: next })
  ElMessage.success(next === 'done' ? '已标记完成' : '已取消完成')
  milestones.value = await milestoneApi.list(pid.value)
}

async function saveMilestone() {
  if (!milestoneForm.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  if (!milestoneForm.due_date) {
    ElMessage.warning('请选择截止日期')
    return
  }
  savingMilestone.value = true
  try {
    const payload = {
      name: milestoneForm.name,
      due_date: milestoneForm.due_date ?? null,
    }
    if (editingMilestone.value) {
      await milestoneApi.update(editingMilestone.value.id, payload)
      ElMessage.success('已更新')
    } else {
      await milestoneApi.create(pid.value, payload)
      ElMessage.success('已创建')
    }
    milestoneDialog.value = false
    milestoneForm.name = ''
    milestoneForm.due_date = null
    editingMilestone.value = null
    milestones.value = await milestoneApi.list(pid.value)
  } finally {
    savingMilestone.value = false
  }
}

async function removeMilestone(id: number) {
  try {
    await ElMessageBox.confirm('删除里程碑后其下任务将保留（解除关联），确定删除？', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await milestoneApi.remove(id)
  ElMessage.success('已删除')
  milestones.value = await milestoneApi.list(pid.value)
}

function openEditProject() {
  if (!project.value) return
  projectForm.name = project.value.name
  projectForm.description = project.value.description ?? ''
  projectForm.dateRange = [
    project.value.start_date ? project.value.start_date.slice(0, 10) : '',
    project.value.end_date ? project.value.end_date.slice(0, 10) : '',
  ]
  projectDialog.value = true
}

async function toggleProjectStatus() {
  if (!project.value) return
  const next = project.value.status === 'archived' ? 'active' : 'archived'
  if (next === 'archived') {
    try {
      await ElMessageBox.confirm('归档后项目仍在「已归档」中可查看，确定归档？', '归档项目', {
        type: 'warning',
        confirmButtonText: '归档',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
  }
  await projectApi.update(project.value.id, { status: next })
  ElMessage.success(next === 'archived' ? '已归档' : '已取消归档')
  await load()
}

async function saveProject() {
  if (!projectForm.name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  savingProject.value = true
  try {
    await projectApi.update(pid.value, {
      name: projectForm.name,
      description: projectForm.description || null,
      start_date: projectForm.dateRange?.[0] ? projectForm.dateRange[0] : null,
      end_date: projectForm.dateRange?.[1] ? projectForm.dateRange[1] : null,
    })
    ElMessage.success('已更新')
    projectDialog.value = false
    await load()
  } finally {
    savingProject.value = false
  }
}

onMounted(load)
// 路由参数变化时组件复用，onMounted 不会再次触发
watch(pid, load)
</script>

<style scoped>
/* hero-band：跟随主题的表面带，Apple 留白风格 */
.hero-band {
  background-color: var(--md-surface);
  color: var(--md-on-surface);
  border-bottom: 1px solid var(--md-outline-variant);
}
.hero-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-6);
  padding-top: var(--md-space-6);
  padding-bottom: var(--md-space-6);
  flex-wrap: wrap;
}
.hero-eyebrow {
  margin: 0 0 var(--md-space-1);
  font-size: var(--md-text-label-md);
  font-weight: var(--md-weight-medium);
  letter-spacing: var(--md-track-caption);
  color: var(--md-on-surface-variant);
}
.hero-title {
  margin: 0;
  font-size: var(--md-text-display);
  color: var(--md-on-surface);
}
.hero-desc {
  margin: var(--md-space-2) 0 var(--md-space-5);
  font-size: var(--md-text-body-md);
  font-weight: var(--md-weight-regular);
  color: var(--md-on-surface-variant);
  max-width: var(--md-text-measure);
}
.hero-actions { display: flex; gap: var(--md-space-4); flex-wrap: wrap; }
.hero-actions :deep(.el-button--primary) {
  background-color: var(--md-primary);
  border-color: var(--md-primary);
}
.hero-ghost-btn {
  background: transparent;
  border: 1px solid var(--md-outline);
  color: var(--md-on-surface);
}
.hero-ghost-btn:hover { border-color: var(--md-primary); color: var(--md-primary); background: var(--md-primary-hover); }

/* hero 进度环（嵌套卡片，跟随主题） */
.hero-progress {
  background-color: var(--md-surface-container-high);
  padding: var(--md-space-5);
  text-align: center;
  border-radius: var(--md-radius-lg);
}
.hero-progress :deep(.el-progress__text) {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.progress-num {
  font-size: var(--md-text-display-sm);
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-surface);
  line-height: 1.2;
}
.progress-label {
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}
.hero-range {
  margin: var(--md-space-2) 0 0;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}
.hero-weighted {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  margin: var(--md-space-1) 0 0;
  font-size: var(--md-text-label-md);
  font-weight: var(--md-weight-semibold);
  color: var(--md-primary);
}
.weighted-help {
  font-size: 13px;
  color: var(--md-on-surface-variant);
  cursor: help;
}

/* subnav：分类标签风格 */
.subnav-wrap {
  border-bottom: 1px solid var(--md-outline-variant);
  background-color: var(--md-surface);
}
.bmw-tabs :deep(.el-tabs__item) {
  font-size: var(--md-text-label-lg);
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-surface-variant);
  padding: 0 var(--md-space-4);
}
.bmw-tabs :deep(.el-tabs__item.is-active) { color: var(--md-on-surface); }
.bmw-tabs :deep(.el-tabs__active-bar) { height: 2px; background-color: var(--md-primary); }

.content {
  padding-top: var(--md-space-6);
}

/* spec-cell */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--md-outline-variant);
  margin-bottom: var(--md-space-5);
}
@media (max-width: 640px) { .stats-row { grid-template-columns: repeat(2, 1fr); } }
.spec-cell {
  padding: var(--md-space-4);
  text-align: center;
  border-right: 1px solid var(--md-outline-variant);
}
.spec-cell:last-child { border-right: none; }
.spec-value {
  display: block;
  font-size: var(--md-text-display-sm);
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-surface);
}
.spec-label {
  display: block;
  margin-top: var(--md-space-1);
  font-size: var(--md-text-label-md);
  letter-spacing: var(--md-track-caption);
  color: var(--md-on-surface-variant);
}

.two-col {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--md-space-5);
  margin-bottom: var(--md-space-5);
}
@media (max-width: 1024px) { .two-col { grid-template-columns: 1fr; } }

/* bmw-card：MD3 卡片（surface-container-low + lg 圆角 + hairline） */
.bmw-card {
  background-color: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg);
  padding: var(--md-card-padding-lg);
  color: var(--md-on-surface);
}
.section-card { margin-bottom: 0; }
.section-title {
  margin: 0;
  font-size: var(--md-text-title-lg);
}
.section-sub {
  margin: var(--md-space-1) 0 var(--md-space-4);
  font-size: var(--md-text-label-md);
  letter-spacing: var(--md-track-caption);
  color: var(--md-on-surface-variant);
}

.ok-block {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  color: var(--md-on-surface-variant);
  font-size: var(--md-text-body-sm);
  padding: var(--md-space-4) 0;
}
.ok-dot {
  width: 10px; height: 10px;
  border-radius: var(--md-radius-full);
  background-color: var(--md-status-done);
}

.overdue-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.overdue-item {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  padding: var(--md-space-2) 0;
  border-bottom: 1px solid var(--md-outline-variant);
}
.overdue-item:last-child { border-bottom: none; }
.od-name { flex: 1; font-weight: var(--md-weight-semibold); font-size: var(--md-text-body-sm); color: var(--md-on-surface); }
.od-late { font-size: var(--md-text-label-md); color: var(--md-status-overdue); font-weight: var(--md-weight-semibold); }

.milestone-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md-space-5);
}
.milestone-row {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
}
.milestone-name {
  font-weight: var(--md-weight-semibold);
  font-size: var(--md-text-body-md);
  color: var(--md-on-surface);
}

/* P4-2 移动端：hero 纵排，进度环居中 */
@media (max-width: 768px) {
  .hero-inner {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--md-space-4);
  }
  .hero-progress { align-self: center; text-align: center; }
}
</style>
