<template>
  <div v-loading="loading">
    <!-- hero-band-dark：深海军蓝横幅，唯一深色块 -->
    <div class="hero-band">
      <div class="page-container hero-inner">
        <div class="hero-info">
          <p class="hero-eyebrow">PROJECT · {{ project?.status === 'archived' ? '已归档' : '进行中' }}</p>
          <h1 class="hero-title">{{ project?.name }}</h1>
          <p class="hero-desc">{{ project?.description || '暂无描述' }}</p>
          <div class="hero-actions">
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
          <p class="section-sub">BURNDOWN</p>
          <BurndownChart v-if="burndown.length" :data="burndown" />
          <el-empty v-else description="暂无任务数据" :image-size="80" />
        </section>

        <!-- 延期预警 -->
        <section class="bmw-card section-card">
          <h2 class="section-title">延期预警</h2>
          <p class="section-sub">OVERDUE</p>
          <div v-if="overdueTasks.length === 0" class="ok-block">
            <span class="ok-dot" />没有延期任务，一切正常
          </div>
          <ul v-else class="overdue-list">
            <li v-for="t in overdueTasks" :key="t.id" class="overdue-item">
              <span class="od-name">{{ t.name }}</span>
              <el-tag
                :type="t.priority === 'high' ? 'danger' : 'warning'"
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
            <p class="section-sub">MILESTONES</p>
          </div>
          <el-button size="large" @click="milestoneDialog = true">新建里程碑</el-button>
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
              <el-button link type="danger" size="small" @click="removeMilestone(m.id)">删除</el-button>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无里程碑" :image-size="80" />
      </section>
    </div>

    <!-- 新建里程碑弹窗 -->
    <el-dialog v-model="milestoneDialog" title="新建里程碑" width="420px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="milestoneForm.name" placeholder="如：完成数据模型" />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="milestoneForm.due_date" type="date" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="milestoneDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingMilestone" @click="saveMilestone">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { milestoneApi, projectApi, statsApi } from '@/api'
import type { Milestone, Project, ProjectStats, BurndownPoint } from '@/types'
import BurndownChart from '@/components/BurndownChart.vue'
import { useProjectEvents } from '@/composables/useProjectEvents'

const props = defineProps<{ id: string }>()
const router = useRouter()
const pid = computed(() => Number(props.id))

const loading = ref(false)
const project = ref<Project | null>(null)
const stats = ref<ProjectStats | null>(null)
const burndown = ref<BurndownPoint[]>([])
const milestones = ref<Milestone[]>([])
const activeTab = ref('overview')

const milestoneDialog = ref(false)
const savingMilestone = ref(false)
const milestoneForm = reactive<{ name: string; due_date: string | null }>({ name: '', due_date: null })

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
useProjectEvents(() => pid.value, scheduleReload)

async function load() {
  loading.value = true
  try {
    const [p, s, b, ms] = await Promise.all([
      projectApi.get(pid.value),
      statsApi.project(pid.value),
      statsApi.burndown(pid.value),
      milestoneApi.list(pid.value),
    ])
    project.value = p
    stats.value = s
    burndown.value = b
    milestones.value = ms
  } finally {
    loading.value = false
  }
}

async function saveMilestone() {
  if (!milestoneForm.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  savingMilestone.value = true
  try {
    await milestoneApi.create(pid.value, {
      name: milestoneForm.name,
      due_date: milestoneForm.due_date ?? null,
    })
    ElMessage.success('已创建')
    milestoneDialog.value = false
    milestoneForm.name = ''
    milestoneForm.due_date = null
    milestones.value = await milestoneApi.list(pid.value)
  } finally {
    savingMilestone.value = false
  }
}

async function removeMilestone(id: number) {
  await ElMessageBox.confirm('删除里程碑后其下任务将保留（解除关联），确定删除？', '删除确认', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await milestoneApi.remove(id)
  ElMessage.success('已删除')
  milestones.value = await milestoneApi.list(pid.value)
}

onMounted(load)
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
  letter-spacing: 1.5px;
  color: var(--md-on-surface-variant);
}
.hero-title {
  margin: 0;
  font-size: var(--md-text-display-lg);
  color: var(--md-on-surface);
}
.hero-desc {
  margin: var(--md-space-2) 0 var(--md-space-5);
  font-size: var(--md-text-body-md);
  font-weight: var(--md-weight-regular);
  color: var(--md-on-surface-variant);
  max-width: 640px;
}
.hero-actions { display: flex; gap: var(--md-space-4); flex-wrap: wrap; }
.hero-actions :deep(.el-button--primary) {
  background-color: var(--md-primary);
  border-color: var(--md-primary);
}
.hero-actions :deep(.el-button--primary:hover) { background-color: color-mix(in srgb, var(--md-primary) 92%, var(--md-on-primary)); }
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
  font-size: 26px;
  font-weight: var(--md-weight-bold);
  color: var(--md-on-surface);
  line-height: 1.1;
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

/* subnav：分类标签风格 */
.subnav-wrap {
  border-bottom: 1px solid var(--md-outline-variant);
  background-color: var(--md-surface);
}
.bmw-tabs :deep(.el-tabs__item) {
  font-size: var(--md-text-label-lg);
  font-weight: var(--md-weight-bold);
  letter-spacing: 0.5px;
  text-transform: uppercase;
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

.two-col {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--md-space-5);
  margin-bottom: var(--md-space-5);
}
@media (max-width: 1024px) { .two-col { grid-template-columns: 1fr; } }

.section-card { margin-bottom: 0; }
.section-title {
  margin: 0;
  font-size: var(--md-text-title-lg);
}
.section-sub {
  margin: var(--md-space-1) 0 var(--md-space-4);
  font-size: var(--md-text-label-md);
  letter-spacing: 1.5px;
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
.od-name { flex: 1; font-weight: var(--md-weight-bold); font-size: var(--md-text-body-sm); color: var(--md-on-surface); }
.od-late { font-size: var(--md-text-label-md); color: var(--md-status-overdue); font-weight: 700; }

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
  font-weight: var(--md-weight-bold);
  font-size: var(--md-text-body-md);
  color: var(--md-on-surface);
}
</style>
