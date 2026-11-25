<template>
  <div class="quota-radar">
    <el-popover placement="bottom-end" :width="320" trigger="click" popper-class="quota-popover">
      <template #reference>
        <button class="quota-badge-btn" :class="statusLevel" title="查看 5h 算力配额与调度雷达">
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
            <el-tag :type="tagType" size="small" effect="dark">{{ quota.remaining_percent }}% 剩余</el-tag>
          </div>
          <el-button link size="small" :loading="loading" @click="fetchQuota">刷新</el-button>
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

        <div class="radar-suggestion" :class="{ warning: quota.remaining_percent < 20 }">
          <div class="sugg-header">💡 调度与额度利用策略</div>
          <div class="sugg-body">{{ quota.suggestion || '正在获取调度推演建议...' }}</div>
        </div>

        <div class="radar-actions">
          <router-link to="/ideas" class="action-btn">
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

.quota-badge-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-pill);
  padding: 4px 10px;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface);
  cursor: pointer;
  transition: all 0.2s ease;
}

.quota-badge-btn:hover {
  background: var(--md-surface-container-high);
}

.quota-badge-btn.critical {
  border-color: color-mix(in srgb, var(--md-error) 55%, transparent);
  background: var(--md-error-tint);
}

.quota-badge-btn.warning {
  border-color: color-mix(in srgb, var(--md-warning) 55%, transparent);
  background: var(--md-warning-tint);
}

.quota-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.quota-pulse.good {
  background: var(--md-success);
  box-shadow: var(--md-glow-success);
}

.quota-pulse.warning {
  background: var(--md-warning-fill);
  box-shadow: var(--md-glow-warning);
}

.quota-pulse.critical {
  background: var(--md-error);
  animation: pulse-crit 1.5s infinite;
}

@keyframes pulse-crit {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.quota-timer {
  font-weight: 600;
  color: var(--md-error);
  background: var(--md-error-tint);
  padding: 1px 6px;
  border-radius: var(--md-radius-xs);
}

.radar-card {
  padding: 4px;
}

.radar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.radar-title {
  font-weight: 600;
  font-size: var(--md-text-body);
  display: flex;
  align-items: center;
  gap: 6px;
}

.radar-progress-bar {
  height: 6px;
  background: var(--md-surface-container-highest);
  border-radius: var(--md-radius-xs);
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.progress-fill.good { background: var(--md-success); }
.progress-fill.warning { background: var(--md-warning-fill); }
.progress-fill.critical { background: var(--md-error); }

.radar-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
  background: var(--md-surface-container-low);
  padding: 8px 10px;
  border-radius: var(--md-radius-sm);
}

.meta-item {
  display: flex;
  flex-direction: column;
}

.meta-item .label {
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant);
}

.meta-item .val {
  font-size: var(--md-text-label-md);
  font-weight: 600;
  color: var(--md-on-surface);
}

.meta-item .val.highlight {
  color: var(--md-primary);
}

.radar-suggestion {
  background: var(--md-primary-container);
  border-left: var(--md-accent-bar-width) solid var(--md-primary);
  padding: 8px 10px;
  border-radius: var(--md-radius-xs);
  font-size: var(--md-text-body-sm);
  margin-bottom: 12px;
  line-height: 1.45;
}

.radar-suggestion.warning {
  background: var(--md-warning-container);
  border-left-color: var(--md-warning);
}

.sugg-header {
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--md-on-surface);
}

.sugg-body {
  color: var(--md-on-surface-variant);
}

.radar-actions {
  text-align: right;
}

.action-btn {
  font-size: var(--md-text-body-sm);
  color: var(--md-primary);
  text-decoration: none;
  font-weight: 500;
}

.action-btn:hover {
  text-decoration: underline;
}
</style>
