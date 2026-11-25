import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { User } from '@/types'

const defaultAdmin: User = {
  id: 1,
  username: 'admin',
  email: 'admin@example.com',
}

export const useAuthStore = defineStore('auth', () => {
  // 内网/Tailscale 安全访问模式：无需登录，默认持有管理员身份
  const token = ref<string | null>('tailnet-mode-token')
  const user = ref<User | null>(defaultAdmin)

  const username = computed(() => user.value?.username ?? 'admin')

  async function login(_username: string, _password: string) {
    user.value = defaultAdmin
    token.value = 'tailnet-mode-token'
  }

  async function register(_username: string, _email: string, _password: string) {
    user.value = defaultAdmin
    token.value = 'tailnet-mode-token'
  }

  function logout() {
    // 免鉴权模式下保持登录
    user.value = defaultAdmin
    token.value = 'tailnet-mode-token'
  }

  return { token, user, username, login, register, logout }
})
