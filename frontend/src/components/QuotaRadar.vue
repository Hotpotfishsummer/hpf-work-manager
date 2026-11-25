<template>
  <div class="quota-radar">
    <el-popover placement="bottom-end" :width="320" trigger="click" popper-class="quota-popover">
      <template #reference>
        <button class="quota-badge-btn md-state" :class="statusLevel" title="查看 5h 算力配额与调度雷达">
          <span class="quota-pulse" :class="statusLevel"></span>
          <span class="quota-icon">⚡</span>
          <span class="quota-text">5h额度: <strong>{{ quota.remaining_percent }}%</strong></span>
          <span class="quota-timer" v-if="quota.minutes_left !== undefined">⏳ {{ quota.minutes_left }}m</span>
        </button>
      </template>

      <div class="radar-card">
        <div class="radar-header">
          <div class="radar-title">
            <span>⚡ AI 算力窗口雷达</span>
            <el-tag :type="tagType" size="small">{{ quota.remaining_percent }}% 剩余</el-tag>
          </div>
          <el-button text size="small" :loading="loading" @click="fetchQuota">刷新</el-button>
        </div>

        <div class="radar-progress-bar">
          <div class="progress-fill" :class="statusLevel" :style="{ width: quota.remaining_percent + '%' }"></div>
        </div>

        <div class="radar-meta-grid">
          <div class="meta-item">
            <span class="label">下次 5h 刷新</span>
            <span class="val highlight">{{ quota.reset_time_str || '--:--' }}</span>
          </div>
          <div class="meta-item">
            <span class="label">倒计时</span>
            <span class="val">{{ quota.minutes_left || 0 }} 分钟</span>
          </div>
          <div class="meta-item">
            <span class="label">本周剩余配额</span>
            <span class="val">{{ quota.weekly_remaining_percent || 0 }}%</span>
          </div>
          <div class="meta-item">
            <span class="label">夜间闲时时段</span>
            <span class="val">{{ quota.is_night_shift ? '🌙 是 (23-07)' : '☀️ 否' }}</span>
          </div>
        </div>

        <div class="md-callout radar-suggestion" :class="{ good: 'md-callout--primary', warning: 'md-callout--warning', critical: 'md-callout--error' }[statusLevel]">
          <div class="sugg-header">💡 调度与额度利用策略</div>
          <div class="sugg-body">{{ quota.suggestion || '正在获取调度推演建议...' }}</div>
        </div>

        <div class="radar-actions">
          <router-link to="/ideas" class="md-btn md-btn--text md-state action-btn">
            前往灵感工坊备单 →
          </router-link>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import http from '@/api/http'

interface QuotaData {
  ok: boolean
  remaining_percent: number
  weekly_remaining_percent: number
  minutes_left: number
  reset_time_str: string
  is_night_shift: boolean
  suggestion: string
}

const quota = ref<QuotaData>({
  ok: true,
  remaining_percent: 100,
  weekly_remaining_percent: 100,
  minutes_left: 0,
  reset_time_str: '--:--:--',
  is_night_shift: false,
  suggestion: '正在连接额度探针...',
})

const loading = ref(false)
let timer: number | null = null

const statusLevel = computed(() => {
  const p = quota.value.remaining_percent
  if (p <= 10) return 'critical'
  if (p <= 30) return 'warning'
  return 'good'
})

const tagType = computed(() => {
  const p = quota.value.remaining_percent
  if (p <= 10) return 'danger'
  if (p <= 30) return 'warning'
  return 'success'
})

async function fetchQuota() {
  loading.value = true
  try {
    const res: any = await http.get('/quota')
    if (res) {
      quota.value = res
    }
  } catch (err) {
    console.error('Failed to fetch quota:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchQuota()
  // 30秒轮询一次额度变化
  timer = window.setInterval(fetchQuota, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.quota-radar {
  display: inline-flex;
  align-items: center;
}

/* 顶栏里的状态徽标：色块不描边，按健康度换容器色 */
.quota-badge-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: var(--md-shape-full);
  padding: var(--md-space-1) var(--md-space-3);
  font: inherit;
  font-size: var(--md-type-label-md);
  color: var(--md-on-surface);
  cursor: pointer;
  background-color: var(--md-surface-container-high);
  --state-color: var(--md-on-surface);
  transition: background-color var(--md-duration-short-2) var(--md-ease-standard);
}
.quota-badge-btn.good {
  background-color: var(--md-success-container);
  color: var(--md-on-success-container);
  --state-color: var(--md-on-success-container);
}
.quota-badge-btn.warning {
  background-color: var(--md-warning-container);
  color: var(--md-on-warning-container);
  --state-color: var(--md-on-warning-container);
}
.quota-badge-btn.critical {
  background-color: var(--md-error-container);
  color: var(--md-on-error-container);
  --state-color: var(--md-on-error-container);
}

.quota-pulse {
  width: 8px;
  height: 8px;
  border-radius: var(--md-shape-full);
  background-color: currentColor;
}

.quota-pulse.critical {
  animation: pulse-crit 1.5s infinite;
}

@keyframes pulse-crit {
  0% { transform: scale(0.85); opacity: 0.7; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.85); opacity: 0.7; }
}

.quota-timer {
  font-weight: var(--md-weight-medium);
}

/* 浮层底色（surface-container-high）与 --md-elevation-2 由 element-plus.css 的 .el-popper 统一给 */
.radar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--md-space-2);
  margin-bottom: var(--md-space-2);
}

.radar-title {
  font-weight: var(--md-weight-medium);
  font-size: var(--md-type-title-sm);
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
}

.radar-progress-bar {
  height: 6px;
  background-color: var(--md-surface-container-lowest);
  border-radius: var(--md-shape-full);
  overflow: hidden;
  margin-bottom: var(--md-space-3);
}

.progress-fill {
  height: 100%;
  transition: width var(--md-duration-medium-2) var(--md-ease-standard);
}

.progress-fill.good { background: var(--md-success); }
.progress-fill.warning { background: var(--md-warning); }
.progress-fill.critical { background: var(--md-error); }

.radar-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--md-space-2) var(--md-space-3);
  margin-bottom: var(--md-space-3);
}

.meta-item {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--md-space-1);
  border-bottom: 1px solid var(--md-outline-variant);
}

.meta-item .label {
  font-size: var(--md-type-body-sm);
  color: var(--md-on-surface-variant);
}

.meta-item .val {
  font-size: var(--md-type-body-sm);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}

.meta-item .val.highlight {
  color: var(--md-primary);
}

.radar-suggestion {
  display: block;
  font-size: var(--md-type-body-sm);
  line-height: var(--md-type-body-lh-sm);
  margin-bottom: var(--md-space-3);
  border-radius: var(--md-shape-small);
}

.sugg-header {
  font-weight: var(--md-weight-medium);
  margin-bottom: var(--md-space-1);
}

.sugg-body {
  opacity: 0.9;
}

.radar-actions {
  display: flex;
  justify-content: flex-end;
}

.action-btn {
  height: var(--md-control-height-sm);
  font-size: var(--md-type-label-md);
}
</style>
