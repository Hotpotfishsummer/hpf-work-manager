<template>
  <div class="pcp">
    <div class="pcp-intro">
      <p class="pcp-lead">
        这里写的话会留给<b>下一次接手「{{ projectName }}」的 Agent</b>：下一步往哪走、优先级怎么排、什么别碰。
        主页「复制 Prompt」「夜班指令包」会自动带上未处理的指示。
      </p>
      <div class="pcp-filters">
        <button
          type="button"
          class="md-chip md-chip--filter"
          :class="{ 'is-selected': !showResolved }"
          :aria-pressed="!showResolved"
          @click="showResolved = false"
        >
          待处理 {{ open.length }}
        </button>
        <button
          type="button"
          class="md-chip md-chip--filter"
          :class="{ 'is-selected': showResolved }"
          :aria-pressed="showResolved"
          @click="showResolved = true"
        >
          已处理 {{ resolved.length }}
        </button>
      </div>
    </div>

      <div v-if="!showResolved" class="pcp-composer">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        maxlength="2000"
        show-word-limit
        resize="none"
        :placeholder="`例：下一步优先把备份恢复做成一键脚本；暂时不要动 MCP 工具签名。`"
        @keydown.ctrl.enter.prevent="submit"
        @keydown.meta.enter.prevent="submit"
      />
      <div class="pcp-composer-foot">
        <span class="pcp-kbd-hint">Ctrl / ⌘ + Enter 快速提交</span>
        <el-button type="primary" size="small" :loading="submitting" :disabled="!draft.trim()" @click="submit">
          留下指示
        </el-button>
      </div>
    </div>

    <div v-loading="loading" class="pcp-list">
      <div v-if="visible.length === 0" class="pcp-empty">
        <span class="pcp-empty-icon">{{ showResolved ? '📦' : '💬' }}</span>
        <span>{{ showResolved ? '还没有已处理的指示' : '暂无待处理指示 —— 现在留一条，Agent 下次开工就能看到' }}</span>
      </div>
      <div
        v-for="c in visible"
        :key="c.id"
        class="pcp-item"
        :class="{ 'is-resolved': c.resolved }"
      >
        <div class="pcp-item-head">
          <span class="pcp-author">{{ c.author_username }}</span>
          <span class="pcp-time">{{ fmt(c.created_at) }}</span>
          <span v-if="c.resolved" class="md-chip md-chip--sm md-chip--success">已处理 {{ fmt(c.resolved_at) }}</span>
          <span class="pcp-item-actions">
            <el-tooltip v-if="!showResolved" content="标记已处理：后续 Agent 不再读到这条" placement="top">
              <button type="button" class="pcp-icon-btn ok" title="标记已处理" aria-label="标记已处理" @click="resolve(c, true)">✓</button>
            </el-tooltip>
            <el-tooltip v-else content="重新打开：这条指示重新生效" placement="top">
              <button type="button" class="pcp-icon-btn" title="重新打开" aria-label="重新打开" @click="resolve(c, false)">↩</button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <button type="button" class="pcp-icon-btn danger" title="删除" aria-label="删除" @click="remove(c)">✕</button>
            </el-tooltip>
          </span>
        </div>
        <p class="pcp-content">{{ c.content }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api/http'

interface ProjectComment {
  id: number
  project_id: number
  author_username: string
  content: string
  created_at: string
  resolved_at: string | null
  resolved: boolean
}

const props = withDefaults(
  defineProps<{ projectId: number; projectName?: string; autoload?: boolean }>(),
  { projectName: '', autoload: true },
)

const emit = defineEmits<{ (e: 'changed'): void }>()

const loading = ref(false)
const submitting = ref(false)
const draft = ref('')
const showResolved = ref(false)
const comments = ref<ProjectComment[]>([])

const open = computed(() => comments.value.filter((c) => !c.resolved))
const resolved = computed(() => comments.value.filter((c) => c.resolved))
const visible = computed(() => (showResolved.value ? resolved.value : open.value))

function fmt(ts?: string | null) {
  if (!ts) return ''
  // 库里是 UTC，按浏览器本地时间显示到分钟
  const d = new Date(ts)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function reload() {
  if (!props.projectId) return
  loading.value = true
  try {
    const res: any = await http.get(`/projects/${props.projectId}/comments`, {
      params: { include_resolved: true },
    })
    comments.value = res || []
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载项目指示失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  const content = draft.value.trim()
  if (!content) return
  submitting.value = true
  try {
    await http.post(`/projects/${props.projectId}/comments`, { content })
    draft.value = ''
    showResolved.value = false
    await reload()
    emit('changed')
    ElMessage.success('已留下指示，Agent 下次读取该项目时会看到')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function resolve(c: ProjectComment, value: boolean) {
  try {
    await http.post(`/comments/${c.id}/resolve`, { resolved: value })
    await reload()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function remove(c: ProjectComment) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确定删除这条指示？', '删除指示', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await http.delete(`/comments/${c.id}`)
    await reload()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// 调用方可以通过模板 ref 在 SSE 事件到来时刷新
defineExpose({ reload })

onMounted(() => {
  if (props.autoload) reload()
})

watch(
  () => props.projectId,
  () => {
    showResolved.value = false
    if (props.autoload) reload()
  },
)
</script>

<style scoped>
.pcp {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-3);
}

.pcp-intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-4);
  flex-wrap: wrap;
}
.pcp-lead {
  margin: 0;
  font-size: var(--md-type-label-md);
  line-height: var(--md-type-body-lh-md);
  color: var(--md-on-surface-variant);
}
.pcp-filters { display: flex; gap: var(--md-space-2); }

/* 输入区：表面色块，不描框 */
.pcp-composer {
  background-color: var(--md-surface);
  border-radius: var(--md-shape-medium);
  padding: var(--md-space-3);
}
.pcp-composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--md-space-2);
}
.pcp-kbd-hint {
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
}

/* 条目：分隔线分行，不逐条描框 */
.pcp-list {
  display: flex;
  flex-direction: column;
  min-height: 48px;
}
.pcp-item {
  padding: var(--md-space-3) var(--md-space-2);
}
.pcp-item + .pcp-item {
  border-top: 1px solid var(--md-outline-variant);
}
.pcp-item.is-resolved .pcp-content {
  color: var(--md-on-surface-variant);
}

.pcp-empty {
  display: flex;
  align-items: center;
  gap: var(--md-space-3);
  padding: var(--md-space-4) var(--md-space-2);
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}
.pcp-empty-icon {
  font-size: var(--md-type-title-lg);
  line-height: 1;
}

.pcp-item-head {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
}
.pcp-author {
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}
.pcp-item-actions {
  margin-left: auto;
  display: flex;
  gap: var(--md-space-1);
}

/* 图标按钮：32px 点击区 */
.pcp-icon-btn {
  width: var(--md-control-height-sm);
  height: var(--md-control-height-sm);
  border: 0;
  border-radius: var(--md-shape-full);
  background-color: transparent;
  cursor: pointer;
  font-size: var(--md-type-label-lg);
  line-height: 1;
  color: var(--md-on-surface-variant);
}
.pcp-icon-btn:hover {
  background-color: color-mix(in srgb, var(--md-on-surface) var(--md-state-hover), transparent);
}
.pcp-icon-btn.ok:hover { color: var(--md-success); }
.pcp-icon-btn.danger:hover { color: var(--md-error); }

.pcp-content {
  margin: var(--md-space-1) 0 0;
  font-size: var(--md-type-label-md);
  line-height: var(--md-type-body-lh-md);
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--md-on-surface);
}
</style>
