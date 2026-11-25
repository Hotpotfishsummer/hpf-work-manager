<template>
  <div class="page">
    <!-- 页面头部：标题 + 唯一的主按钮 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">项目</h1>
        <p class="page-sub">Projects · 管理你的全部项目与进度</p>
      </div>
      <div class="head-actions">
        <el-button plain size="large" :loading="syncing" @click="syncLocalProjects">
          <el-icon><Refresh /></el-icon>
          同步本地项目库
        </el-button>
        <el-button type="primary" size="large" @click="openCreate">
          <el-icon><Plus /></el-icon>
          新建项目
        </el-button>
      </div>
    </div>

    <!-- 状态筛选：筛选芯片 -->
    <div class="filter-chips">
      <button
        v-for="opt in STATUS_OPTIONS"
        :key="opt.value"
        type="button"
        class="md-chip md-chip--filter"
        :class="{ 'is-selected': statusFilter === opt.value }"
        :aria-pressed="statusFilter === opt.value"
        @click="setStatusFilter(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- 项目卡片网格：4-up → 2-up → 1-up -->
    <div v-loading="loading" class="project-grid">
      <div
        v-for="p in projects"
        :key="p.id"
        class="project-card"
        :class="{ 'is-archived': p.status !== 'active' }"
        role="button"
        tabindex="0"
        @click="goDetail(p.id)"
        @keydown.enter.prevent="goDetail(p.id)"
      >
        <!-- 卡片操作菜单 -->
        <el-dropdown trigger="click" class="card-menu" @command="(cmd: string) => onCardCommand(cmd, p)" @click.stop>
          <span class="card-menu-trigger" role="button" aria-label="项目操作菜单" title="项目操作菜单" @click.stop>
            <el-icon><MoreFilled /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="edit">编辑</el-dropdown-item>
              <el-dropdown-item v-if="p.status === 'active'" command="archive">归档</el-dropdown-item>
              <el-dropdown-item v-else command="restore">取消归档</el-dropdown-item>
              <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- 项目名首字块 -->
        <div class="project-avatar" aria-hidden="true">{{ p.name.slice(0, 1).toUpperCase() }}</div>
        <h3 class="card-title">{{ p.name }}</h3>
        <p class="card-desc">{{ p.description || '暂无描述' }}</p>
        <div class="card-meta">
          <span class="md-chip md-chip--sm" :class="p.status === 'active' ? 'md-chip--primary' : 'md-chip--neutral'">
            {{ p.status === 'active' ? '进行中' : '已归档' }}
          </span>
          <span class="meta-date">{{ fmtDate(p.end_date) }}</span>
        </div>
        <button class="text-link-upper" tabindex="-1">
          查看项目<span class="chev">›</span>
        </button>
      </div>

      <el-empty v-if="!loading && projects.length === 0" description="还没有项目，点击右上角新建" />
    </div>

    <!-- 新建/编辑项目弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑项目' : '新建项目'"
      width="480px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="如：官网改版 2026" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="项目简介（可选）" />
        </el-form-item>
        <el-form-item label="起止日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="截止日期"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, MoreFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { projectApi } from '@/api'
import http from '@/api/http'
import type { Project } from '@/types'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)
const saving = ref(false)
const syncing = ref(false)

async function syncLocalProjects() {
  syncing.value = true
  try {
    const res: any = await http.post('/ideator/sync-projects')
    if (res && res.synced_count > 0) {
      ElMessage.success(`成功导入 ${res.synced_count} 个本地独立代码库项目！`)
    } else {
      ElMessage.info('本地代码库已全部同步建档为独立项目')
    }
    await load()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '同步项目失败')
  } finally {
    syncing.value = false
  }
}
const dialogVisible = ref(false)
const editing = ref<Project | null>(null)
const statusFilter = ref<'active' | 'archived'>('active')
// 筛选芯片选项；点击时赋值并重新拉取（等价原 el-radio-group v-model + @change="load"）
const STATUS_OPTIONS: { value: 'active' | 'archived'; label: string }[] = [
  { value: 'active', label: '进行中' },
  { value: 'archived', label: '已归档' },
]
function setStatusFilter(v: 'active' | 'archived') {
  statusFilter.value = v
  load()
}
const formRef = ref<FormInstance>()

const form = reactive({ name: '', description: '' })
const dateRange = ref<[string, string] | null>(null)

const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

function fmtDate(d: string | null) {
  if (!d) return ''
  return d.slice(0, 10)
}

