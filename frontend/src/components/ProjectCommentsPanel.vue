<template>
  <div class="pcp">
    <div class="pcp-intro">
      <p class="pcp-lead">
        这里写的话会留给<b>下一次接手「{{ projectName }}」的 Agent</b>：下一步往哪走、优先级怎么排、什么别碰。
        主页「复制 Prompt」「夜班指令包」会自动带上未处理的指示。
      </p>
      <el-radio-group v-model="showResolved" size="small">
        <el-radio-button :value="false">待处理 {{ open.length }}</el-radio-button>
        <el-radio-button :value="true">已处理 {{ resolved.length }}</el-radio-button>
      </el-radio-group>
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
          <span v-if="c.resolved" class="pcp-resolved-tag">已处理 {{ fmt(c.resolved_at) }}</span>
          <span class="pcp-item-actions">
            <el-tooltip v-if="!showResolved" content="标记已处理：后续 Agent 不再读到这条" placement="top">
              <button type="button" class="pcp-icon-btn ok" title="标记已处理" @click="resolve(c, true)">✓</button>
            </el-tooltip>
            <el-tooltip v-else content="重新打开：这条指示重新生效" placement="top">
              <button type="button" class="pcp-icon-btn" title="重新打开" @click="resolve(c, false)">↩</button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <button type="button" class="pcp-icon-btn danger" title="删除" @click="remove(c)">✕</button>
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
  gap: 12px;
}

.pcp-intro {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.pcp-lead {
  margin: 0;
  font-size: var(--md-text-label-md);
  line-height: 1.6;
  color: var(--md-on-surface-variant);
}

.pcp-composer {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: 10px;
}

.pcp-composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.pcp-kbd-hint {
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
}

.pcp-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 48px;
}

.pcp-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 12px;
  border: 1px dashed var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}

.pcp-empty-icon {
  font-size: var(--md-text-title-lg);
}

.pcp-item {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-left: var(--md-accent-bar-width) solid var(--md-primary);
  border-radius: var(--md-radius-md);
  padding: 10px 12px;
}

.pcp-item.is-resolved {
  border-left-color: var(--md-success);
  opacity: 0.78;
}

.pcp-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
}

.pcp-author {
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-surface);
}

.pcp-resolved-tag {
  color: var(--md-on-success-container);
}

.pcp-item-actions {
  margin-left: auto;
  display: flex;
  gap: 4px;
}

.pcp-icon-btn {
  width: 24px;
  height: 24px;
  border-radius: var(--md-radius-sm);
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-size: var(--md-text-label-md);
  line-height: 1;
  color: var(--md-on-surface-variant);
}

.pcp-icon-btn:hover {
  background: var(--md-surface-container);
}

.pcp-icon-btn.ok:hover {
  color: var(--md-on-success-container);
}

.pcp-icon-btn.danger:hover {
  color: var(--md-on-error-container);
}

.pcp-content {
  margin: 6px 0 0;
  font-size: var(--md-text-label-md);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--md-on-surface);
}
</style>
