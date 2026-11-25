<template>
  <div class="app-layout">
    <!-- 顶部应用栏：目的地标题 + 上下文状态。导航本身在侧栏 / 底栏 -->
    <header class="top-app-bar">
      <router-link to="/" class="brand" aria-label="HarnessPilot 首页">
        <span class="brand-icon">⚡</span>
        <span class="brand-title">HarnessPilot</span>
      </router-link>

      <h1 class="app-bar-title">{{ currentTitle }}</h1>

      <div class="app-bar-actions">
        <span class="harness-badge" title="DeepSeek Harness MCP 运行正常">
          <span class="pulse-dot"></span>
          dsh 已连接
        </span>
        <span class="tailnet-chip" title="Tailscale 内网免密访问">🔒 内网</span>

        <!-- 5h 算力：健康度用色调容器表达，不用描边 -->
        <button class="quota-chip" :class="`is-${quotaStatus}`" title="查看 5h 算力详情" @click="router.push('/quota')">
          <el-icon><Cpu /></el-icon>
          <span class="quota-chip__value">{{ quota.remaining_percent ?? 100 }}%</span>
          <span class="quota-chip__meta">{{ quota.minutes_left ?? 0 }} 分钟</span>
        </button>

        <NotificationBell />

        <button class="md-icon-btn" :title="theme.scheme === 'dark' ? '切换浅色' : '切换深色'" :aria-label="theme.scheme === 'dark' ? '切换浅色' : '切换深色'" @click="toggleTheme">
          <el-icon v-if="theme.scheme === 'dark'"><Sunny /></el-icon>
          <el-icon v-else><Moon /></el-icon>
        </button>
      </div>
    </header>

    <!-- 导航栏（宽屏）：四个顶层目的地，选中项背后是药丸形指示器 -->
    <nav class="rail" aria-label="主导航">
      <router-link
        v-for="d in destinations"
        :key="d.to"
        :to="d.to"
        class="rail-item md-state"
        :class="{ 'is-active': isActive(d) }"
        :aria-current="isActive(d) ? 'page' : undefined"
      >
        <span class="rail-item__indicator"><el-icon><component :is="d.icon" /></el-icon></span>
        <span class="rail-item__label">{{ d.label }}</span>
      </router-link>
    </nav>

    <main class="page-content">
      <router-view />
    </main>

    <!-- 导航栏（窄屏）：落到底部 -->
    <nav class="bottom-nav" aria-label="主导航">
      <router-link
        v-for="d in destinations"
        :key="d.to"
        :to="d.to"
        class="bottom-nav-item md-state"
        :class="{ 'is-active': isActive(d) }"
        :aria-current="isActive(d) ? 'page' : undefined"
      >
        <span class="bottom-nav-item__indicator"><el-icon><component :is="d.icon" /></el-icon></span>
        <span class="bottom-nav-item__label">{{ d.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Aim, Cpu, Folder, MagicStick, Moon, Sunny } from '@element-plus/icons-vue'
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

/** 四个顶层目的地。顺序在各断点下保持不变；窄屏落到底部导航栏。 */
const destinations = [
  { to: '/', label: '任务看板', icon: Aim, match: (p: string) => p === '/' },
  { to: '/ideas', label: '灵感推演', icon: MagicStick, match: (p: string) => p.startsWith('/ideas') },
  { to: '/quota', label: '算力调度', icon: Cpu, match: (p: string) => p.startsWith('/quota') },
  { to: '/projects', label: '项目管理', icon: Folder, match: (p: string) => p.startsWith('/projects') },
]
const isActive = (d: (typeof destinations)[number]) => d.match(route.path)
const currentTitle = computed(() => destinations.find((d) => isActive(d))?.label ?? 'HarnessPilot')

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
  display: grid;
  grid-template-columns: var(--rail-width) 1fr;
  grid-template-rows: auto 1fr;
  grid-template-areas:
    'bar bar'
    'rail content';
  background-color: var(--md-surface);
  --rail-width: 88px;
}

/* ---- 顶部应用栏：surface，无阴影无边框 ---- */
.top-app-bar {
  grid-area: bar;
  position: sticky;
  top: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: var(--md-space-4);
  height: var(--md-top-app-bar-height);
  padding: 0 var(--md-space-5);
  background-color: var(--md-surface);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-2);
  color: var(--md-on-surface);
  text-decoration: none;
}
.brand-icon {
  font-size: var(--md-type-title-lg);
  color: var(--md-primary);
}
.brand-title {
  font-size: var(--md-type-title-md);
  font-weight: var(--md-weight-medium);
  color: var(--md-on-surface);
}

.app-bar-title {
  margin-left: var(--md-space-2);
  font-size: var(--md-type-title-lg);
  line-height: var(--md-type-title-lh-lg);
  font-weight: var(--md-weight-regular);
  color: var(--md-on-surface);
}