async function load() {
  loading.value = true
  try {
    projects.value = await projectApi.list(statusFilter.value)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  dateRange.value = null
  dialogVisible.value = true
}

function openEdit(p: Project) {
  editing.value = p
  form.name = p.name
  form.description = p.description ?? ''
  dateRange.value = [
    p.start_date ? p.start_date.slice(0, 10) : '',
    p.end_date ? p.end_date.slice(0, 10) : '',
  ]
  dialogVisible.value = true
}

async function onCardCommand(cmd: string, p: Project) {
  if (cmd === 'edit') openEdit(p)
  else if (cmd === 'archive') await setStatus(p, 'archived')
  else if (cmd === 'restore') await setStatus(p, 'active')
  else if (cmd === 'delete') await removeProject(p)
}

async function setStatus(p: Project, status: 'active' | 'archived') {
  await projectApi.update(p.id, { status })
  ElMessage.success(status === 'archived' ? '已归档' : '已取消归档')
  load()
}

async function removeProject(p: Project) {
  try {
    await ElMessageBox.confirm(`确定删除项目「${p.name}」吗？相关任务与里程碑将一并删除，且不可恢复。`, '删除项目', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await projectApi.remove(p.id)
  ElMessage.success('已删除')
  load()
}

function goDetail(id: number) {
  router.push(`/projects/${id}`)
}

async function save() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return

  saving.value = true
  try {
    const payload = {
      name: form.name,
      description: form.description || null,
      start_date: dateRange.value?.[0] ? dateRange.value[0] : null,
      end_date: dateRange.value?.[1] ? dateRange.value[1] : null,
    }
    if (editing.value) {
      await projectApi.update(editing.value.id, payload)
      ElMessage.success('已更新')
    } else {
      await projectApi.create(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.project-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--md-space-5);
  min-height: 240px;
}
@media (max-width: 1200px) { .project-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 1024px) { .project-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .project-grid { grid-template-columns: 1fr; } }

/* 状态筛选：筛选芯片 */
.filter-chips {
  display: flex;
  gap: var(--md-space-2);
  padding: var(--md-space-1) 0 var(--md-space-5);
}

/* 填充式项目卡片：无描边，悬停靠色阶变化 */
.project-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: var(--md-card-padding);
  background-color: var(--md-surface-container-highest);
  border: 0;
  border-radius: var(--md-shape-medium);
  color: var(--md-on-surface);
  cursor: pointer;
  transition: background-color var(--md-duration-short-4) var(--md-ease-standard);
}
.project-card:hover {
  background-color: var(--md-surface-container-high);
}
.project-card:focus-visible { outline-offset: 2px; }
/* 主色左侧强调条：进行中才亮 */
.project-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: var(--md-space-4);
  bottom: var(--md-space-4);
  width: var(--md-accent-bar-width);
  border-radius: var(--md-shape-full);
  background-color: var(--md-primary);
}
.project-card.is-archived::before { background-color: var(--md-outline); }

/* 项目名首字块：primary-container */
.project-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin-bottom: var(--md-space-4);
  border-radius: var(--md-shape-medium);
  background-color: var(--md-primary-container);
  color: var(--md-on-primary-container);
  font-size: var(--md-type-headline-sm);
  line-height: var(--md-type-headline-lh-sm);
  font-weight: var(--md-weight-medium);
}
.project-card.is-archived .project-avatar {
  background-color: var(--md-surface-container);
  color: var(--md-on-surface-variant);
}

.card-title {
  margin: 0;
  padding-right: var(--md-space-6);
  font-size: var(--md-type-title-md);
  line-height: var(--md-type-title-lh-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}
.card-desc {
  margin: var(--md-space-1) 0 var(--md-space-4);
  font-size: var(--md-type-body-sm);
  line-height: var(--md-type-body-lh-sm);
  color: var(--md-on-surface-variant);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}
.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--md-space-3);
}
.meta-date {
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface-variant);
}

/* 文字按钮（查看项目） */
.text-link-upper {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  background: transparent;
  border: none;
  padding: 0;
  font-family: var(--md-font);
  font-size: var(--md-type-label-lg);
  font-weight: var(--md-weight-medium);
  letter-spacing: var(--md-tracking-label);
  color: var(--md-primary);
  cursor: pointer;
}
.chev { font-size: var(--md-type-body-lg); line-height: 1; }

/* 卡片右上角操作菜单：图标按钮 */
.card-menu {
  position: absolute;
  top: var(--md-space-2);
  right: var(--md-space-2);
}
.card-menu-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--md-control-height);
  height: var(--md-control-height);
  border-radius: var(--md-shape-full);
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: background-color var(--md-duration-short-4) var(--md-ease-standard);
}
.card-menu-trigger:hover {
  background-color: var(--md-surface-container-high);
}
.project-card:hover .card-menu-trigger:hover {
  background-color: var(--md-surface-container);
}
</style>
