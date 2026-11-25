<template>
  <div class="page not-found">
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
}
/* 404：primary-container 色块里的展示数字 */
.nf-code {
  padding: var(--md-space-3) var(--md-space-5);
  border-radius: var(--md-shape-large);
  background-color: var(--md-primary-container);
  color: var(--md-on-primary-container);
  font-size: var(--md-type-display-sm);
  line-height: var(--md-type-display-lh-sm);
  font-weight: var(--md-weight-bold);
  letter-spacing: 2px;
}
.nf-title { margin: var(--md-space-3) 0 0; }
.nf-sub { margin: 0; color: var(--md-on-surface-variant); font-size: var(--md-type-body-md); }
.not-found .el-button { margin-top: var(--md-space-2); }
</style>
