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
  background: var(--md-surface-container, #f1f2f4);
  border: 1px solid var(--md-outline-variant, #e0e2e8);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--md-on-surface, #1d1d1f);
  cursor: pointer;
  transition: all 0.2s ease;
}

.quota-badge-btn:hover {
  background: var(--md-surface-container-high, #eaecf0);
}

.quota-badge-btn.critical {
  border-color: #ff9999;
  background: rgba(255, 77, 79, 0.08);
}

.quota-badge-btn.warning {
  border-color: #ffd591;
  background: rgba(250, 173, 20, 0.08);
}

.quota-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.quota-pulse.good {
  background: #52c41a;
  box-shadow: 0 0 6px rgba(82, 196, 26, 0.6);
}

.quota-pulse.warning {
  background: #faad14;
  box-shadow: 0 0 6px rgba(250, 173, 20, 0.6);
}

.quota-pulse.critical {
  background: #ff4d4f;
  animation: pulse-crit 1.5s infinite;
}

@keyframes pulse-crit {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.quota-timer {
  font-weight: 600;
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
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
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.radar-progress-bar {
  height: 6px;
  background: var(--md-surface-container-highest, #e2e4e9);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.progress-fill.good { background: #52c41a; }
.progress-fill.warning { background: #faad14; }
.progress-fill.critical { background: #ff4d4f; }

.radar-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
  background: var(--md-surface-container-low, #f8f9fa);
  padding: 8px 10px;
  border-radius: 8px;
}

.meta-item {
  display: flex;
  flex-direction: column;
}

.meta-item .label {
  font-size: 11px;
  color: var(--md-on-surface-variant, #666);
}

.meta-item .val {
  font-size: 13px;
  font-weight: 600;
  color: var(--md-on-surface, #222);
}

.meta-item .val.highlight {
  color: #0066cc;
}

.radar-suggestion {
  background: #f0f7ff;
  border-left: 3px solid #0066cc;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12px;
  margin-bottom: 12px;
  line-height: 1.45;
}

.radar-suggestion.warning {
  background: #fffbe6;
  border-left-color: #faad14;
}

.sugg-header {
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--md-on-surface, #222);
}

.sugg-body {
  color: #444;
}

.radar-actions {
  text-align: right;
}

.action-btn {
  font-size: 12px;
  color: #0066cc;
  text-decoration: none;
  font-weight: 500;
}

.action-btn:hover {
  text-decoration: underline;
}
</style>
