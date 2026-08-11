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
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('hpf_token')
      localStorage.removeItem('hpf_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    } else {
      const detail =
        error.response?.data?.detail ||
        (typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : '请求失败，请稍后重试')
      ElMessage.error(detail)
    }
    return Promise.reject(error)
  }
)

export default http
