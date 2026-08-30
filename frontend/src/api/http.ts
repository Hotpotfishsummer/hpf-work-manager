import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

// 请求拦截：附加 JWT
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('hpf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 跳登录；统一错误提示
http.interceptors.response.use(
  (res) => res.data,
  async (error: AxiosError<{ detail?: string | Array<{ loc: string[]; msg: string; type: string }> }>) => {
    if (error.response?.status === 401) {
      // 关键：同步清空 Pinia store 的 token ref（而非仅 localStorage），
      // 否则路由守卫读到旧值会把 /login 弹回 /dashboard，形成 401 循环
      const { useAuthStore } = await import('@/stores/auth')
      const authStore = useAuthStore()
      authStore.logout()
      const { default: router } = await import('@/router')
      const current = router.currentRoute.value
      if (current.path !== '/login') {
        router.push({ path: '/login', query: { redirect: current.fullPath } })
      }
    } else {
      const detail = error.response?.data?.detail
      let message: string
      if (Array.isArray(detail)) {
        // FastAPI 422 校验错误：[{ loc, msg, type }, ...]
        message = detail.map((d) => d.msg).join('；') || '请求参数有误'
      } else if (typeof detail === 'string') {
        message = detail
      } else {
        message = '请求失败，请稍后重试'
      }
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default http
