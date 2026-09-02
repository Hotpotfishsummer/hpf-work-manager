<template>
  <div class="global-search">
    <el-input
      v-model="query"
      placeholder="搜索项目、任务、里程碑… (至少 2 字符)"
      size="default"
      clearable
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      class="search-input"
    >
      <template #prefix>
        <el-icon class="search-icon"><Search /></el-icon>
      </template>
      <template #suffix v-if="loading">
        <el-icon class="loading-icon"><Loading /></el-icon>
      </template>
    </el-input>

    <el-dropdown
      v-if="showDropdown && results.length > 0"
      trigger="click"
      placement="bottom-start"
      :hide-on-click="false"
      class="search-dropdown"
    >
      <template #dropdown>
        <el-dropdown-menu class="search-dropdown-menu">
          <el-dropdown-item
            v-for="item in results"
            :key="`${item.type}-${item.id}`"
            :disabled="false"
            class="search-result-item"
            @click.native="selectResult(item)"
          >
            <div class="result-content">
              <div class="result-main">
                <el-icon :class="typeIconClass(item.type)" class="result-icon">
                  <component :is="typeIcon(item.type)" />
                </el-icon>
                <span class="result-name">{{ item.name }}</span>
                <el-tag :type="typeTagType(item.type)" size="small" class="result-type">
                  {{ typeLabel(item.type) }}
                </el-tag>
              </div>
              <div v-if="item.description" class="result-desc">{{ item.description }}</div>
              <div class="result-meta">
                <span v-if="item.project_name" class="result-project">{{ item.project_name }}</span>
                <span v-else-if="item.project_id" class="result-project">项目 #{{ item.project_id }}</span>
                <span v-if="item.due_date" class="result-due">截止：{{ item.due_date }}</span>
                <span v-if="item.status" class="result-status">{{ statusLabel(item.status) }}</span>
              </div>
            </div>
          </el-dropdown-item>
          <el-dropdown-item disabled class="search-result-footer">
            共 {{ total }} 条结果
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Loading, Folder, Document, Flag } from '@element-plus/icons-vue'
import { searchApi } from '@/api'
import type { SearchResultItem } from '@/types'
import { useRouter } from 'vue-router'

const router = useRouter()

const query = ref('')
const results = ref<SearchResultItem[]>([])
const total = ref(0)
const loading = ref(false)
const showDropdown = ref(false)
const focused = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null
// 请求序号守卫：慢请求晚返回时丢弃过期结果（axios abort 需全链路透传 signal，此处以序号实现同等效果）
let latestSeq = 0

const DEBOUNCE_MS = 300
const MIN_QUERY_LENGTH = 2

function typeIcon(type: string) {
  switch (type) {
    case 'project':
      return Folder
    case 'task':
      return Document
    case 'milestone':
      return Flag
    default:
      return Document
  }
}

function typeIconClass(type: string) {
  switch (type) {
    case 'project':
      return 'icon-project'
    case 'task':
      return 'icon-task'
    case 'milestone':
      return 'icon-milestone'
    default:
      return ''
  }
}

function typeTagType(type: string) {
  switch (type) {
    case 'project':
      return 'primary'
    case 'task':
      return 'info'
    case 'milestone':
      return 'warning'
    default:
      return 'info'
  }
}

function typeLabel(type: string) {
  switch (type) {
    case 'project':
      return '项目'
    case 'task':
      return '任务'
    case 'milestone':
      return '里程碑'
    default:
      return type
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'todo':
      return '待办'
    case 'in_progress':
      return '进行中'
    case 'done':
      return '已完成'
    case 'active':
      return '进行中'
    case 'archived':
      return '已归档'
    default:
      return status
  }
}

async function doSearch(q: string) {
  if (q.length < MIN_QUERY_LENGTH) {
    results.value = []
    total.value = 0
    showDropdown.value = false
    return
  }

  const seq = ++latestSeq
  loading.value = true

  try {
    const res = await searchApi.global(q)
    if (seq !== latestSeq) return // 已有更新的搜索，丢弃过期结果
    results.value = res.items
    total.value = res.total
    showDropdown.value = true
  } catch (err) {
    console.error('Search failed:', err)
    if (seq !== latestSeq) return
    results.value = []
    total.value = 0
    showDropdown.value = false
  } finally {
    if (seq === latestSeq) loading.value = false
  }
}

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    doSearch(query.value.trim())
  }, DEBOUNCE_MS)
}

function onFocus() {
  focused.value = true
  if (query.value.trim().length >= MIN_QUERY_LENGTH && results.value.length > 0) {
    showDropdown.value = true
  }
}

function onBlur() {
  focused.value = false
  // 延迟隐藏，允许点击下拉项
  setTimeout(() => {
    if (!focused.value) showDropdown.value = false
  }, 150)
}

function selectResult(item: SearchResultItem) {
  showDropdown.value = false
  query.value = ''
  navigateToResult(item)
}

function navigateToResult(item: SearchResultItem) {
  const pid = item.project_id
  if (!pid) return

  switch (item.type) {
    case 'project':
      router.push(`/projects/${pid}`)
      break
    case 'task':
      router.push(`/projects/${pid}/tasks`)
      break
    case 'milestone':
      router.push(`/projects/${pid}`)
      break
  }
}

// 点击外部关闭
function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.global-search')) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (debounceTimer) clearTimeout(debounceTimer)
  latestSeq += 1 // 使在途请求结果全部失效
})
</script>

<style scoped>
.global-search {
  position: relative;
  width: 320px;
  max-width: 100%;
}

.search-input {
  width: 100%;
}

.search-icon {
  color: var(--md-on-surface-variant);
}

.loading-icon {
  color: var(--md-primary);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 200;
  margin-top: var(--md-space-1);
}

.search-dropdown-menu {
  min-width: 320px;
  max-width: 480px;
  padding: var(--md-space-1);
  border-radius: var(--md-radius-lg);
  box-shadow: var(--md-elevation-3);
  border: 1px solid var(--md-outline-variant);
}

.search-result-item {
  padding: var(--md-space-2) var(--md-space-3) !important;
  border-radius: var(--md-radius-md);
  transition: background-color 0.1s ease;
}

.search-result-item:hover {
  background-color: var(--md-surface-container-high);
}

.search-result-item.is-disabled {
  opacity: 0.5;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-1);
}

.result-main {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
}

.result-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.icon-project {
  color: var(--md-primary);
}

.icon-task {
  color: var(--md-on-surface-variant);
}

.icon-milestone {
  color: var(--md-warning);
}

.result-name {
  font-size: var(--md-text-body-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-type {
  flex-shrink: 0;
}

.result-desc {
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface-variant);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--md-space-2);
  font-size: var(--md-text-label-sm);
  color: var(--md-on-surface-variant);
}

.result-project {
  font-weight: var(--md-weight-medium);
}

.result-due {
  color: var(--md-warning);
}

.result-status {
  text-transform: capitalize;
}

.search-result-footer {
  text-align: center;
  color: var(--md-on-surface-variant);
  font-size: var(--md-text-label-sm);
  padding: var(--md-space-2) !important;
}
</style>