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
  background-color: var(--bmw-canvas);
}

/* hero-band-dark */
.login-hero {
  background-color: var(--bmw-surface-dark);
  color: var(--bmw-on-dark);
  text-align: center;
  padding: var(--bmw-space-xxl) var(--bmw-space-lg);
}
.hero-mark { color: var(--bmw-primary); margin-bottom: var(--bmw-space-sm); }
.hero-title {
  margin: 0;
  color: var(--bmw-on-dark);
  font-size: var(--bmw-text-display-md);
  font-weight: var(--bmw-weight-display);
  letter-spacing: 0.5px;
}
.hero-sub {
  margin: var(--bmw-space-sm) 0 0;
  color: var(--bmw-on-dark-soft);
  font-size: var(--bmw-text-body-sm);
  font-weight: var(--bmw-weight-body);
}

/* 登录卡片 */
.login-card {
  width: 100%;
  max-width: 420px;
  margin: var(--bmw-space-xxl) auto;
  padding: var(--bmw-card-padding);
  border: 1px solid var(--bmw-hairline);
  border-radius: var(--bmw-radius-none);
  background-color: var(--bmw-canvas);
}

.login-tabs :deep(.el-tabs__item) {
  font-size: var(--bmw-text-title-sm);
  font-weight: var(--bmw-weight-display);
}
.login-tabs :deep(.el-tabs__active-bar) { background-color: var(--bmw-primary); }

.submit-btn {
  width: 100%;
  height: var(--bmw-control-height);
  margin-top: var(--bmw-space-xs);
}

.legal {
  margin: var(--bmw-space-lg) 0 0;
  text-align: center;
  font-size: var(--bmw-text-caption);
  color: var(--bmw-muted-soft);
}
</style>
