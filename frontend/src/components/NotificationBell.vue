<template>
  <el-popover v-model:visible="open" placement="bottom-end" :width="340" trigger="click" popper-class="notify-popper">
    <template #reference>
      <button class="notify-btn" title="通知中心" @click="onToggle">
        <el-badge :value="unread" :hidden="unread === 0" :max="99" type="danger">
          <el-icon :size="17"><Bell /></el-icon>
        </el-badge>
      </button>
    </template>

    <div class="notify-head">
      <span class="notify-title">通知中心</span>
      <span class="notify-conn" :class="connected ? 'is-on' : 'is-off'">
        {{ connected ? '实时' : '已断开' }}
      </span>
      <el-button v-if="!connected && reconnectable" link size="small" @click="reconnect">重连</el-button>
      <el-button v-if="unread > 0" link size="small" @click="markAllRead">全部已读</el-button>
    </div>

    <el-scrollbar max-height="360px">
      <template v-if="list.length">
        <div
          v-for="n in list"
          :key="n.id"
          class="notify-item"
          :class="{ 'is-unread': isUnread(n) }"
          role="button"
          tabindex="0"
          @click="go(n)"
          @keydown.enter="go(n)"
        >
          <el-tag :type="tagType(n.type)" size="small" effect="plain" class="notify-tag">
            {{ TYPE_LABEL[n.type] ?? n.type }}
          </el-tag>
          <span class="notify-text">
            {{ ENTITY_LABEL[n.entity] ?? n.entity }} #{{ n.entity_id }}
            <em class="notify-project">· 项目 #{{ n.project_id }}</em>
          </span>
          <span class="notify-time">{{ relTime(n.ts) }}</span>
        </div>
      </template>
      <div v-else class="notify-empty">暂无通知——AI 工具或队友更新任务时会在这里提示</div>
    </el-scrollbar>
  </el-popover>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { ENTITY_LABEL, TYPE_LABEL, useNotifications, type NotificationItem } from '@/stores/notifications'

const router = useRouter()
const { list, unread, connected, reconnectable, lastReadTs, reconnect, markAllRead } =
  useNotifications()
const open = ref(false)

function onToggle() {
  // 打开面板即清空未读（内容保留，仅推进已读水位）
  if (!open.value) markAllRead()
}

function isUnread(n: NotificationItem) {
  // 按已读水位判断（与角标同口径）；此前"60 秒窗口"在刷新后永久丢失高亮
  return new Date(n.ts).getTime() > lastReadTs.value
}

function tagType(t: string) {
  if (t === 'created') return 'success'
  if (t === 'deleted') return 'danger'
  return 'info'
}

function relTime(ts: string) {
  const diff = Date.now() - new Date(ts).getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return ts.slice(0, 10)
}

function go(n: NotificationItem) {
  open.value = false
  const sub = n.entity === 'log' || n.entity === 'session' ? '/logs' : n.entity === 'milestone' ? '' : '/tasks'
  router.push(`/projects/${n.project_id}${sub}`)
}
</script>

<style scoped>
.notify-btn {
  width: var(--md-control-height);
  height: var(--md-control-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-full);
  background: transparent;
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.notify-btn:hover {
  background-color: var(--md-surface-container-high);
  color: var(--md-on-surface);
  border-color: var(--md-outline);
}
.notify-head {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  padding: 0 0 var(--md-space-2);
  border-bottom: 1px solid var(--md-outline-variant);
}
.notify-title {
  font-weight: var(--md-weight-semibold);
  font-size: var(--md-text-body-md);
  color: var(--md-on-surface);
}
.notify-conn {
  font-size: var(--md-text-label-sm);
  padding: 0 var(--md-space-1);
  border-radius: var(--md-radius-sm);
}
.notify-conn.is-on { color: var(--md-success, var(--md-status-done)); }
.notify-conn.is-off { color: var(--md-on-surface-variant); }
.notify-item {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  padding: var(--md-space-2) var(--md-space-1);
  border-radius: var(--md-radius-md);
  cursor: pointer;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface);
}
.notify-item:hover { background-color: var(--md-surface-container-high); }
.notify-item.is-unread { background-color: var(--md-surface-container); }
.notify-text { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.notify-project { font-style: normal; color: var(--md-on-surface-variant); }
.notify-time { font-size: var(--md-text-label-sm); color: var(--md-on-surface-variant); flex-shrink: 0; }
.notify-empty {
  padding: var(--md-space-6) var(--md-space-2);
  text-align: center;
  color: var(--md-on-surface-variant);
  font-size: var(--md-text-body-sm);
}
@media (max-width: 560px) {
  .notify-btn { display: none; } /* 极小屏收起，与顶栏适配策略一致 */
}
</style>
