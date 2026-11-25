<template>
  <div class="quota-view-container" v-loading="loading">
    <div class="view-header">
      <div>
        <h1 class="view-title">⚡ 5h 算力配额与自主调度雷达 (Quota Radar)</h1>
        <p class="view-sub">监控 MiniMax / DeepSeek 5小时滚动算力窗口与每周余量，规划夜间无人值守开发批次，告别“有额度无目标，有目标无额度”。</p>
      </div>
      <el-button type="primary" plain @click="fetchData">
        <el-icon><Refresh /></el-icon> 刷新配额探针
      </el-button>
    </div>

    <!-- 算力大盘仪表卡片 -->
    <div class="dashboard-grid">
      <!-- 5小时当前窗口 -->
      <div class="metric-card main-gauge">
        <div class="metric-head">
          <span class="head-title">5小时滚动算力余量</span>
          <el-tag :type="tagType" size="small" effect="dark">{{ quota.remaining_percent ?? 100 }}% 剩余</el-tag>
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
      <div class="metric-card strategy-card">
        <div class="metric-head">
          <span class="head-title">💡 当前时段调度推演建议</span>
          <span class="strategy-badge" :class="statusLevel">
            {{ quota.remaining_percent >= 50 ? '算力充沛' : (quota.remaining_percent >= 20 ? '算力平稳' : '算力见底') }}
          </span>
        </div>

        <div class="strategy-content">
          <div class="sugg-box" :class="{ warning: (quota.remaining_percent ?? 100) < 30 }">
            <div class="sugg-icon">⚡</div>
            <div class="sugg-text">
              <strong>策略提示：</strong>
              {{ quota.suggestion || '正在由配额探针与时间模型计算最优执行建议...' }}
            </div>
          </div>

          <div class="action-suggestions">
            <h4>💡 建议的下一步动作：</h4>
            <div class="suggestion-item" @click="router.push('/ideas')">
              <span class="item-icon">🔍</span>
              <div class="item-info">
                <span class="item-title">进行项目代码体检与 Next Steps 推演</span>
                <span class="item-sub">由 AI 深度扫描代码库与 TODOs，提炼 3 个高价值工单</span>
              </div>
              <span class="arrow">→</span>
            </div>

            <div class="suggestion-item" @click="router.push('/')">
              <span class="item-icon">🎯</span>
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

    <!-- 夜间无人值守任务调度包 (Night-Shift Autonomous Dispatcher) -->
    <div class="nightshift-section">
      <div class="section-head">
        <div>
          <h2 class="sec-title">🌙 夜间无人值守批次备单箱 (Night-Shift Dispatcher)</h2>
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
              <el-button size="small" link type="primary" @click="copySingle(row)">复制单项</el-button>
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
.quota-view-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.view-title {
  font-size: var(--md-text-title-lg);
  font-weight: var(--md-weight-semibold);
  margin: 0 0 6px 0;
  color: var(--md-on-surface);
}

.view-sub {
  margin: 0;
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 28px;
}

.metric-card {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: 20px;
  box-shadow: var(--md-shadow-1);
}

.metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.head-title {
  font-size: var(--md-text-body-lg);
  font-weight: 600;
  color: var(--md-on-surface);
}

.gauge-center {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.big-percent {
  font-size: var(--md-text-display-xl);
  font-weight: var(--md-weight-bold);
  line-height: 1;
}
.big-percent.good { color: var(--md-success); }
.big-percent.warning { color: var(--md-warning); }
.big-percent.critical { color: var(--md-error); }

.countdown-badge {
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  background: var(--md-surface-container);
  padding: 6px 12px;
  border-radius: var(--md-radius-lg);
}

.progress-track {
  height: 8px;
  background: var(--md-surface-container-highest);
  border-radius: var(--md-radius-xs);
  overflow: hidden;
  margin-bottom: 20px;
}

.progress-bar {
  height: 100%;
  transition: width 0.3s ease;
}
.progress-bar.good { background: var(--md-success); }
.progress-bar.warning { background: var(--md-warning-fill); }
.progress-bar.critical { background: var(--md-error); }

.metric-footer-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  background: var(--md-surface-container-low);
  padding: 12px 14px;
  border-radius: var(--md-radius-sm);
}

.meta-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant);
}

.meta-val {
  font-size: var(--md-text-label-md);
  font-weight: 600;
  color: var(--md-on-surface);
}
.meta-val.highlight { color: var(--md-primary); }

/* 策略卡片 */
.strategy-badge {
  font-size: var(--md-text-caption);
  padding: 2px 8px;
  border-radius: var(--md-radius-xs);
  font-weight: 600;
}
.strategy-badge.good { background: var(--md-success-tint); color: var(--md-success); }
.strategy-badge.warning { background: var(--md-warning-tint); color: var(--md-warning); }
.strategy-badge.critical { background: var(--md-error-tint); color: var(--md-error); }

.sugg-box {
  display: flex;
  gap: 10px;
  background: var(--md-primary-container);
  border-left: var(--md-accent-bar-width) solid var(--md-primary);
  padding: 12px 14px;
  border-radius: var(--md-radius-sm);
  margin-bottom: 16px;
  font-size: var(--md-text-label-md);
  line-height: 1.5;
  color: var(--md-on-primary-container);
}
.sugg-box.warning {
  background: var(--md-warning-container);
  border-left-color: var(--md-warning);
  color: var(--md-on-warning-container);
}

.action-suggestions h4 {
  font-size: var(--md-text-label-md);
  margin: 0 0 10px 0;
  color: var(--md-on-surface);
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.suggestion-item:hover {
  border-color: var(--md-primary);
  background: var(--md-surface-container-high);
}

.item-icon { font-size: var(--md-text-body-lg); }
.item-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.item-title { font-size: var(--md-text-label-md); font-weight: 600; color: var(--md-on-surface); }
.item-sub { font-size: var(--md-text-caption); color: var(--md-on-surface-variant); }
.arrow { color: var(--md-outline); font-weight: var(--md-weight-semibold); }

/* 夜间调度区 */
.nightshift-section {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-md);
  padding: 22px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.sec-title {
  font-size: var(--md-text-title-md);
  font-weight: var(--md-weight-semibold);
  margin: 0 0 6px 0;
  color: var(--md-on-surface);
}

.sec-desc {
  font-size: var(--md-text-label-md);
  color: var(--md-on-surface-variant);
  margin: 0;
  max-width: 800px;
  line-height: 1.5;
}

.batch-table-container {
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-sm);
  overflow: hidden;
}

.batch-dialog-input textarea {
  font-family: var(--md-font-mono);
  font-size: var(--md-text-body-sm);
  line-height: 1.5;
}

@media (max-width: 900px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .section-head { flex-direction: column; gap: 12px; }
}
</style>
