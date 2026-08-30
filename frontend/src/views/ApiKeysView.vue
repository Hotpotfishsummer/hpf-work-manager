<template>
  <div class="page-container keys-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">API Keys</h1>
        <p class="page-sub">为 AI 编码工具生成长期访问凭证，用于自动更新任务/项目进度。</p>
      </div>
      <el-button type="primary" @click="openCreate">新建 Key</el-button>
    </div>

    <el-alert
      v-if="visibleKey"
      type="success"
      :closable="true"
      show-icon
      class="key-alert"
      @close="visibleKey = ''"
    >
      <template #title>
        已生成 Key <code>{{ visibleKey }}</code> — <strong>仅此一次显示</strong>，请立即复制保存。
      </template>
      <template #default>
        <el-button size="small" @click="copyKey(visibleKey)">复制</el-button>
      </template>
    </el-alert>

    <el-table :data="keys" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column label="前缀" min-width="120">
        <template #default="{ row }">
          <code>{{ row.prefix }}</code>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.revoked_at" type="danger" effect="plain">已撤销</el-tag>
          <el-tag v-else type="success" effect="plain">有效</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最近使用" min-width="160">
        <template #default="{ row }">{{ row.last_used_at ? fmtDate(row.last_used_at) : '—' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" min-width="160">
        <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110" align="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.revoked_at"
            link
            type="danger"
            @click="revoke(row)"
          >撤销</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && keys.length === 0" description="还没有 API Key，点击右上角创建" :image-size="80" />

    <el-dialog v-model="createVisible" title="新建 API Key" width="420px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Key 名称">
          <el-input v-model="name" placeholder="如：Claude Code / Cursor / 自建 agent" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!name.trim()" :loading="creating" @click="create">
          生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { keyApi } from '@/api'
import type { ApiKey } from '@/types'

const keys = ref<ApiKey[]>([])
const loading = ref(false)
const createVisible = ref(false)
const creating = ref(false)
const name = ref('')
const visibleKey = ref('')

async function load() {
  loading.value = true
  try {
    keys.value = await keyApi.list()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  name.value = ''
  createVisible.value = true
}

async function create() {
  creating.value = true
  try {
    const res = await keyApi.create({ name: name.value.trim() })
    visibleKey.value = res.key
    createVisible.value = false
    await load()
  } finally {
    creating.value = false
  }
}

function fmtDate(d: string | null) {
  if (!d) return ''
  return d.slice(0, 10)
}

async function copyKey(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 非安全上下文（http）或剪贴板不可用时退回传统方案
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
    } catch {
      ElMessage.error('复制失败，请手动复制')
      document.body.removeChild(ta)
      return
    }
    document.body.removeChild(ta)
  }
  ElMessage.success('已复制')
}

async function revoke(row: ApiKey) {
  try {
    await ElMessageBox.confirm(
      `撤销后该 Key 立即失效，且无法恢复。确认撤销「${row.name}」？`,
      '撤销确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  await keyApi.revoke(row.id)
  ElMessage.success('已撤销')
  await load()
}

onMounted(load)
</script>

<style scoped>
.keys-page {
  padding-top: var(--md-space-6);
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--md-space-5);
}
.page-title {
  font-size: var(--md-text-display-sm);
  font-weight: var(--md-weight-semibold);
  color: var(--md-on-surface);
}
.page-sub {
  color: var(--md-on-surface-variant);
  margin-top: var(--md-space-1);
  font-size: var(--md-text-body-sm);
}
.key-alert {
  margin-bottom: var(--md-space-4);
}
.key-alert :deep(code) {
  font-family: var(--md-font-mono);
  background: var(--md-surface-container-high);
  padding: 1px var(--md-space-2);
  border-radius: var(--md-radius-sm);
}
</style>