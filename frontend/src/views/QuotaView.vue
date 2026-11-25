<template>
  <div class="page quota-view" v-loading="loading">
    <div class="page-head">
      <div>
        <h1 class="page-title">⚡ 5h 算力配额与自主调度雷达 (Quota Radar)</h1>
        <p class="page-sub">监控 MiniMax / DeepSeek 5小时滚动算力窗口与每周余量，规划夜间无人值守开发批次，告别“有额度无目标，有目标无额度”。</p>
      </div>
      <el-button type="primary" plain @click="fetchData">
        <el-icon><Refresh /></el-icon> 刷新配额探针
      </el-button>
    </div>

    <!-- 算力大盘仪表卡片 -->
    <div class="dashboard-grid">
      <!-- 5小时当前窗口 -->
      <div class="md-card metric-card">
        <div class="metric-head">
          <span class="head-title">5小时滚动算力余量</span>
          <el-tag :type="tagType" size="small" class="md-chip--sm">{{ quota.remaining_percent ?? 100 }}% 剩余</el-tag>
        </div>

        <div class="gauge-center">
          <div class="big-percent" :class="statusLevel">{{ quota.remaining_percent ?? 100 }}%</div>
          <div class="countdown-badge">
            <span class="hourglass">⏳</span>
            <span>距离窗口重置: <strong>{{ quota.minutes_left ?? 0 }}</strong> 分钟</span>
          </div>
        </div>

        <div class="progress-track">
          <div class="progress-bar" :class="statusLevel" :style="{ width: (quota.remaining_percent ?? 100) + '%' }"></div>
        </div>

        <div class="metric-footer-grid">
          <div class="meta-col">
            <span class="meta-label">重置时间点 (CST)</span>
            <span class="meta-val highlight">{{ quota.reset_time_str || '--:--:--' }}</span>
          </div>
          <div class="meta-col">
            <span class="meta-label">每周累计余量</span>
            <span class="meta-val">{{ quota.weekly_remaining_percent ?? 100 }}%</span>
          </div>
          <div class="meta-col">
            <span class="meta-label">夜间闲时状态 (23:00-07:00)</span>
            <span class="meta-val">{{ quota.is_night_shift ? '🌙 闲时时段 (睡眠开发黄金期)' : '☀️ 日间时段' }}</span>
          </div>
        </div>
      </div>

      <!-- 智能调度策略卡片 -->
      <div class="md-card strategy-card">
        <div class="metric-head">
          <span class="head-title">💡 当前时段调度推演建议</span>
          <span class="md-chip md-chip--sm strategy-badge" :class="strategyTone">
            {{ quota.remaining_percent >= 50 ? '算力充沛' : (quota.remaining_percent >= 20 ? '算力平稳' : '算力见底') }}
          </span>
        </div>

        <div class="strategy-content">
          <div class="md-callout sugg-box" :class="calloutTone">
            <div class="sugg-icon">⚡</div>
            <div class="sugg-text">
              <strong>策略提示：</strong>
              {{ quota.suggestion || '正在由配额探针与时间模型计算最优执行建议...' }}
            </div>
          </div>

          <div class="action-suggestions">
            <h4>💡 建议的下一步动作：</h4>
            <div class="suggestion-list">
            <div class="md-state suggestion-item" @click="router.push('/ideas')">
              <span class="item-icon">1</span>
              <div class="item-info">
                <span class="item-title">进行项目代码体检与 Next Steps 推演</span>
                <span class="item-sub">由 AI 深度扫描代码库与 TODOs，提炼 3 个高价值工单</span>
              </div>
              <span class="arrow">→</span>
            </div>

            <div class="md-state suggestion-item" @click="router.push('/')">
              <span class="item-icon">2</span>
              <div class="item-info">
                <span class="item-title">前往任务看板派发工单给 dsh</span>
                <span class="item-sub">一键复制 Prompt 给 DeepSeek Harness 执行当前高优任务</span>
              </div>
              <span class="arrow">→</span>
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 夜间无人值守任务调度包 (Night-Shift Autonomous Dispatcher) -->
    <div class="md-section nightshift-section">
      <div class="section-head">
        <div class="section-intro">
          <h2 class="md-section__title">🌙 夜间无人值守批次备单箱 (Night-Shift Dispatcher)</h2>
          <p class="sec-desc">
            为解决“睡眠时间浪费 5 小时额度”的问题，在此处勾选待办池任务，一键生成结构化夜间自主开发 Prompt，让 AI 在无人值守状态下逐个实现、编写测试并提交 commit。
          </p>
        </div>
        <el-button type="primary" size="large" :disabled="selectedTaskIds.length === 0" @click="generateAndCopyBatchPrompt">
          📋 复制已勾选 {{ selectedTaskIds.length }} 项的夜班批量 Prompt
        </el-button>
      </div>

      <div class="batch-table-container">
        <el-table
          :data="todoTasks"
          style="width: 100%"
          @selection-change="handleSelectionChange"
          empty-text="当前待办池为空，请先在看板中创建或推演工单"
        >
          <el-table-column type="selection" width="50" />
          <el-table-column label="优先级" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="priorityTag(row.priority)">{{ priorityLabel(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="工单名称" min-width="200">
            <template #default="{ row }">
              <strong style="color: var(--md-on-surface)">{{ row.name }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="预估工时" width="100">
            <template #default="{ row }">
              <span>⏱️ {{ row.estimated_hours || 2 }}h</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="Prompt / 任务描述" min-width="300" show-overflow-tooltip />
          <el-table-column label="操作" width="140" align="right">
            <template #default="{ row }">
              <el-button size="small" text @click="copySingle(row)">复制单项</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 批量 Prompt 预览弹窗 -->
    <el-dialog
      v-model="batchModalOpen"
      title="🌙 夜间无人值守自主开发 Prompt (已复制至剪贴板)"
      width="720px"
      append-to-body
    >
      <el-input
        v-model="generatedPrompt"
        type="textarea"
        :rows="14"
        readonly
        class="batch-dialog-input"
      />
      <template #footer>
        <el-button @click="batchModalOpen = false">完成</el-button>
        <el-button type="primary" @click="reCopy">重新复制</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import http from '@/api/http'
import { copyText } from '@/utils/clipboard'

const router = useRouter()
const loading = ref(false)
const quota = ref<any>({})
const todoTasks = ref<any[]>([])
const selectedTaskIds = ref<number[]>([])

const batchModalOpen = ref(false)
const generatedPrompt = ref('')

const statusLevel = computed(() => {
  const p = quota.value.remaining_percent ?? 100
  if (p <= 10) return 'critical'
  if (p <= 30) return 'warning'
  return 'good'
})

/** 纯展示：健康度 → 色调类名（良好 primary / 注意 warning / 紧急 error） */
const strategyTone = computed(() => ({ good: 'md-chip--success', warning: 'md-chip--warning', critical: 'md-chip--error' })[statusLevel.value])

const calloutTone = computed(() => ({ good: 'md-callout--primary', warning: 'md-callout--warning', critical: 'md-callout--error' })[statusLevel.value])

const tagType = computed(() => {
  const p = quota.value.remaining_percent ?? 100
  if (p <= 10) return 'danger'
  if (p <= 30) return 'warning'
  return 'success'
})

function priorityTag(p: string) {
  if (p === 'high') return 'danger'
  if (p === 'medium') return 'warning'
  return 'info'
}

function priorityLabel(p: string) {
  if (p === 'high') return '高优'
  if (p === 'medium') return '中优'
  return '低优'
}

async function fetchData() {
  loading.value = true
  try {
    const [qRes, tRes] = await Promise.all([
      http.get('/quota').catch(() => ({})),
      http.get('/tasks?status=todo').catch(() => []),
    ])
    quota.value = qRes || {}
    todoTasks.value = (tRes as any[]) || []
    ElMessage.success('配额与待办池数据已刷新')
  } catch (err) {
    console.error('Failed to fetch quota view data:', err)
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(rows: any[]) {
  selectedTaskIds.value = rows.map((r) => r.id)
}

async function copySingle(task: any) {
  const text = `【任务】: ${task.name}\n【执行要求与 Prompt】:\n${task.description || '阅读项目代码实现此目标。'}`
  const ok = await copyText(text)
  if (ok) {
    ElMessage.success('工单 Prompt 已复制！')
  } else {
    ElMessage.info('未能自动写入剪贴板，请手动复制')
  }
}

async function generateAndCopyBatchPrompt() {
  const selected = todoTasks.value.filter((t) => selectedTaskIds.value.includes(t.id))
  if (selected.length === 0) return

  let p = `# 🌙 夜间无人值守自主开发任务包 (Night-Shift Autonomous Dispatch)\n`
  p += `你是自主开发 AI Agent。当前为夜间无人值守时段，请按照优先级依次自主推进以下 ${selected.length} 个任务：\n\n`

  selected.forEach((item, idx) => {
    p += `### 任务 ${idx + 1}: ${item.name} (${priorityLabel(item.priority)})\n`
    p += `【详细要求与执行指导】:\n${item.description || '阅读项目上下文实现该功能或修复。'}\n\n`
  })

  p += `--------------------------------------------------\n`
  p += `【自主开发执行准则】\n`
  p += `1. 逐个推进任务，每一项任务先分析受影响文件，制定变更计划；\n`
  p += `2. 代码实现完成后，务必执行单元测试或静态分析；\n`
  p += `3. 若发生报错，必须自主排查原因并修复，直至测试全通；\n`
  p += `4. 每完成一项任务，自动生成一条规范的 git commit 提交；\n`
  p += `5. 全部任务完成后，在控制台总结各项任务的执行结果。\n`

  generatedPrompt.value = p
  const ok = await copyText(p)
  if (ok) {
    ElMessage.success('📋 夜班批量 Prompt 已生成并复制到剪贴板！可直接粘贴至 dsh')
  } else {
    ElMessage.info('已生成 Prompt，由于浏览器安全限制未能自动写入剪贴板，请在下方弹窗手动复制')
  }
  batchModalOpen.value = true
}

async function reCopy() {
  const ok = await copyText(generatedPrompt.value)
  if (ok) {
    ElMessage.success('已重新复制到剪贴板')
  } else {
    ElMessage.info('请在上方文本框中全选手动复制')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md-space-5);
  margin-bottom: var(--md-space-7);
}

.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-3);
  margin-bottom: var(--md-space-4);
}

.head-title {
  font-size: var(--md-type-title-md);
  line-height: var(--md-type-title-lh-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}

.gauge-center {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--md-space-3);
  margin-bottom: var(--md-space-3);
}

.big-percent {
  font-size: var(--md-type-display-sm);
  line-height: var(--md-type-display-lh-sm);
  font-weight: var(--md-weight-bold);
  letter-spacing: var(--md-tracking-display);
}
.big-percent.good { color: var(--md-success); }
.big-percent.warning { color: var(--md-warning); }
.big-percent.critical { color: var(--md-error); }

.countdown-badge {
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
}

.progress-track {
  height: var(--md-progress-height);
  background: var(--md-surface-container-lowest);
  border-radius: var(--md-shape-full);
  overflow: hidden;
  margin-bottom: var(--md-space-5);
}

.progress-bar {
  height: 100%;
  transition: width var(--md-duration-medium-2) var(--md-ease-standard);
}
.progress-bar.good { background: var(--md-success); }
.progress-bar.warning { background: var(--md-warning); }
.progress-bar.critical { background: var(--md-error); }

/* 卡片内再分一小块：用低一级表面色，不套卡、不描边 */
.metric-footer-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--md-space-3);
  background: var(--md-surface-container);
  padding: var(--md-space-3) var(--md-space-4);
  border-radius: var(--md-shape-small);
}

.meta-col {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-1);
}

.meta-label {
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
}

.meta-val {
  font-size: var(--md-type-body-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}
.meta-val.highlight { color: var(--md-primary); }

.strategy-card {
  display: flex;
  flex-direction: column;
}

.strategy-content {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-4);
  flex: 1;
}

.sugg-box .sugg-icon {
  line-height: var(--md-type-body-lh-md);
}

/* 建议动作：列表行，分隔线分行，不用框 */
.action-suggestions h4 {
  font-size: var(--md-type-title-sm);
  line-height: var(--md-type-title-lh-sm);
  font-weight: var(--md-weight-medium);
  margin: 0 0 var(--md-space-2);
  color: var(--md-on-surface);
}

.suggestion-list {
  display: flex;
  flex-direction: column;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: var(--md-space-3);
  padding: var(--md-space-3) var(--md-space-2);
  border-radius: var(--md-shape-small);
  cursor: pointer;
  border-bottom: 1px solid var(--md-outline-variant);
}
.suggestion-item:last-child {
  border-bottom: 0;
}

.item-icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--md-shape-full);
  background-color: var(--md-primary-container);
  color: var(--md-on-primary-container);
  font-size: var(--md-type-label-md);
  font-weight: var(--md-weight-medium);
}
.item-info { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.item-title { font-size: var(--md-type-body-md); font-weight: var(--md-weight-medium); color: var(--md-on-surface); }
.item-sub { font-size: var(--md-type-body-sm); color: var(--md-on-surface-variant); }
.arrow { color: var(--md-primary); }

/* 夜间调度区：只靠间距与标题分组 */
.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--md-space-4);
}

.section-intro {
  display: flex;
  flex-direction: column;
  gap: var(--md-space-1);
  min-width: 0;
}

.sec-desc {
  font-size: var(--md-type-body-md);
  color: var(--md-on-surface-variant);
  margin: 0;
  max-width: 800px;
}

.batch-dialog-input :deep(textarea) {
  font-family: var(--md-font-mono);
  font-size: var(--md-type-body-sm);
}

@media (max-width: 900px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .section-head { flex-direction: column; }
  .metric-footer-grid { grid-template-columns: 1fr; }
}
</style>
