<template>
  <div class="app-layout">
    <!-- top-nav：Apple 风格半透明毛玻璃吸顶导航 -->
    <header class="top-nav">
      <div class="page-container nav-inner">
        <router-link to="/projects" class="brand">
          <svg class="brand-mark" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
            <circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="1.6" />
            <path d="M12 3.5c2.4 2.2 3.6 5.2 3.6 8.5s-1.2 6.3-3.6 8.5c-2.4-2.2-3.6-5.2-3.6-8.5S9.6 5.7 12 3.5Z" fill="currentColor" />
            <path d="M3.5 12h17" stroke="currentColor" stroke-width="1.4" />
          </svg>
          <span class="brand-name">HPF WORK MANAGER</span>
        </router-link>

        <nav class="nav-menu">
          <router-link to="/projects" class="nav-item">项目</router-link>
          <router-link to="/dashboard" class="nav-item">进度</router-link>
          <router-link to="/keys" class="nav-item">API Keys</router-link>
        </nav>

        <div class="nav-actions">
          <button class="theme-toggle" :title="theme.scheme === 'dark' ? '切换到浅色' : '切换到深色'" @click="toggleTheme">
            <el-icon v-if="theme.scheme === 'dark'"><Sunny /></el-icon>
            <el-icon v-else><Moon /></el-icon>
          </button>

          <el-dropdown trigger="click" @command="onUserCommand">
            <span class="nav-item user-chip">
              <el-icon><User /></el-icon>
              <span class="user-name">{{ authStore.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <main class="page-body">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { Moon, Sunny, User } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const authStore = useAuthStore()
const theme = useThemeStore()

function toggleTheme() {
  theme.setMode(theme.scheme === 'dark' ? 'light' : 'dark')
}

function onUserCommand(cmd: string) {
  if (cmd === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-layout {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--md-surface);
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--md-nav-height);
  background-color: color-mix(in srgb, var(--md-surface) 82%, transparent);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--md-outline-variant);
}

.nav-inner {
  height: 100%;
  display: flex;
  align-items: center;
  gap: var(--md-space-6);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--md-space-1);
  color: var(--md-on-surface);
}
.brand:hover { color: var(--md-primary); }
.brand-mark { color: var(--md-primary); }
.brand-name {
  font-size: var(--md-text-label-lg);
  font-weight: var(--md-weight-bold);
  letter-spacing: 0.3px;
}

.nav-menu {
  display: flex;
  gap: var(--md-space-5);
  margin-left: var(--md-space-5);
}
.nav-item {
  font-size: var(--md-text-label-lg);
  font-weight: 400;
  letter-spacing: 0.3px;
  color: var(--md-on-surface);
  padding: var(--md-space-1) 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.15s ease, color 0.15s ease;
}
.nav-item.router-link-active {
  color: var(--md-on-surface);
  border-bottom-color: var(--md-primary);
}
.nav-item:hover { color: var(--md-primary); }

.nav-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
}
.theme-toggle {
  width: var(--md-control-height);
  height: var(--md-control-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-full);
  background-color: transparent;
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.theme-toggle:hover {
  background-color: var(--md-surface-container-high);
  color: var(--md-on-surface);
  border-color: var(--md-outline);
}
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--md-space-1);
  cursor: pointer;
}
.user-name { font-weight: var(--md-weight-medium); }

.page-body {
  flex: 1;
  padding-bottom: var(--md-space-7);
}
</style>
