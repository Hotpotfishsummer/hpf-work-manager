import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 120000,
})

// 请求拦截：有 token 才附加 Authorization。
// 内网免鉴权部署下本就没有 token，硬塞占位串会让每个请求都带一个
// 无效凭证（后端白跑一次 JWT 解码），日志里也全是噪音。
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('hpf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else {
    delete config.headers.Authorization
  }
  return config
})

// 响应拦截：统一错误提示。
// 401 说明凭证失效（强制鉴权模式）→ 清本地凭证并跳登录页；
// 内网免鉴权模式下不会出现 401，这段自然不触发。
http.interceptors.response.use(
  (res) => res.data,
  async (
    error: AxiosError<{
      detail?: string | Array<{ loc: string[]; msg: string; type: string }>
    }>
  ) => {
    const detail = error.response?.data?.detail
    let message: string
    if (Array.isArray(detail)) {
      message = detail.map((d) => d.msg).join('；') || '请求参数有误'
    } else if (typeof detail === 'string') {
      message = detail
    } else {
      message = '请求失败，请稍后重试'
    }

    if (error.response?.status === 401) {
      localStorage.removeItem('hpf_token')
      localStorage.removeItem('hpf_user')
      // 动态导入：避免 router ↔ http 循环依赖，也让免鉴权模式不加载路由
      const { default: router } = await import('@/router')
      if (router.currentRoute.value.path !== '/login') {
        await router.push({
          path: '/login',
          query: { redirect: router.currentRoute.value.fullPath },
        })
      }
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

export default http
