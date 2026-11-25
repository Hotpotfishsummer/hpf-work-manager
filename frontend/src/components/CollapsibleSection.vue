<template>
  <section class="fold-section md-section" :class="[`tone-${tone}`, { 'is-open': open }]">
    <button type="button" class="fold-header md-section__head" :aria-expanded="open" @click="toggle">
      <el-icon class="fold-chevron"><ArrowRight /></el-icon>
      <span class="fold-dot"></span>
      <span class="fold-title md-section__title">{{ title }}</span>
      <span v-if="count !== null" class="fold-count md-chip md-chip--sm" :class="'md-chip--' + toneChip">{{ count }}</span>
      <span v-if="hint && !open" class="fold-hint">{{ hint }}</span>
      <span class="fold-actions md-section__actions" @click.stop>
        <slot name="actions"></slot>
      </span>
    </button>
    <div v-show="open" class="fold-body">
      <slot></slot>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'

/**
 * 可折叠的纵向分区（受控）：开合状态由父组件持有（v-model:open），
 * 这样主页可以把它记到 localStorage，刷新后保持原样。
 * header 是一个 button（键盘可达），右侧动作区阻止冒泡，
 * 所以「添加」这类按钮不会顺带把面板折叠掉。
 */
const props = withDefaults(
  defineProps<{
    title: string
    count?: number | null
    hint?: string
    tone?: 'todo' | 'running' | 'done' | 'neutral'
    open: boolean
  }>(),
  { count: null, hint: '', tone: 'neutral' },
)

const emit = defineEmits<{ (e: 'update:open', open: boolean): void }>()

/** 分区色调 → 计数芯片色调（待办 primary、执行中 warning、完成 success、中性 neutral） */
const toneChip = computed(() => (props.tone === 'todo' ? 'primary' : props.tone === 'running' ? 'warning' : props.tone === 'done' ? 'success' : 'neutral'))

function toggle() {
  emit('update:open', !props.open)
}
</script>

<style scoped>
/* 分区：无外框、无底色，靠标题 + 间距分组（.md-section 负责间距） */
.fold-header {
  width: 100%;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
  border-radius: var(--md-shape-small);
}

.fold-chevron {
  color: var(--md-on-surface-variant);
  transition: transform var(--md-duration-short-2) var(--md-ease-standard);
}

.is-open .fold-chevron {
  transform: rotate(90deg);
}

.fold-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tone-todo .fold-dot { background: var(--md-primary); }
.tone-running .fold-dot { background: var(--md-warning); }
.tone-done .fold-dot { background: var(--md-success); }
.tone-neutral .fold-dot { background: var(--md-outline); }

.fold-title {
  white-space: nowrap;
}

.fold-hint {
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.fold-actions {
  gap: var(--md-space-1);
  flex-shrink: 0;
}

.fold-body {
  padding: 0;
}
</style>