.app-bar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
}

.harness-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  height: 24px;
  padding: 0 var(--md-space-2);
  border-radius: var(--md-shape-small);
  background-color: var(--md-success-container);
  color: var(--md-on-success-container);
  font-size: var(--md-type-label-md);
  font-weight: var(--md-weight-medium);
}
.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--md-shape-full);
  background-color: var(--md-success);
  box-shadow: var(--md-glow-success);
}

.tailnet-chip {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 var(--md-space-2);
  border-radius: var(--md-shape-small);
  background-color: var(--md-surface-container-high);
  color: var(--md-on-surface-variant);
  font-size: var(--md-type-label-md);
}

.quota-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  height: var(--md-chip-height);
  padding: 0 var(--md-space-3);
  border: 0;
  border-radius: var(--md-shape-small);
  font: inherit;
  font-size: var(--md-type-label-lg);
  cursor: pointer;
  background-color: var(--md-surface-container-high);
  color: var(--md-on-surface-variant);
}
.quota-chip.is-good { background-color: var(--md-success-container); color: var(--md-on-success-container); }
.quota-chip.is-warning { background-color: var(--md-warning-container); color: var(--md-on-warning-container); }
.quota-chip.is-critical { background-color: var(--md-error); color: var(--md-on-error); }
.quota-chip__value { font-weight: var(--md-weight-medium); }
.quota-chip__meta { font-size: var(--md-type-label-md); opacity: 0.85; }

/* ---- 导航栏（rail）：surface-container，选中项 = secondary-container 药丸 ---- */
.rail {
  grid-area: rail;
  position: sticky;
  top: var(--md-top-app-bar-height);
  align-self: start;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--md-space-1);
  padding: var(--md-space-3) 0;
  background-color: var(--md-surface-container);
  border-radius: 0 var(--md-shape-large) var(--md-shape-large) 0;
  min-height: calc(100vh - var(--md-top-app-bar-height));
}
.rail-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 80px;
  padding: var(--md-space-1) 0;
  text-decoration: none;
  color: var(--md-on-surface-variant);
  border-radius: var(--md-shape-large);
  font-size: var(--md-type-label-md);
  font-weight: var(--md-weight-medium);
}
.rail-item__indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: var(--md-chip-height);
  border-radius: var(--md-shape-full);
  font-size: var(--md-type-title-lg);
  transition: background-color var(--md-duration-short-2) var(--md-ease-standard);
}
.rail-item:hover .rail-item__indicator {
  background-color: color-mix(in srgb, var(--md-on-surface) 8%, transparent);
}
.rail-item.is-active { color: var(--md-on-surface); }
.rail-item.is-active .rail-item__indicator {
  background-color: var(--md-secondary-container);
  color: var(--md-on-secondary-container);
}
.rail-item__label {
  padding: 0 var(--md-space-1);
  line-height: var(--md-type-label-lh-md);
}

.page-content {
  grid-area: content;
  min-width: 0;
  padding: var(--md-space-3) var(--md-space-5) var(--md-space-7);
}

/* ---- 底部导航栏：窄屏才出现 ---- */
.bottom-nav { display: none; }

/* 中等宽度：rail 收窄为纯图标 */
@media (max-width: 1100px) {
  .app-layout { --rail-width: 72px; }
  .rail-item { width: 64px; }
}

/* 紧凑宽度：导航落到底部，顶栏简化 */
@media (max-width: 839px) {
  .app-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
    grid-template-areas:
      'bar'
      'content'
      'bottom';
  }
  .rail { display: none; }
  .brand-title,
  .harness-badge,
  .tailnet-chip,
  .quota-chip__meta { display: none; }
  .app-bar-title { margin-left: 0; }
  .page-content { padding: 0 var(--md-space-4) var(--md-space-7); }

  .bottom-nav {
    grid-area: bottom;
    position: sticky;
    bottom: 0;
    z-index: 1000;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    padding: var(--md-space-2) var(--md-space-1) var(--md-space-2);
    background-color: var(--md-surface-container);
  }
  .bottom-nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: var(--md-space-1) 0;
    text-decoration: none;
    color: var(--md-on-surface-variant);
    font-size: var(--md-type-label-md);
    font-weight: var(--md-weight-medium);
  }
  .bottom-nav-item__indicator {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: var(--md-chip-height);
    border-radius: var(--md-shape-full);
    font-size: var(--md-type-title-lg);
  }
  .bottom-nav-item.is-active { color: var(--md-on-surface); }
  .bottom-nav-item.is-active .bottom-nav-item__indicator {
    background-color: var(--md-secondary-container);
    color: var(--md-on-secondary-container);
  }
}
</style>
