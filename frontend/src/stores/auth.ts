import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { User } from '@/types'

const TOKEN_KEY = 'hpf_token'
const USER_KEY = 'hpf_user'

/**
 * 认证 store。
 *
 * 后端有两种模式（由 AUTH_REQUIRED 控制）：
 * - 内网免鉴权（默认）：后端对匿名请求回退 admin，前端无需登录即可用；
 *   此时本地没有 token，请求不带 Authorization 头。
 * - 强制鉴权：必须持有效 JWT，未登录会被 401 拦下。
 *
 * 因此这里不再伪造 "tailnet-mode-token"：有真实凭证就存、就带，
 * 没有就是空 —— 让两种部署模式共用同一套前端逻辑。
 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))

  const user = ref<User | null>(readCachedUser())

  const username = computed(() => user.value?.username ?? 'admin')

  /** 是否已持有凭证（免鉴权部署下为 false，但不影响使用） */
  const isAuthenticated = computed(() => Boolean(token.value))

  function readCachedUser(): User | null {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as User
    } catch {
      return null
    }
  }

  function persist(nextToken: string, nextUser: User) {
    token.value = nextToken
    user.value = nextUser
    localStorage.setItem(TOKEN_KEY, nextToken)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
  }

  async function login(name: string, password: string) {
    const { default: http } = await import('@/api/http')
    const data = await http.post<never, { access_token: string; user: User }>(
      '/auth/login',
      { username: name, password }
    )
    persist(data.access_token, data.user)
  }

  async function register(name: string, email: string, password: string) {
    const { default: http } = await import('@/api/http')
    const data = await http.post<never, { access_token: string; user: User }>(
      '/auth/register',
      { username: name, email, password }
    )
    persist(data.access_token, data.user)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, username, isAuthenticated, login, register, logout }
})
