<template>
  <div
    class="live-indicator"
    role="status"
    aria-live="polite"
    :title="tooltip"
  >
    <span
      class="live-dot"
      :class="{ connected: connected, disconnected: !connected && !isReconnectable, reconnectable: isReconnectable }"
      aria-hidden="true"
    />
    <span class="live-text" v-if="!connected && !isReconnectable">连接中…</span>
    <span class="live-text" v-else-if="connected">实时</span>
    <el-button
      v-else
      class="reconnect-btn"
      size="small"
      variant="text"
      @click="$emit('reconnect')"
    >
      重连
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  connected: boolean
  isReconnectable: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ reconnect: [] }>()

const tooltip = computed(() => {
  if (props.connected) return 'SSE 连接正常，实时同步已启用'
  if (props.isReconnectable) return 'SSE 连接已断开，点击重连'
  return '正在尝试连接 SSE…'
})
</script>

<style scoped>
.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  white-space: nowrap;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--md-radius-full);
  transition: background-color var(--md-duration-standard) var(--md-ease-standard),
    box-shadow var(--md-duration-standard) var(--md-ease-standard);
}

.live-dot.connected {
  background-color: var(--md-status-done);
  box-shadow: 0 0 6px var(--md-status-done);
}

.live-dot.disconnected {
  background-color: var(--md-on-surface-variant);
  opacity: 0.5;
}

.live-dot.reconnectable {
  background-color: var(--md-status-overdue);
  box-shadow: 0 0 6px var(--md-status-overdue);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.live-text {
  font-weight: var(--md-weight-medium);
}

.reconnect-btn {
  margin-left: var(--md-space-1);
}
.reconnect-btn :deep(.el-button__text) {
  font-weight: var(--md-weight-semibold);
}
</style>