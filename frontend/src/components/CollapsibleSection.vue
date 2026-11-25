<template>
  <section class="fold-section" :class="[`tone-${tone}`, { 'is-open': open }]">
    <button type="button" class="fold-header" :aria-expanded="open" @click="toggle">
      <el-icon class="fold-chevron"><ArrowRight /></el-icon>
      <span class="fold-dot"></span>
      <span class="fold-title">{{ title }}</span>
      <span v-if="count !== null" class="fold-count">{{ count }}</span>
      <span v-if="hint && !open" class="fold-hint">{{ hint }}</span>
      <span class="fold-actions" @click.stop>
        <slot name="actions"></slot>
      </span>
    </button>
    <div v-show="open" class="fold-body">
      <slot></slot>
    </div>
  </section>
</template>

<script setup lang="ts">
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

function toggle() {
  emit('update:open', !props.open)
}
</script>

<style scoped>
.fold-section {
  background: var(--md-surface-container-low, #f7f8fa);
  border: 1px solid var(--md-outline-variant, #e8eaee);
  border-radius: 12px;
  margin-bottom: 14px;
  overflow: hidden;
  transition: border-color 0.2s ease;
}

.fold-section:hover {
  border-color: var(--md-outline, #c3c6cc);
}

.fold-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}

.fold-chevron {
  color: var(--md-on-surface-variant, #666);
  transition: transform 0.2s ease;
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

.tone-todo .fold-dot { background: #0066cc; }
.tone-running .fold-dot { background: #fa8c16; box-shadow: 0 0 6px rgba(250, 140, 22, 0.6); }
.tone-done .fold-dot { background: #52c41a; }
.tone-neutral .fold-dot { background: var(--md-outline, #999); }

.fold-title {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.fold-count {
  font-size: 12px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--md-surface-container, #eaecf0);
  color: var(--md-on-surface-variant, #44474d);
}

.fold-hint {
  font-size: 12px;
  color: var(--md-on-surface-variant-2, #61686f);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.fold-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.fold-body {
  padding: 4px 16px 16px;
}
</style>
