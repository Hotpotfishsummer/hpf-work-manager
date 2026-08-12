<template>
  <div class="page-container">
    <!-- 页面头部：display-lg 标题 + 主按钮 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">项目</h1>
        <p class="page-sub">PROJECTS · 管理你的全部项目与进度</p>
      </div>
      <el-button type="primary" size="large" @click="openCreate">
        <el-icon style="margin-right: 6px"><Plus /></el-icon>
        新建项目
      </el-button>
    </div>

    <!-- 项目卡片网格：4-up → 2-up → 1-up -->
    <div v-loading="loading" class="project-grid">
      <div v-for="p in projects" :key="p.id" class="model-card" @click="goDetail(p.id)">
        <!-- model-card-photo：surface-card 底板 -->
        <div class="model-card-photo">
          <span class="photo-badge">{{ p.name.slice(0, 1).toUpperCase() }}</span>
        </div>
        <h3 class="card-title">{{ p.name }}</h3>
        <p class="card-desc">{{ p.description || '暂无描述' }}</p>
        <div class="card-meta">
          <el-tag
            :type="p.status === 'active' ? 'primary' : 'info'"
            effect="plain"
            size="small"
          >
            {{ p.status === 'active' ? '进行中' : '已归档' }}
          </el-tag>
          <span class="meta-date">{{ fmtDate(p.end_date) }}</span>
        </div>
        <button class="text-link-upper">
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
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { projectApi } from '@/api'
import type { Project } from '@/types'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref<Project | null>(null)
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
    projects.value = await projectApi.list()
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
      start_date: dateRange.value?.[0] ?? null,
      end_date: dateRange.value?.[1] ?? null,
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
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--md-space-6) 0 var(--md-space-6);
}
.page-title {
  margin: 0;
  font-size: var(--md-text-display-lg);
  line-height: 1.1;
}
.page-sub {
  margin: var(--md-space-1) 0 0;
  font-size: var(--md-text-body-sm);
  font-weight: var(--md-weight-regular);
  color: var(--md-on-surface-variant);
  letter-spacing: 1.5px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--md-space-5);
  min-height: 240px;
}
@media (max-width: 1200px) { .project-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 1024px) { .project-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .project-grid { grid-template-columns: 1fr; } }

/* model-card：圆角卡片 */
.model-card {
  background-color: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg);
  padding: var(--md-space-5);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s ease, box-shadow 0.18s ease, transform 0.18s ease;
}
.model-card:hover {
  border-color: var(--md-primary);
  box-shadow: var(--md-shadow-1);
  transform: translateY(-2px);
}

/* model-card-photo：底板 */
.model-card-photo {
  background-color: var(--md-surface-container-high);
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--md-space-4);
  border-radius: var(--md-radius-md);
}
.photo-badge {
  font-size: 40px;
  font-weight: var(--md-weight-bold);
  color: var(--md-primary);
}

.card-title {
  margin: 0;
  font-size: var(--md-text-title-md);
  font-weight: var(--md-weight-bold);
  color: var(--md-on-surface);
}
.card-desc {
  margin: var(--md-space-1) 0 var(--md-space-4);
  font-size: var(--md-text-body-sm);
  font-weight: var(--md-weight-regular);
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
  margin-bottom: var(--md-space-4);
}
.meta-date {
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}
</style>
