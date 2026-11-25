<template>
  <div class="page" v-loading="loading">
    <!-- 页面头部 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">进度</h1>
        <p class="page-sub">Dashboard · 全项目进度总览</p>
      </div>
      <div class="head-actions">
        <span v-if="overview" class="md-chip md-chip--primary">今日完成 {{ overview.today_completed }}</span>
      </div>
    </div>

    <!-- 项目进度卡片行 -->
    <section class="md-section">
      <div class="milestone-head">
        <div>
          <h2 class="section-title">项目进度</h2>
          <p class="section-sub">Projects</p>
        </div>
      </div>

      <div v-if="overview && overview.projects.length" class="project-cards-row">
        <div
          v-for="p in overview.projects"
          :key="p.project_id"
          class="mini-project-card"
          role="button"
          tabindex="0"
          @click="router.push(`/projects/${p.project_id}`)"
          @keydown.enter="router.push(`/projects/${p.project_id}`)"
        >
          <div class="mini-project-header">
            <span class="mini-project-name">{{ p.name }}</span>
            <span class="md-chip md-chip--sm" :class="p.status === 'active' ? 'md-chip--primary' : 'md-chip--neutral'">
              {{ p.status === 'active' ? '进行中' : '已归档' }}
            </span>
          </div>
          <div class="mini-progress-bar">
            <el-progress
              :percentage="Math.round(p.progress)"
              :stroke-width="8"
              :color="
                p.progress >= 50 ? 'var(--md-success)' : p.progress >= 20 ? 'var(--md-primary)' : 'var(--md-on-surface-variant)'
              "
            />
          </div>
          <div class="mini-progress-meta">
            <span>{{ p.total_tasks }} 任务 · {{ p.done_tasks }} 完成</span>
            <span v-if="p.overdue_count" class="meta-overdue">逾期 {{ p.overdue_count }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else description="还没有项目，前往项目页创建" :image-size="80" />
    </section>

    <div class="two-col">
      <!-- 跨项目逾期任务 -->
      <section class="md-section">
        <div class="milestone-head">
          <div>
            <h2 class="section-title">逾期任务</h2>
            <p class="section-sub">Overdue</p>
          </div>
          <span v-if="overview && overview.overdue_tasks.length === 0" class="md-chip md-chip--sm md-chip--success">无逾期</span>
        </div>
        <ul v-if="overview && overview.overdue_tasks.length" class="overdue-list">
          <li v-for="t in overview.overdue_tasks" :key="t.id" class="overdue-item">
            <span class="od-name">{{ t.name }}</span>
            <span class="md-chip md-chip--sm" :class="t.priority === 'high' ? 'md-chip--error' : 'md-chip--neutral'">
              {{ t.priority }}
            </span>
            <span class="od-late">逾期 {{ t.days_late }} 天</span>
          </li>
        </ul>
        <el-empty v-else description="暂无逾期任务" :image-size="80" />
      </section>

      <!-- 近期开发记录 -->
      <section class="md-section">
        <div class="milestone-head">
          <div>
            <h2 class="section-title">近期记录</h2>
            <p class="section-sub">Recent DevLog</p>
          </div>
        </div>
        <ul v-if="overview && overview.recent_logs.length" class="recent-log-list">
          <li v-for="l in overview.recent_logs" :key="l.id" class="recent-log-item">
            <span class="rl-title">{{ l.title }}</span>
            <span class="rl-meta">{{ fmtTime(l.created_at) }}</span>
          </li>
        </ul>
        <el-empty v-else description="暂无开发记录" :image-size="80" />
      </section>
    </div>

    <!-- 活跃开发会话 -->
    <section class="md-section" v-if="overview && overview.active_sessions.length">
      <div class="milestone-head">
        <div>
          <h2 class="section-title">活跃会话</h2>
          <p class="section-sub">Active DevSession</p>
        </div>
      </div>
      <el-timeline>
        <el-timeline-item
          v-for="s in overview.active_sessions"
          :key="s.id"
          timestamp="进行中"
          type="primary"
          placement="top"
        >
          <div class="session-row">
            <span class="session-name">{{ s.title || '未命名会话' }}</span>
            <span class="md-chip md-chip--sm md-chip--secondary">
              {{ s.project_name }} · {{ s.log_count }} 条记录
            </span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { statsApi } from '@/api'
import type { DashboardOverview } from '@/types'

const router = useRouter()
const overview = ref<DashboardOverview | null>(null)
const loading = ref(false)

function fmtTime(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    const res = await statsApi.overview()
    overview.value = res
  } catch (e) {
    ElMessage.error('加载仪表盘数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
/* 项目卡：填充式色块，无描边 */
.project-cards-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--md-space-4);
}
.mini-project-card {
  background-color: var(--md-surface-container-highest);
  border-radius: var(--md-shape-medium);
  padding: var(--md-card-padding);
  cursor: pointer;
  transition: background-color var(--md-duration-short-4) var(--md-ease-standard);
}
.mini-project-card:hover {
  background-color: var(--md-surface-container-high);
}
.mini-project-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-2);
  margin-bottom: var(--md-space-3);
}
.mini-project-name {
  font-size: var(--md-type-title-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}
.mini-progress-bar { margin-bottom: var(--md-space-1); }
.mini-progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}
.meta-overdue {
  color: var(--md-error);
  font-weight: var(--md-weight-medium);
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md-space-6);
}
@media (max-width: 1024px) { .two-col { grid-template-columns: 1fr; } }

/* 通用列表：行间分隔线 */
.overdue-list,
.recent-log-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.overdue-item {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  padding: var(--md-space-2) 0;
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface);
}
.overdue-item + .overdue-item,
.recent-log-item + .recent-log-item {
  border-top: 1px solid var(--md-outline-variant);
}
.od-name {
  flex: 1;
  font-weight: var(--md-weight-medium);
}
.od-late {
  color: var(--md-error);
  font-weight: var(--md-weight-medium);
}
.recent-log-item {
  display: flex;
  justify-content: space-between;
  gap: var(--md-space-2);
  padding: var(--md-space-2) 0;
  font-size: var(--md-type-body-sm);
}
.rl-title {
  color: var(--md-on-surface);
  flex: 1;
}
.rl-meta {
  color: var(--md-on-surface-variant);
  font-size: var(--md-type-label-md);
}
.session-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-2);
  flex-wrap: wrap;
}
.session-name {
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}
</style>
