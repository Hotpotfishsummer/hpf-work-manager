<template>
  <div class="not-found">
    <div class="nf-code">404</div>
    <h1 class="nf-title">页面未找到</h1>
    <p class="nf-sub">你访问的页面不存在或已被移动</p>
    <el-button type="primary" size="large" @click="router.push('/projects')">返回项目列表</el-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--md-space-3);
  text-align: center;
  padding: var(--md-space-7) var(--md-space-4);
}
.nf-code {
  font-size: 80px;
  font-weight: var(--md-weight-bold);
  color: var(--md-primary);
  letter-spacing: 2px;
  line-height: 1;
}
.nf-title { margin: 0; font-size: var(--md-text-display-sm); color: var(--md-on-surface); }
.nf-sub { margin: 0; color: var(--md-on-surface-variant); font-size: var(--md-text-body-md); }
</style>
