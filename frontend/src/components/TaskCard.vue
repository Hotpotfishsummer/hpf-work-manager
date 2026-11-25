<template>
  <div class="task-card md-card" :class="{ 'is-active': running, 'is-done': done }">
    <div class="card-meta">
      <span
        class="project-tag clickable md-chip md-chip--sm md-chip--secondary md-state"
        title="点击仅筛选该项目的工单"
        @click="emit('filter-project', task.project_id)"
      >{{ projectName }}</span>

      <span class="md-chip md-chip--sm" :class="priorityClass(task.priority)">
        {{ priorityLabel(task.priority) }}
      </span>

      <span class="category-tag md-chip md-chip--sm" :class="categoryClass(category)" :title="category ? '分类：' + categoryLabel(category) : '未分类（点「··· → 编辑工单」可设置）'">
        {{ categoryIcon(category) }} {{ categoryLabel(category) }}
      </span>

      <span v-if="task.estimated_hours && !done" class="hours-tag" title="预估工时">⏱️ {{ task.estimated_hours }}h</span>

      <span
        v-if="directionCount > 0 && !done"
        class="direction-badge md-chip md-chip--sm md-chip--warning md-state"
        role="button"
        tabindex="0"
        title="该项目有负责人的未处理指示（复制 Prompt 时会自动带上）。点击查看 / 补充"
        @click="emit('open-directions', task.project_id)"
      >💬 {{ directionCount }}</span>

      <span v-if="running" class="running-indicator md-chip md-chip--sm md-chip--warning"><span class="pulse-ring"></span> 开发中</span>

      <template v-if="done">
        <span class="done-check md-chip md-chip--sm md-chip--success">✓ 已完成</span>
        <span v-if="task.completed_at" class="time-done">{{ formatTime(task.completed_at) }}</span>
      </template>
    </div>

    <h4 class="card-title" :class="{ strike: done }">{{ task.name }}</h4>

    <div v-if="task.description && !done" class="prompt-preview">
      <div class="prompt-header">
        <span>Agent Prompt 预览</span>
        <button type="button" class="mini-copy-btn md-btn md-btn--text md-btn--sm" @click.stop="emit('copy')">📋 复制</button>
      </div>
      <div class="prompt-text">{{ task.description }}</div>
    </div>

    <div class="card-footer" :class="{ 'done-footer': done }">
      <template v-if="done">
        <el-button size="small" text @click="emit('command', 'backlog')">↩ 重启任务</el-button>
        <el-button size="small" link type="danger" @click="emit('command', 'delete')">删除</el-button>
      </template>

      <template v-else>
        <button type="button" class="action-btn copy-btn md-btn md-btn--tonal md-btn--sm" @click="emit('copy')">📋 复制 Prompt</button>
        <div class="footer-right">
          <el-button
            v-if="running"
            size="small"
            type="success"
            plain
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

/** 优先级 → 色调芯片：高优 error、中优 warning、低优 neutral */
function priorityClass(p: string) {
  if (p === 'high') return 'md-chip--error'
  if (p === 'medium') return 'md-chip--warning'
  return 'md-chip--neutral'
}

/** 分类 → 固定的 accent 1–6 色调芯片（按 TASK_CATEGORIES 顺序），未分类 neutral */
function categoryClass(c: string | null) {
  if (!c) return 'md-chip--neutral'
  const idx = TASK_CATEGORIES.findIndex((x) => x.value === c)
  return idx >= 0 ? `md-chip--accent-${idx + 1}` : 'md-chip--neutral'
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
/* 任务卡片：填充式卡片（.md-card：surface-container-highest / 圆角 12 / 无边框） */
.task-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--md-space-2);
  transition: background-color var(--md-duration-short-2) var(--md-ease-standard);
}

.task-card:hover {
  background-color: var(--md-surface-container-high);
}

/* 状态强调条（规范允许的强调线）：执行中 = warning */
.task-card.is-active {
  border-left: var(--md-accent-bar-width) solid var(--md-warning);
}

.task-card.is-done {
  opacity: 0.78;
}

.card-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--md-space-1);
}

.project-tag.clickable {
  cursor: pointer;
}

.project-tag.clickable:hover {
  background-color: var(--md-primary-container);
  color: var(--md-on-primary-container);
  --state-color: var(--md-on-primary-container);
}

.hours-tag {
  margin-left: auto;
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}

.running-indicator {
  margin-left: auto;
}

.pulse-ring {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--md-on-warning-container);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.5; }
  100% { transform: scale(0.9); opacity: 1; }
}

.time-done {
  margin-left: auto;
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}

.card-title {
  font-size: var(--md-type-title-md);
  line-height: var(--md-type-title-lh-md);
  font-weight: var(--md-weight-medium);
  margin: 0;
  color: var(--md-on-surface);
  overflow-wrap: anywhere;
}

.card-title.strike {
  text-decoration: line-through;
  color: var(--md-on-surface-variant);
}

/* 卡内小块：surface-container-high，不再套边框 */
.prompt-preview {
  background: var(--md-surface-container-high);
  border-radius: var(--md-shape-small);
  padding: var(--md-space-2) var(--md-space-3);
}

.prompt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-2);
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
  margin-bottom: var(--md-space-1);
}

.mini-copy-btn {
  height: 24px;
  font-size: var(--md-type-label-md);
}

.prompt-text {
  font-size: var(--md-type-body-sm);
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
  gap: var(--md-space-2);
  padding-top: var(--md-space-2);
  border-top: 1px solid var(--md-outline-variant);
}

.card-footer.done-footer {
  justify-content: flex-end;
  gap: var(--md-space-2);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
}

.more-btn {
  color: var(--md-on-surface-variant);
}

.direction-badge {
  font-weight: var(--md-weight-medium);
}

.direction-badge:focus-visible {
  outline: 2px solid var(--md-primary);
  outline-offset: 2px;
}
</style>
