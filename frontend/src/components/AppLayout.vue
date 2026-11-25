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
  border-bottom: 1px solid var(--md-outline-variant, #e2e4e8);
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
  font-size: 18px;
  color: var(--md-primary, #0066cc);
}

.brand-title {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: var(--md-on-surface);
}

.harness-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.3);
  border-radius: 999px;
  font-weight: 500;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: #52c41a;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(82, 196, 26, 0.8);
}

/* Tabs */
.nav-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--md-surface-container, #f1f2f4);
  padding: 3px;
  border-radius: 8px;
}

.tab-item {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--md-on-surface-variant, #666);
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.tab-item:hover {
  color: var(--md-on-surface, #111);
}

.tab-item.is-active {
  background: var(--md-surface, #ffffff);
  color: var(--md-primary, #0066cc);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
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
  background: var(--md-surface-container, #f1f2f4);
  border: 1px solid var(--md-outline-variant, #e0e2e8);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 12px;
  color: var(--md-on-surface, #222);
  cursor: pointer;
  transition: all 0.2s ease;
}

.mini-quota-capsule:hover {
  background: var(--md-surface-container-high, #e4e6ea);
  border-color: #0066cc;
}

.mini-quota-capsule.critical {
  background: rgba(255, 77, 79, 0.1);
  border-color: #ff9999;
}

.capsule-icon { color: #fa8c16; font-size: 12px; }
.capsule-text { font-weight: 700; }
.capsule-timer {
  font-size: 11px;
  color: var(--md-on-surface-variant, #666);
  background: var(--md-surface, #ffffff);
  padding: 1px 5px;
  border-radius: 4px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--md-outline-variant, #e0e2e8);
  border-radius: 50%;
  background: transparent;
  color: var(--md-on-surface-variant, #555);
  cursor: pointer;
  transition: all 0.15s ease;
}

.icon-btn:hover {
  background: var(--md-surface-container, #f1f2f4);
  color: var(--md-on-surface, #111);
}

.tailnet-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--md-on-surface-variant, #777);
  background: var(--md-surface-container-low, #f8f9fa);
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--md-outline-variant, #eaecef);
}

.lock-icon { font-size: 11px; }

.page-content {
  flex: 1;
}

@media (max-width: 900px) {
  .brand-title, .harness-badge, .tailnet-chip { display: none; }
  .nav-tabs { gap: 2px; }
  .tab-item { padding: 4px 8px; font-size: 12px; }
}
</style>
