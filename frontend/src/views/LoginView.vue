<template>
  <div class="login-page">
    <!-- hero-band-dark：深海军蓝横幅，品牌签名 -->
    <div class="login-hero">
      <svg class="hero-mark" viewBox="0 0 24 24" width="56" height="56" aria-hidden="true">
        <circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="1.4" />
        <path d="M12 3.5c2.4 2.2 3.6 5.2 3.6 8.5s-1.2 6.3-3.6 8.5c-2.4-2.2-3.6-5.2-3.6-8.5S9.6 5.7 12 3.5Z" fill="currentColor" />
        <path d="M3.5 12h17" stroke="currentColor" stroke-width="1.2" />
      </svg>
      <h1 class="hero-title">HPF WORK MANAGER</h1>
      <p class="hero-sub">任务 / 项目 / 进度 · 一体化管理</p>
    </div>

    <!-- 白底登录卡片：直角 + hairline -->
    <div class="login-card">
      <el-tabs v-model="mode" class="login-tabs" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>

        <el-form-item v-if="mode === 'register'" label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" autocomplete="email" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </el-form-item>

        <el-form-item v-if="mode === 'register'" label="确认密码" prop="confirm">
          <el-input
            v-model="form.confirm"
            type="password"
            placeholder="请再次输入密码"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="submit"
        >
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <p class="legal">© HPF Work Manager · 本地部署任务管理</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirm: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    {
      validator: (_r, v: string, cb) => {
        if (v !== form.password) cb(new Error('两次输入的密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return

  loading.value = true
  try {
    if (mode.value === 'login') {
      await authStore.login(form.username, form.password)
      ElMessage.success('登录成功')
    } else {
      await authStore.register(form.username, form.email, form.password)
      ElMessage.success('注册成功')
    }
    router.push((route.query.redirect as string) || '/projects')
  } catch {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--md-surface);
}

/* hero-band：始终深色横幅 */
.login-hero {
  background-color: var(--md-inverse-surface);
  color: var(--md-inverse-on-surface);
  text-align: center;
  padding: var(--md-space-7) var(--md-space-5);
}
.hero-mark { color: var(--md-primary); margin-bottom: var(--md-space-2); }
.hero-title {
  margin: 0;
  color: var(--md-inverse-on-surface);
  font-size: var(--md-text-display-sm);
  font-weight: var(--md-weight-bold);
  letter-spacing: 0.5px;
}
.hero-sub {
  margin: var(--md-space-2) 0 0;
  color: var(--md-inverse-on-surface);
  opacity: 0.85;
  font-size: var(--md-text-body-sm);
  font-weight: var(--md-weight-regular);
}

/* 登录卡片 */
.login-card {
  width: 100%;
  max-width: 420px;
  margin: var(--md-space-7) auto;
  padding: var(--md-space-5);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-radius-lg);
  background-color: var(--md-surface);
  box-shadow: var(--md-shadow-2);
}

.login-tabs :deep(.el-tabs__item) {
  font-size: var(--md-text-title-sm);
  font-weight: var(--md-weight-bold);
}
.login-tabs :deep(.el-tabs__active-bar) { background-color: var(--md-primary); }

.submit-btn {
  width: 100%;
  height: var(--md-control-height);
  margin-top: var(--md-space-1);
}

.legal {
  margin: var(--md-space-5) 0 0;
  text-align: center;
  font-size: var(--md-text-label-md);
  color: var(--md-outline-variant);
}
</style>
