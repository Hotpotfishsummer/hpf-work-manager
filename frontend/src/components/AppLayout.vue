<template>
  <div class="app-layout">
    <!-- 极简毛玻璃顶栏 (Linear / Vercel 现代工作台风格) -->
    <header class="top-nav">
      <div class="nav-inner">
        <!-- 左侧 Brand 与 Harness 状态 -->
        <router-link to="/" class="brand">
          <span class="brand-icon">⚡</span>
          <span class="brand-title">HARNESS PILOT</span>
          <span class="harness-badge" title="DeepSeek Harness MCP 运行正常">
            <span class="pulse-dot"></span>
            dsh Linked
          </span>
        </router-link>

        <!-- 中间核心导航 Tabs -->
        <nav class="nav-tabs">
          <router-link to="/" class="tab-item" :class="{ 'is-active': isCockpitRoute }">
            🎯 任务看板
          </router-link>
          <router-link to="/ideas" class="tab-item" active-class="is-active">
            💡 灵感推演
          </router-link>
          <router-link to="/quota" class="tab-item" active-class="is-active">
            ⚡ 算力调度
          </router-link>
          <router-link to="/projects" class="tab-item" :class="{ 'is-active': isProjectsRoute }">
            📁 项目管理
          </router-link>
        </nav>

        <!-- 右侧状态胶囊与工具栏 -->
        <div class="nav-right">
          <!-- 迷你 5h 配额胶囊 -->
          <button class="mini-quota-capsule" :class="quotaStatus" title="点击查看 5h 算力详情" @click="router.push('/quota')">
            <span class="capsule-icon">⚡</span>
            <span class="capsule-text">{{ quota.remaining_percent ?? 100 }}%</span>
            <span class="capsule-timer">{{ quota.minutes_left ?? 0 }}m</span>
          </button>

          <!-- 简洁通知中心 -->
          <NotificationBell />

          <!-- 主题切换 -->
          <button class="icon-btn" :title="theme.scheme === 'dark' ? '切换浅色' : '切换深色'" @click="toggleTheme">
            <el-icon v-if="theme.scheme === 'dark'"><Sunny /></el-icon>
            <el-icon v-else><Moon /></el-icon>
          </button>

          <!-- Tailnet 状态标记 -->
          <div class="tailnet-chip" title="Tailscale 内网免密安全访问">
            <span class="lock-icon">🔒</span>
            <span>100.69.225.112</span>
          </div>
        </div>
      </div>
    </header>

    <main class="page-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Moon, Sunny } from '@element-plus/icons-vue'
import NotificationBell from '@/components/NotificationBell.vue'
import { useNotifications } from '@/stores/notifications'
import { useThemeStore } from '@/stores/theme'
import http from '@/api/http'

const route = useRoute()
const router = useRouter()
const theme = useThemeStore()
const { connect: connectNotifications, disconnect: disconnectNotifications } = useNotifications()

const quota = ref<any>({})
let quotaTimer: number | null = null

const isCockpitRoute = computed(() => route.path === '/')
const isProjectsRoute = computed(() => route.path.startsWith('/projects'))

const quotaStatus = computed(() => {
  const p = quota.value.remaining_percent ?? 100
  if (p <= 10) return 'critical'
  if (p <= 30) return 'warning'
  return 'good'
})

async function fetchMiniQuota() {
  try {
    const res: any = await http.get('/quota')
    if (res) quota.value = res
  } catch {}
}

onMounted(() => {
  connectNotifications()
  fetchMiniQuota()
  quotaTimer = window.setInterval(fetchMiniQuota, 45000)
})

onUnmounted(() => {
  disconnectNotifications()
  if (quotaTimer) clearInterval(quotaTimer)
})

function toggleTheme() {
  theme.setMode(theme.scheme === 'dark' ? 'light' : 'dark')
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--md-surface);
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  height: 52px;
  background-color: color-mix(in srgb, var(--md-surface) 86%, transparent);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--md-outline-variant);
}

.nav-inner {
  max-width: 1400px;
  height: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Brand */
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--md-on-surface);
}

.brand-icon {
  font-size: var(--md-text-title-lg);
  color: var(--md-primary);
}

.brand-title {
  font-size: var(--md-text-body-lg);
  font-weight: var(--md-weight-bold);
  letter-spacing: 0.5px;
  color: var(--md-on-surface);
}

.harness-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--md-text-caption);
  padding: 2px 8px;
  background: var(--md-success-tint);
  color: var(--md-on-success-container);
  border: 1px solid color-mix(in srgb, var(--md-success) 30%, transparent);
  border-radius: var(--md-radius-pill);
  font-weight: var(--md-weight-medium);
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: var(--md-success);
  border-radius: 50%;
  box-shadow: var(--md-glow-success);
}

/* Tabs */
.nav-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--md-surface-container);
  padding: 3px;
  border-radius: var(--md-radius-sm);
}

.tab-item {
  padding: 6px 14px;
  font-size: var(--md-text-label-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface-variant);
  text-decoration: none;
  border-radius: var(--md-radius-sm);
  transition: all 0.15s ease;
}

.tab-item:hover {
  color: var(--md-on-surface);
}

.tab-item.is-active {
  background: var(--md-surface);
  color: var(--md-primary);
  font-weight: var(--md-weight-semibold);
  box-shadow: var(--md-shadow-1);
}

/* Right Tools */
.nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mini-quota-capsule {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-pill);
  padding: 3px 10px;
  font-size: var(--md-text-body-sm);
  color: var(--md-on-surface);
  cursor: pointer;
  transition: all 0.2s ease;
}

.mini-quota-capsule:hover {
  background: var(--md-surface-container-high);
  border-color: var(--md-primary);
}

.mini-quota-capsule.critical {
  background: var(--md-error-tint);
  border-color: color-mix(in srgb, var(--md-error) 50%, transparent);
}

.capsule-icon { color: var(--md-warning); font-size: var(--md-text-body-sm); }
.capsule-text { font-weight: var(--md-weight-bold); }
.capsule-timer {
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant);
  background: var(--md-surface);
  padding: 1px 5px;
  border-radius: var(--md-radius-xs);
}

.icon-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--md-outline-variant);
  border-radius: 50%;
  background: transparent;
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-btn:hover {
  background: var(--md-surface-container);
  color: var(--md-on-surface);
}

.tailnet-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--md-text-caption);
  color: var(--md-on-surface-variant);
  background: var(--md-surface-container-low);
  padding: 3px 8px;
  border-radius: var(--md-radius-sm);
  border: 1px solid var(--md-outline-variant);
}

.lock-icon { font-size: var(--md-text-caption); }

.page-content {
  flex: 1;
}

@media (max-width: 900px) {
  .brand-title, .harness-badge, .tailnet-chip { display: none; }
  .nav-tabs { gap: 2px; }
  .tab-item { padding: 4px 8px; font-size: var(--md-text-body-sm); }
}
</style>
