<template>
  <div class="app-layout">
    <!-- top-nav：白底 64px 吸顶，nav-link 14px/400 -->
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
          <router-link to="/projects" class="nav-item">进度</router-link>
        </nav>

        <div class="nav-actions">
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
import { User } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

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
  background-color: var(--bmw-canvas);
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--bmw-nav-height);
  background-color: var(--bmw-canvas);
  border-bottom: 1px solid var(--bmw-hairline);
}

.nav-inner {
  height: 100%;
  display: flex;
  align-items: center;
  gap: var(--bmw-space-xl);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--bmw-space-xs);
  color: var(--bmw-ink);
}
.brand:hover { color: var(--bmw-primary); }
.brand-mark { color: var(--bmw-primary); }
.brand-name {
  font-size: var(--bmw-text-nav);
  font-weight: var(--bmw-weight-display);
  letter-spacing: 0.3px;
}

.nav-menu {
  display: flex;
  gap: var(--bmw-space-lg);
  margin-left: var(--bmw-space-lg);
}
.nav-item {
  font-size: var(--bmw-text-nav);
  font-weight: 400;
  letter-spacing: 0.3px;
  color: var(--bmw-ink);
  padding: var(--bmw-space-xs) 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.15s ease;
}
.nav-item.router-link-active {
  color: var(--bmw-ink);
  border-bottom-color: var(--bmw-primary);
}
.nav-item:hover { color: var(--bmw-primary); }

.nav-actions {
  margin-left: auto;
}
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--bmw-space-xs);
  cursor: pointer;
  outline: none;
}
.user-name { font-weight: 700; }

.page-body {
  flex: 1;
  padding-bottom: var(--bmw-space-xxl);
}
</style>
