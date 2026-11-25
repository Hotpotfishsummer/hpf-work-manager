<template>
  <div class="task-card" :class="{ 'is-active': running, 'is-done': done }">
    <div class="card-meta">
      <span
        class="project-tag clickable"
        title="点击仅筛选该项目的工单"
        @click="emit('filter-project', task.project_id)"
      >{{ projectName }}</span>

      <el-tag size="small" :type="priorityTag(task.priority)" effect="light">
        {{ priorityLabel(task.priority) }}
      </el-tag>

      <span class="category-tag" :title="category ? '分类：' + categoryLabel(category) : '未分类（点「··· → 编辑工单」可设置）'">
        {{ categoryIcon(category) }} {{ categoryLabel(category) }}
      </span>

      <span v-if="task.estimated_hours && !done" class="hours-tag">⏱️ {{ task.estimated_hours }}h</span>

      <span
        v-if="directionCount > 0 && !done"
        class="direction-badge"
        title="该项目有负责人的未处理指示（复制 Prompt 时会自动带上）。点击查看 / 补充"
        @click="emit('open-directions', task.project_id)"
      >💬 {{ directionCount }}</span>

      <span v-if="running" class="running-indicator"><span class="pulse-ring"></span> 开发中</span>

      <template v-if="done">
        <span class="done-check">✓ 已完成</span>
        <span v-if="task.completed_at" class="time-done">{{ formatTime(task.completed_at) }}</span>
      </template>
    </div>

    <h4 class="card-title" :class="{ strike: done }">{{ task.name }}</h4>

    <div v-if="task.description && !done" class="prompt-preview">
      <div class="prompt-header">
        <span>Agent Prompt 预览</span>
        <button class="mini-copy-btn" @click.stop="emit('copy')">📋 复制</button>
      </div>
      <div class="prompt-text">{{ task.description }}</div>
    </div>

    <div class="card-footer" :class="{ 'done-footer': done }">
      <template v-if="done">
        <el-button size="small" link @click="emit('command', 'backlog')">↩ 重启任务</el-button>
        <el-button size="small" link type="danger" @click="emit('command', 'delete')">删除</el-button>
      </template>

      <template v-else>
        <button class="action-btn copy-btn" @click="emit('copy')">📋 复制 Prompt</button>
        <div class="footer-right">
          <el-button
            v-if="running"
            size="small"
            type="success"
            @click="emit('command', 'done')"
          >✓ 完成</el-button>
          <el-button
            v-else
            size="small"
            type="primary"
            plain
            @click="emit('command', 'start')"
          >▶ 开始执行</el-button>
          <el-dropdown trigger="click" @command="(cmd: string) => emit('command', cmd)">
            <el-button size="small" circle text class="more-btn">···</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑工单</el-dropdown-item>
                <el-dropdown-item v-if="running" command="backlog">放回待办</el-dropdown-item>
                <el-dropdown-item v-if="!running" command="done">直接标记完成</el-dropdown-item>
                <el-dropdown-item
                  v-for="c in TASK_CATEGORIES"
                  :key="c.value"
                  :command="`category:${c.value}`"
                >{{ c.icon }} 设为「{{ c.label }}」</el-dropdown-item>
                <el-dropdown-item
                  v-if="task.category"
                  command="category:"
                  divided
                >📎 改回未分类</el-dropdown-item>
                <el-dropdown-item command="delete" divided style="color: var(--md-error)">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { TASK_CATEGORIES, categoryIcon, categoryLabel } from '@/utils/taskCategory'

export interface CardTask {
  id: number
  project_id: number
  name: string
  description?: string | null
  priority: 'low' | 'medium' | 'high'
  status: 'todo' | 'in_progress' | 'done'
  progress: number
  estimated_hours?: number | null
  category?: string | null
  completed_at?: string | null
  created_at: string
}

const props = withDefaults(
  defineProps<{
    task: CardTask
    projectName: string
    /** 该任务所属项目的「未处理指示」数 */
    directionCount?: number
  }>(),
  { directionCount: 0 },
)

const emit = defineEmits<{
  (e: 'copy'): void
  (e: 'command', cmd: string): void
  (e: 'filter-project', projectId: number): void
  (e: 'open-directions', projectId: number): void
}>()

const running = computed(() => props.task.status === 'in_progress')
const done = computed(() => props.task.status === 'done')
const category = computed(() => props.task.category ?? null)

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
</script>

<style scoped>
/* 卡片样式从主页原样迁入 */
/* 任务卡片 */
.task-card {
  background: var(--md-surface-container-lowest);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: 14px;
  box-shadow: var(--md-shadow-1);
  transition: all 0.2s ease;
}

.task-card:hover {
  box-shadow: var(--md-shadow-2);
  border-color: var(--md-outline);
}

.task-card.is-active {
  border-left: 3px solid var(--md-warning);
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
  background: var(--md-primary-container);
  color: var(--md-primary);
}
.project-tag {
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant);
  background: var(--md-surface-container);
  padding: 2px 6px;
  border-radius: var(--md-radius-xs);
}

.hours-tag {
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant-2);
  margin-left: auto;
}

.running-indicator {
  margin-left: auto;
  font-size: var(--md-text-caption);
  color: var(--md-warning);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.pulse-ring {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--md-warning);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.5; }
  100% { transform: scale(0.9); opacity: 1; }
}

.done-check {
  font-size: var(--md-text-caption);
  color: var(--md-success);
  font-weight: 600;
}

.time-done {
  margin-left: auto;
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant-2);
}

.card-title {
  font-size: var(--md-text-body);
  font-weight: 600;
  margin: 0 0 10px 0;
  line-height: 1.4;
  color: var(--md-on-surface);
}

.card-title.strike {
  text-decoration: line-through;
  color: var(--md-on-surface-variant-2);
}

.prompt-preview {
  background: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  padding: 8px 10px;
  margin-bottom: 12px;
}

.prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant-2);
  margin-bottom: 4px;
}

.mini-copy-btn {
  background: none;
  border: none;
  color: var(--md-primary);
  cursor: pointer;
  font-size: var(--md-text-caption);
  padding: 0;
}
.mini-copy-btn:hover { text-decoration: underline; }

.prompt-text {
  font-size: var(--md-text-body-sm);
  line-height: 1.4;
  color: var(--md-on-surface);
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
  border-top: 1px dashed var(--md-outline-variant);
}

.card-footer.done-footer {
  justify-content: flex-end;
  gap: 12px;
}

.action-btn.copy-btn {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  padding: 4px 10px;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface);
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn.copy-btn:hover {
  background: var(--md-primary-tint);
  border-color: var(--md-primary);
  color: var(--md-primary);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.more-btn {
  color: var(--md-on-surface-variant-2);
}

/* ---------- 本轮新增 ---------- */
.category-tag {
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  white-space: nowrap;
}

.direction-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 7px;
  height: 20px;
  border-radius: var(--md-radius-pill);
  background: var(--md-warning-container);
  border: 1px solid color-mix(in srgb, var(--md-warning) 40%, transparent);
  color: var(--md-on-warning-container);
  font-size: var(--md-text-body-sm);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.direction-badge:hover {
  background: var(--md-warning-container-strong);
}

.task-card.is-done .card-meta {
  /* 已完成卡片没有分类/指示徽标，保持紧凑 */
  gap: 8px;
}
</style>
